import binascii
import sys
import logging
from flask import Flask, request, jsonify, current_app, make_response, abort, Response
from flask.logging import PROD_LOG_FORMAT
from flask_cors import CORS

from populus import Project
from populus.utils.wait import wait_for_transaction_receipt
import ipfsapi

from gevent import queue

if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()

LOG = logging.getLogger('app')
LOG.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(PROD_LOG_FORMAT))
LOG.addHandler(handler)

ipfs = {}
try:
    ipfs = ipfsapi.connect('127.0.0.1', 5001)
except Exception as ex:
    LOG.error("cannot connect to ipfs: {}".format(ex))
    sys.exit(-1)
LOG.info("connected to IPFS: {}".format(ipfs.id()['ID']))


class TransactionFailed(Exception):
    status_code = 400

    def __init__(self, gas, gasUsed):
        Exception.__init__(self)


def check_txn(chain, txid):
    LOG.info("waiting for: {}".format(txid))
    receipt = wait_for_transaction_receipt(chain.web3, txid)
    LOG.info("receipt: {}".format(receipt))
    # post BZ : status is 1 for success
    if receipt.status == '0x1':
        return receipt
    if receipt.status == 1:
        return receipt
    # 0 for fail with REVERT (for THROW gasused == gas)
    txinfo = chain.web3.eth.getTransaction(txid)
    LOG.info("txn: {}".format(txinfo))
    raise TransactionFailed(txinfo['gas'], receipt['gasUsed'])


def replace(items, into, lookup):
    for item in items:  # sender
        if item in into:  # sender is in args
            addr = into[item].lower()  # sender address in lower
            if addr in lookup:
                into[item] = lookup[addr]


def run_app(app):

    @app.errorhandler(TransactionFailed)
    def transaction_failed(error):
        message = {
            'message': 'Transaction Failed',
        }
        resp = jsonify(message)
        resp.status_code = error.status_code
        return resp

    with Project().get_chain('parity') as chain:
        # list of gevent Queues
        subscriptions = []

        def notify(ev):
            for sub in subscriptions[:]:
                sub.put(ev)

        def on_transfer(args):
            notify(args)
            # LOG.info("EVENT transfer: {}".format(args))

        def on_channel(args):
            notify(args)
            # LOG.info("EVENT channel: {}".format(args))

        def on_settle(args):
            notify(args)
            # LOG.info("EVENT settlement: {}".format(args))

        provider = chain.web3.providers[0]
        if not provider.isConnected():
            LOG.error("Cannot connect to Ethereum")
            sys.exit(-1)

        # accounts need to be unlocked

        # names => addresses
        accounts = {}
        acc = provider.make_request("parity_allAccountsInfo", params=[])
        for address, value in acc["result"].items():
            name = value["name"]
            LOG.info("acc: {}:{}".format(address, name))
            accounts[name] = address
        # addresses => names
        addresses = {v: k for k, v in accounts.items()}

        owner = accounts['owner']
        # assert owner in keybase
        token, _ = chain.provider.get_or_deploy_contract(
            'ScryToken',
            deploy_args=[1000000],
            deploy_transaction={'from': owner})
        LOG.info("token: {}".format(token.address))

        token.on('Transfer', {}, on_transfer)

        contract, _ = chain.provider.get_or_deploy_contract(
            'Scry',
            deploy_args=[token.address],
            deploy_transaction={'from': owner})
        LOG.info("contract: {}".format(contract.address))

        contract.on('ChannelCreated', {}, on_channel)
        contract.on('ChannelSettled', {}, on_settle)

        # subscribe
        @app.route("/subscribe")
        def subscribe():
            def gen():
                q = queue.Queue()
                subscriptions.append(q)
                try:
                    while True:
                        msg = q.get()
                        _args = msg['args']
                        replace(['sender', 'receiver', 'verifier', 'from', 'to'],
                                _args, addresses)

                        yield "data:{}\n\n".format({
                            'event': msg['event'],
                            'args': _args,
                            'block': msg['blockNumber']
                        })
                except GeneratorExit:
                    subscriptions.remove(q)

            return Response(gen(), mimetype="text/event-stream")

        @app.route('/members')
        def members():
            response = jsonify(list(accounts.keys()))
            return response

        # check balance
        @app.route('/balance')
        def balance():
            account = accounts[request.args.get('account')]
            response = jsonify({'balance': token.call().balanceOf(account)})
            return response

        # fund participant
        @app.route('/fund')
        def fund():
            to = request.args.get('account')
            account = accounts[to]
            amount = int(request.args.get('amount'))

            txid = token.transact({"from": owner}).transfer(account, amount)
            check_txn(chain, txid)
            return jsonify({'balance': token.call().balanceOf(account)})

        # create channel to seller
        @app.route('/buyer/channel')
        def channel():
            buyer = accounts[request.args.get('buyer', 'buyer')]
            seller = accounts[request.args.get('seller', 'seller')]

            amount = int(request.args.get('amount', 100))
            txid = token.transact({"from": buyer}).transfer(
                contract.address, amount, bytes.fromhex(seller[2:].zfill(40)))
            LOG.info("channel amount {} txid: {}".format(amount, txid))
            receipt = check_txn(chain, txid)
            return jsonify({'create_block': receipt['blockNumber']})

        # authorize: generate balance_sig
        @app.route('/buyer/authorize')
        def authorize():
            buyer = accounts[request.args.get('buyer', 'buyer')]
            seller = accounts[request.args.get('seller', 'seller')]

            amount = int(request.args.get('amount', 100))
            create_block = int(request.args.get('create_block'))
            msg = contract.call().getBalanceMessage(seller, create_block, amount)
            return jsonify(
                {'balance_sig': chain.web3.eth.sign(buyer, msg)[2:]})

        # verification string
        @app.route('/verifier/sign')
        def verify():
            verifier = accounts[request.args.get('verifier', 'verifier')]
            seller = accounts[request.args.get('seller', 'seller')]

            cid = request.args.get('CID')
            # verifier does its thing
            verification = contract.call().getVerifyMessage(seller, cid)
            return jsonify(
                {'verification_sig': chain.web3.eth.sign(verifier, verification)[2:]})

        @app.route('/seller/upload', methods=['POST'])
        def upload_file():
            f = request.files['data']
            added = ipfs.add(f)
            LOG.info("ipfs upload: {}".format(added))
            return jsonify({'CID': added['Hash'], "size": added['Size']})

        @app.route('/seller/download', methods=['GET'])
        def download_file():
            cid = request.args.get('CID')
            raw_bytes = ''
            try:
                raw_bytes = ipfs.cat(cid)
            except Exception as e:
                abort(Response(response="invalid CID", status=400))
            LOG.info("ipfs found: {}".format(cid))
            response = make_response(raw_bytes)
            response.headers['Content-Type'] = "application/octet-stream"
            response.headers['Content-Disposition'] = "inline; filename=" + cid
            return response

        @app.route("/seller/verify_balance")
        def verify_balance():
            buyer = accounts[request.args.get('buyer', 'buyer')]
            seller = accounts[request.args.get('seller', 'seller')]

            amount = int(request.args.get('amount', 100))
            balance_sig = request.args.get('balance_sig')
            create_block = int(request.args.get('create_block'))
            msg = contract.call().getBalanceMessage(seller, create_block, amount)
            LOG.info("msg: {}".format(msg))
            proof = contract.call().verifyBalanceProof(
                seller, create_block, amount, binascii.unhexlify(balance_sig))
            LOG.info("proof: {}".format(proof))
            if(proof.lower() == buyer.lower()):
                response = jsonify({'verification': 'OK'})
            else:
                response = jsonify({'verification': "!!"})
                response.status_code = 400
            return response

        @app.route('/seller/close')
        def close():
            buyer = accounts[request.args.get('buyer', 'buyer')]
            seller = accounts[request.args.get('seller', 'seller')]
            verifier = accounts[request.args.get('verifier', 'verifier')]

            amount = int(request.args.get('amount', 100))
            balance_sig = request.args.get('balance_sig')
            verify_sig = request.args.get('verification_sig')
            cid = request.args.get('CID')
            create_block = int(request.args.get('create_block'))

            txid = contract.transact({"from": seller}).close(buyer,
                                                             create_block,
                                                             amount,
                                                             binascii.unhexlify(
                                                                 balance_sig),
                                                             verifier,
                                                             cid,
                                                             binascii.unhexlify(verify_sig))
            receipt = check_txn(chain, txid)
            return jsonify({'close_block': receipt['blockNumber']})


app = Flask(__name__)
# 1G file upload limit
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
# allow all domains on all routes
CORS(app)
with app.app_context():
    run_app(current_app)

if __name__ == '__main__':
    from gevent.wsgi import WSGIServer

    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()

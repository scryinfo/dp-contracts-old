import binascii
import logging
import sys

from flask import request, jsonify, make_response, abort, Response
import simplejson as json
from gevent import queue

from playhouse.shortcuts import model_to_dict
from peewee import IntegrityError

from eth_utils import to_checksum_address
import rlp
from ethereum.transactions import Transaction

from model import Listing, Trader
from txn import check_txn, TransactionFailed
from ops import (
    account_balance,
    open_channel,
    close_channel,
    verify_balance_sig,
    buyer_authorization,
    verifier_authorization,
    BalanceVerificationError
)

LOG = logging.getLogger('app')


def replace(items, into, lookup):
    out = into.copy()
    for item in items:  # sender
        if item in into:  # sender is in args
            addr = into[item].lower()  # sender address in lower
            if addr in lookup:
                out[item] = lookup[addr]
    return out


def run_app(app, web3, token, contract, ipfs):

    @app.errorhandler(TransactionFailed)
    def transaction_failed(error):
        message = {
            'message': 'Transaction Failed',
        }
        resp = jsonify(message)
        resp.status_code = error.status_code
        return resp

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        message = {
            'message': 'Save Error: {}'.format(error),
        }
        resp = jsonify(message)
        resp.status_code = 400
        return resp

    @app.errorhandler(BalanceVerificationError)
    def balance_error(error):
        message = {
            'verification': '{}'.format(error),
        }
        resp = jsonify(message)
        resp.status_code = 400
        return resp

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

    token.on('Transfer', {}, on_transfer)
    contract.on('ChannelCreated', {}, on_channel)
    contract.on('ChannelSettled', {}, on_settle)

    provider = web3.providers[0]
    # accounts need to be unlocked

    # names => addresses
    accounts = {}
    acc = provider.make_request("parity_allAccountsInfo", params=[])
    for address, value in acc["result"].items():
        name = value["name"]
        LOG.info("{}:{}".format(name, address))
        accounts[name] = address
    # addresses => names
    addresses = {v: k for k, v in accounts.items()}

    owner = to_checksum_address(accounts['owner'])
    # TODO - assert owner is keybase

    # contract address needs to be visible to events
    addresses[contract.address] = 'contract'

    # subscribe
    @app.route("/subscribe")
    def subscribe():
        def gen():
            q = queue.Queue()
            subscriptions.append(q)
            try:
                while True:
                    msg = q.get()
                    out = replace(['sender', 'receiver', 'verifier', 'from', 'to'],
                                  msg['args'], addresses)

                    yield "data:{}\n\n".format(json.dumps({
                        'event': msg['event'],
                        'args': out,
                        'block': msg['blockNumber']
                    }))
            except GeneratorExit:
                subscriptions.remove(q)

        return Response(gen(), mimetype="text/event-stream")

    def trader_details(trader):
        return {**model_to_dict(trader), **account_balance(web3, trader.account, token)}

    @app.route('/trader', methods=['GET',  'POST'])
    def members():
        if request.method == 'GET':
            return jsonify([trader_details(trader) for trader in Trader.select()])

        # load json
        data = json.loads(request.data)
        ret = provider.make_request("parity_newAccountFromSecret", params=[
                                    "0x" + data['password'], "asdf"])
        if ret['result'] != data['account']:
            raise Exception("saved account is not the same")

        trader = Trader(
            name=data['username'], account=data['account'], password=data['password'])
        try:
            trader.save()
        except IntegrityError as e:
            LOG.info("save conflict: {}: {}".format(model_to_dict(trader), e))
            raise
        return jsonify(model_to_dict(trader))

    # check balance
    @app.route('/balance')
    def balance():
        account = to_checksum_address(request.args.get('account'))
        return jsonify(account_balance(web3, account, token))

    # fund participant
    @app.route('/fund')
    def fund():
        account = to_checksum_address(request.args.get('account'))
        amount = int(request.args.get('amount'))
        LOG.info("fund amount:{} from:{} to:{}".format(
            amount, owner, account))

        # send token
        txid = token.transact({"from": owner}).transfer(account, amount)
        check_txn(web3, txid)

        # send eth too
        txid2 = web3.eth.sendTransaction(
            {'to': account, 'value': 10, 'from': owner})
        check_txn(web3, txid2)

        return jsonify(account_balance(web3, account, token))

    @app.route('/purchase', methods=['POST'])
    def purchase():
        data = json.loads(request.data)
        print(data)
        buyer = to_checksum_address(data['buyer'])
        listing_id = data['id']
        listing = Listing.get(Listing.id == listing_id)
        ch = open_channel(web3, listing.price, buyer,
                          listing.owner, token, contract)

        auth_buyer = buyer_authorization(
            web3, buyer, listing.owner, ch['create_block'], listing.price, contract)
        auth_verifier = verifier_authorization(
            web3, listing.owner, accounts['verifier'], listing.cid, contract)
        ret = close_channel(web3, buyer, listing.owner,
                            accounts['verifier'], ch['create_block'],
                            listing.cid, listing.price,
                            auth_buyer['balance_sig'], auth_verifier['verification_sig'], contract)
        return jsonify(ret)

    # create channel to seller
    @app.route('/buyer/channel')
    def channel():
        buyer = to_checksum_address(request.args.get('buyer'))
        seller = to_checksum_address(request.args.get('seller'))
        amount = int(request.args.get('amount'))
        return jsonify(open_channel(web3, amount, buyer, seller, token, contract))

     # create channel to seller
    @app.route('/buyer/channel2')
    def channel2():
        buyer = request.args.get('buyer')
        seller = request.args.get('seller')
        amount = int(request.args.get('amount', 100))
        LOG.info("channel amount:{} from:{} to:{}".format(
            amount, buyer, seller))

        # find buyer, seller
        buyer = Trader.get(Trader.account == buyer)
        seller = Trader.get(Trader.account == seller)

        buyer_account = to_checksum_address(buyer.account)
        seller_account = to_checksum_address(seller.account)

        # web3.eth.sendTransaction(
        #     {'to': buyer_account, 'value': 100000, 'from': owner})
        LOG.info('buyer balance: eth:{} token:{}'.format(
            web3.eth.getBalance(buyer_account), token.call().balanceOf(buyer_account)))

        nonce = web3.eth.getTransactionCount(buyer_account)
        LOG.info("channel nonce: {}".format(nonce))

        # open a channel: buyer sends txn to token
        # token transfers tokens to contract for seller
        txn = token.buildTransaction({
            "from": buyer_account,
            "nonce": nonce
        }).transfer(
            contract.address, amount, bytes.fromhex(seller_account[2:].zfill(40)))
        LOG.info("channel prepared: {}".format(txn))
        # remove item
        # txn = dict((i, txn[i]) for i in txn if i != 'chainId')
        # gas = web3.eth.estimateGas(txn)
        # LOG.info("channel gas: {}".format(gas))
        # gas = token.estimateGas().transfer(
        #     contract.address, amount, bytes.fromhex(seller_account[2:].zfill(40)))
        # LOG.info("channel gas: {}".format(gas))

        txn = Transaction(nonce=txn['nonce'],
                          gasprice=txn['gasPrice'],
                          #   startgas=gas,
                          #   startgas=txn['gas'] + 100000,
                          startgas=int('0x2a0f8', 16),  # 0x154f0 + 100000,
                          to=txn['to'],
                          data=txn['data'],
                          value=0)
        txn.sign(buyer.password)
        encoded = web3.toHex(rlp.encode(txn))
        txid = web3.eth.sendRawTransaction(encoded)
        # LOG.info("channel txid: {}".format(txid.hex()))
        receipt = check_txn(web3, txid)
        return jsonify({'create_block': receipt['blockNumber']})

     # authorize: generate balance_sig

    @app.route('/buyer/authorize')
    def authorize():
        buyer = request.args.get('buyer')
        seller = request.args.get('seller')
        amount = request.args.get('amount')
        create_block = request.args.get('create_block')
        return jsonify(buyer_authorization(web3, buyer, seller, create_block, amount, contract))

     # verification string
    @app.route('/verifier/sign')
    def verify():
        verifier = request.args.get('verifier')
        seller = request.args.get('seller')
        cid = request.args.get('CID')
        return jsonify(verifier_authorization(web3, seller, verifier, cid, contract))

    def add_user(listing):
        model = model_to_dict(listing)
        try:
            trader = Trader.get(Trader.account == model['owner'])
            model['username'] = trader.name
        finally:
            return model

    @app.route('/listings')
    def sale_items():
        query = Listing.select()
        owner = request.args.get("owner", None)
        if owner:
            query = query.where(Listing.owner == owner)
        res = [add_user(listing) for listing in query]
        return jsonify(res)

    @app.route('/seller/upload', methods=['POST'])
    def upload_file():
        seller = request.args.get('account')
        price = request.args.get('price')
        listing = None
        if len(request.files) == 0:
            cid = request.args.get('CID')
            size = request.args.get('size')
            name = request.args.get('name')
            listing = Listing(cid=cid, size=size,
                              owner=seller, name=name, price=price)
        else:
            if 'data' in request.files:
                f = request.files['data']
                added = ipfs.add(f)
                LOG.info("ipfs upload: {}".format(added))
                cid = added['Hash']
                size = added['Size']
                name = f.filename
                listing = Listing(cid=cid, size=size,
                                  owner=seller, name=name, price=price)

        try:
            listing.save()
        except IntegrityError as e:
            LOG.info("save conflict: {}: {}".format(model_to_dict(listing), e))
            raise

        m2dict = add_user(listing)
        notify({"event": "Upload",
                'args': m2dict,
                'blockNumber': None})

        return jsonify(m2dict)

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
        buyer = request.args.get('buyer')
        seller = request.args.get('seller')

        amount = int(request.args.get('amount', 100))
        balance_sig = request.args.get('balance_sig')
        create_block = int(request.args.get('create_block'))
        verify_balance_sig(buyer, seller, create_block,
                           amount, balance_sig, contract)
        return jsonify({'verification': 'OK'})

    @app.route('/seller/close')
    def close():
        buyer = request.args.get('buyer')
        seller = request.args.get('seller')
        verifier = request.args.get('verifier')

        amount = int(request.args.get('amount', 100))
        balance_sig = request.args.get('balance_sig')
        verify_sig = request.args.get('verification_sig')
        cid = request.args.get('CID')
        create_block = int(request.args.get('create_block'))

        return jsonify(close_channel(web3, buyer, seller, verifier, create_block, cid, amount, balance_sig, verify_sig, contract))

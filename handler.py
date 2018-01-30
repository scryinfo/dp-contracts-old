import binascii
import logging
import sys
import copy

from flask import request, jsonify, make_response, abort, Response
from flask.json import JSONEncoder

import simplejson as json
from gevent import queue

from playhouse.shortcuts import model_to_dict
from peewee import IntegrityError

from eth_utils import to_checksum_address
import rlp
from ethereum.transactions import Transaction

from model import Listing, Trader, PurchaseOrder
from txn import check_txn, TransactionFailed
from ops import (
    channel_info,
    account_balance,
    open_channel,
    close_channel,
    verify_balance_sig,
    buyer_authorization,
    verifier_authorization,
    BalanceVerificationError
)

LOG = logging.getLogger('app')

class ConstraintError(Exception):
    status_code = 400

# class CustomJSONEncoder(JSONEncoder):
    # def default(self, obj):
    #     print('jere')
    #     if isinstance(obj, Listing):
    #         obj = model_to_dict(obj)
    #         del obj['cid']
    #     return JSONEncoder.default(self, obj)

# todo :
# filter fields : cid, passwords etc
# configure % reward
# allow deleteing items

def replace(items, into, lookup):
    out = into.copy()
    for item in items:  # sender
        if item in into:  # sender is in args
            addr = into[item].lower()  # sender address in lower
            if addr in lookup:
                out[item] = lookup[addr]
    return out


def run_app(app, web3, token, contract, ipfs):

    # app.json_encoder = CustomJSONEncoder

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

    @app.errorhandler(ConstraintError)
    def constraint_error(error):
        message = {
            'error': '{}'.format(error),
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
            # add the new queue to list that needs to be notified
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

        # load post json
        data = json.loads(request.data)
        LOG.info("new trader: {}".format(data))        
        ret = provider.make_request("parity_newAccountFromSecret", params=[
                                    "0x" + data['password'], "asdf"])
        if ret['result'] != data['account']:
            raise Exception(
                "saved account is not the same, ret: {}, data:{}".format(ret, data))

        # bootstrap new account with some ether
        txid2 = web3.eth.sendTransaction(
            {'from': owner, 'to': data['account'], 'value': 10})
        check_txn(web3, txid2)

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

        return jsonify(account_balance(web3, account, token))

    @app.route('/purchase', methods=['POST'])
    def purchase():
        data = json.loads(request.data)
        LOG.info("purchase: {}".format(data))
        # verify parameters
        buyer_id = data['buyer']
        buyer = Trader.get(Trader.account == buyer_id)
        listing_id = data['id']
        listing = Listing.get(Listing.id == listing_id)
        
        owner_cs = to_checksum_address(listing.owner.account)
        buyer_cs = to_checksum_address(buyer_id) # checksum address for eth
        ch = open_channel(web3, listing.price, buyer_cs, owner_cs, token, contract)

        auth_buyer = buyer_authorization(
            web3, buyer_cs, owner_cs, ch['create_block'], listing.price, contract)
        auth_verifier = verifier_authorization(
            web3, owner_cs, accounts['verifier'], listing.cid, contract)
        ret = close_channel(web3, buyer_cs, owner_cs,
                            accounts['verifier'], ch['create_block'],
                            listing.cid, listing.price,
                            auth_buyer['balance_sig'], auth_verifier['verification_sig'], contract)

        purchased = PurchaseOrder(buyer=buyer, listing=listing, create_block = ch['create_block'],
                                needs_verification=False, needs_closure=False, 
                                buyer_auth=auth_buyer['balance_sig'], 
                                verifier_auth=auth_verifier['verification_sig'])
        try:
            purchased.save()
        except IntegrityError as e:
            LOG.info("save conflict: {}: {}".format(
                model_to_dict(purchased), e))
            raise
        return jsonify(ret)

    @app.route('/history', methods=['GET'])
    def history():
        res = []
        buyer_id = request.args.get('buyer')
        if buyer_id:
            buyer = Trader.get(Trader.account == buyer_id)
            res = [model_to_dict(purchased) for purchased in buyer.purchases]

        seller_id = request.args.get('seller')
        if seller_id:
            seller = Trader.get(Trader.account == seller_id)
            for listing in seller.listings:
                res.extend([model_to_dict(purchased) for purchased in listing.sales])

        verifier_id = request.args.get('verifier')
        if verifier_id:
            verifier = Trader.get(Trader.account == verifier_id)
            res = [model_to_dict(verified) for verified in verifier.verifications]

        return jsonify(res)

    # create channel to seller
    @app.route('/buyer/purchase', methods=['POST'])
    def channel():
        data = json.loads(request.data)
        LOG.info("purchase: {}".format(data))
        # verify parameters
        buyer_id = data['buyer']
        buyer = Trader.get(Trader.account == buyer_id)
        listing_id = data['listing']
        listing = Listing.get(Listing.id == listing_id)
        verifier_id = data['verifier']
        verifier = Trader.get(Trader.account == verifier_id)

        # make sure verifier, buyer & seller are different
        if (buyer_id == verifier_id):
            raise ConstraintError("Buyer must not be same as Verifier")
        if (listing.owner == verifier_id):
            raise ConstraintError("Seller must not be same as Verifier")
        if (buyer_id == listing.owner):
            raise ConstraintError("Buyer must not be same as Seller")

        owner_cs = to_checksum_address(listing.owner.account)
        buyer_cs = to_checksum_address(buyer_id) # checksum address for eth
        ch = open_channel(web3, listing.price, buyer_cs, owner_cs, token, contract)
        auth_buyer = buyer_authorization(web3, buyer_cs, owner_cs, ch['create_block'], listing.price, contract)
        
        po = PurchaseOrder(buyer = buyer, listing = listing, 
                            verifier=verifier, create_block = ch['create_block'],
                            needs_verification = True, 
                            needs_closure = True, 
                            buyer_auth = auth_buyer['balance_sig'])
        try:
            po.save()
        except IntegrityError as e:
            LOG.info("save conflict: {}: {}".format(model_to_dict(po), e))
            raise
        return jsonify(model_to_dict(po))

    @app.route('/verifier/sign', methods=['POST'])
    def verify():
        data = json.loads(request.data)
        LOG.info("verify: {}".format(data))
        # get  order ID
        po = PurchaseOrder.get(PurchaseOrder.id == data['id'])

        # TODO: make sure verification is pending
        if (po.needs_verification is False):
            raise ConstraintError("Order does not need verification")
        if (po.needs_closure is False):
            raise ConstraintError("Order has already Been closed")

        owner_cs = to_checksum_address(po.listing.owner.account)
        verifier_cs = to_checksum_address(po.verifier.account)
        auth_verifier = verifier_authorization(web3, owner_cs, verifier_cs, po.listing.cid, contract)

        po.verifier_auth = auth_verifier['verification_sig']
        po.needs_verification = False
        po.save()
        notify({
            "event":"ChannelVerified",
            "args" : {"sender":po.verifier.account, "receiver": po.listing.owner.account},
            'blockNumber' : po.create_block,
            })
        return jsonify(model_to_dict(po))

    @app.route('/seller/close', methods=['POST'])
    def close():
        data = json.loads(request.data)
        LOG.info("close: {}".format(data))
        # get  order ID
        po = PurchaseOrder.get(PurchaseOrder.id == data['id'])

        buyer_cs = to_checksum_address(po.buyer.account) # checksum address for eth
        owner_cs = to_checksum_address(po.listing.owner.account)
        verifier_cs = to_checksum_address(po.verifier.account)
        listing = po.listing

        # TODO: make sure verification is complete
        if (po.needs_verification is True):
            raise ConstraintError("Order needs Verification")
        if (po.needs_closure is False):
            raise ConstraintError("Order has already been Closed")

        ret = close_channel(web3, buyer_cs, owner_cs,
                            verifier_cs, po.create_block,
                            listing.cid, listing.price,
                            po.buyer_auth, po.verifier_auth, contract)

        po.needs_closure = False

        po.save()
        notify({
            "event":"ChannelSettled",
            "args" : {"sender":po.buyer.account, "receiver": po.listing.owner.account},
            'blockNumber' : po.create_block,
            })
        return jsonify(model_to_dict(po))

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

    @app.route('/rawTx', methods=['POST'])
    def rawTx():
        rlp = request.data
        encoded = web3.toHex(rlp)
        txid = web3.eth.sendRawTransaction(encoded)
        # LOG.info("channel txid: {}".format(txid.hex()))
        receipt = check_txn(web3, txid)
        return jsonify({'create_block': receipt['blockNumber']})

    @app.route('/value_tx')
    def getValueTx():
        return jsonify({
            'to': 0,
            'gasLimit': 0,
            'gasPrice': 0,
            'value': 0,
            'nonce': 0,
        })

    @app.route('/listings', methods=['GET'])
    def sale_items():
        owner = request.args.get("owner", None)
        if owner:
            trader = Trader.get(Trader.account == owner)
            res = []
            for listing in trader.listings:
                n_sold = len(listing.sales)
                listing = model_to_dict(listing)
                listing['sold'] = n_sold
                res.append(listing)
            return jsonify(res)

        query = Listing.select()
        res = [model_to_dict(listing) for listing in query]
        return jsonify(res)

    @app.route('/seller/upload', methods=['POST'])
    def upload_file():
        seller_id = request.args.get('account')
        seller = Trader.get(Trader.account == seller_id)
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

        m2dict = model_to_dict(listing)
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

    @app.route("/info/channel", methods=['GET'])
    def info_channel():
        po = PurchaseOrder.get(PurchaseOrder.id == request.args.get('id'))
        buyer = to_checksum_address(po.buyer.account) # checksum address for eth
        seller = to_checksum_address(po.listing.owner.account)
        ret = channel_info(contract, buyer, seller, po.create_block)
        return jsonify(ret)

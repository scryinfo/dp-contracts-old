import logging
import sys
import copy
from datetime import date, datetime

from flask import stream_with_context, request, jsonify, make_response, abort, Response
from flask_login import current_user, login_user, logout_user, login_required

import werkzeug

import simplejson as json
from gevent import queue

from playhouse.shortcuts import model_to_dict
from peewee import IntegrityError

from eth_utils import to_checksum_address
import rlp
from ethereum.transactions import Transaction

from model import Listing, Trader, PurchaseOrder
from txn import TransactionFailed
import ops

from datetime import datetime, timedelta
import jwt

JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 60*60

LOG = logging.getLogger('app')


class ConstraintError(Exception):
    status_code = 400

# todo :
# filter fields : cid
# allow deleteing items ??


def replace(items, into, lookup):
    out = into.copy()
    for item in items:  # sender
        if item in into:  # sender is in args
            addr = into[item].lower()  # sender address in lower
            if addr in lookup:
                out[item] = lookup[addr]
    return out


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def run_app(app, web3, token, contract, ipfs, login_manager):

    def json_err(msg, code):
        message = {
            'message': msg,
        }
        resp = jsonify(message)
        resp.status_code = code
        return resp

    @app.errorhandler(jwt.exceptions.ExpiredSignatureError)
    def signature_expired(error):
        return json_err('Signature has expired', 401)

    @app.errorhandler(TransactionFailed)
    def transaction_failed(error):
        return json_err('Transaction Failed', error.status_code)

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        return json_err('Save Error: {}'.format(error), 400)

    @app.errorhandler(ops.BalanceVerificationError)
    def balance_error(error):
        return json_err('verification: {}'.format(error), 400)

    @app.errorhandler(ops.UnknownChannelError)
    def unknown_channel(error):
        return json_err('channel does not exist', 400)

    @app.errorhandler(ConstraintError)
    def constraint_error(error):
        return json_err('{}'.format(error), 400)

    @app.errorhandler(Trader.DoesNotExist)
    def missing_trader(error):
        return json_err('Trader does not exist', 400)

    @app.errorhandler(Listing.DoesNotExist)
    def missing_listing(error):
        return json_err('Listing does not exist', 400)

    @app.errorhandler(PurchaseOrder.DoesNotExist)
    def missing_po(error):
        return json_err('Purchase does not exist', 400)

    @app.errorhandler(werkzeug.exceptions.BadRequest)
    def handle_bad_request(e):
        return json_err('bad request!', 400)

    @app.errorhandler(werkzeug.exceptions.Unauthorized)
    def handle_unauthorized_request(e):
        return json_err('Unauthorized', 401)

    @app.errorhandler(KeyError)
    def handle_key_error(e):
        return json_err('missing parameter: {}'.format(e), 400)

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

    token.on('Transfer', {}, on_transfer)
    contract.on('ChannelCreated', {}, on_channel)
    contract.on('ChannelSettled', {}, on_settle)

    provider = web3.providers[0]
    # accounts need to be unlocked

    # names => addresses
    accounts = {}
    # addresses => names
    accounts['owner'] = web3.eth.coinbase
    addresses = {v: k for k, v in accounts.items()}

    owner = to_checksum_address(accounts['owner'])
    # TODO - assert owner is keybase

    # contract address needs to be visible to events
    addresses[contract.address] = 'contract'

    @app.route('/login', methods=['POST'])
    def login():
        if current_user.is_authenticated:
            raise ConstraintError('already logged in')
        data = request.get_json()
        trader = Trader.select().where(Trader.name == data['username']).first()
        if trader is None:
            raise ConstraintError('user does not exist')
        if not trader.check_password(data['password']):
            raise ConstraintError('bad password')
        # create token
        payload = {
            'user_id': trader.id,
            'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }
        jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
        dictT = model_to_dict(trader)
        del dictT["password_hash"]
        dictT["token"] = jwt_token
        return jsonify(dictT)

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        return jsonify({'message': 'logged out'})

    @app.route('/signup', methods=['POST'])
    def signup():
        # load post json
        data = json.loads(request.data)
        user = Trader.select().where(Trader.name == data['username']).first()
        if user is not None:
            raise ConstraintError("User already exists")
        trader = Trader(name=data['username'], account=data['account'])
        trader.set_password(password=data['password'])
        trader.save()
        LOG.info("new trader: {}".format(trader))
        dictT = model_to_dict(trader)
        del dictT["password_hash"]
        return jsonify(dictT)

    # subscribe
    @app.route("/subscribe")
    @login_required
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
                    }, default=json_serial))
            except GeneratorExit:
                subscriptions.remove(q)

        return Response(stream_with_context(gen()), mimetype="text/event-stream")

    def trader_details(trader):
        return {**model_to_dict(trader), **ops.account_balance(web3, trader.account, token)}

    @app.route('/trader', methods=['GET'])
    @login_required
    def members():
        return jsonify([trader_details(trader) for trader in Trader.select()])

    # check balance
    @app.route('/balance')
    @login_required
    def balance():
        account = to_checksum_address(request.args.get('account'))
        return jsonify(ops.account_balance(web3, account, token))

    # fund participant
    @app.route('/fund')
    @login_required
    def fund():
        trader = Trader.get(Trader.account == request.args.get('account'))
        account = to_checksum_address(trader.account)

        # bootstrap new account with some ether
        ops.send_eth(web3, owner, account, 0.1)

        amount = int(request.args.get('amount'))
        LOG.info("fund amount:{} from:{} to:{}".format(
            amount, owner, account))

        # send token
        ops.send_token(web3, token, owner, account, amount)

        return jsonify(ops.account_balance(web3, account, token))

    def check_purchase(buyer, verifier_id, listing):
        # make sure verifier, buyer & seller are different
        if (buyer.account == verifier_id):
            raise ConstraintError("Buyer must not be same as Verifier")
        if (listing.owner == verifier_id):
            raise ConstraintError("Seller must not be same as Verifier")
        if (buyer.account == listing.owner):
            raise ConstraintError("Buyer must not be same as Seller")

        # make sure buyer has enough tokens to cover listing price
        token_balance = ops.account_balance(web3, buyer.account, token)
        if (listing.price > token_balance['balance']):
            raise ConstraintError("Buyer does not have enough tokens")

    @app.route('/history', methods=['GET'])
    @login_required
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
                res.extend([model_to_dict(purchased)
                            for purchased in listing.sales])

        verifier_id = request.args.get('verifier')
        if verifier_id:
            verifier = Trader.get(Trader.account == verifier_id)
            res = [model_to_dict(verified)
                   for verified in verifier.verifications]

        return jsonify(res)

    @app.route('/history/<id>', methods=['GET'])
    @login_required
    def history_id(id):
        po = PurchaseOrder.get(PurchaseOrder.id == id)
        return jsonify(model_to_dict(po))

    # create channel to seller
    @app.route('/buyer/purchase', methods=['POST'])
    @login_required
    def channel():
        data = json.loads(request.data)
        LOG.info("purchase: {}".format(data))
        # verify parameters
        buyer_id = data['buyer']
        buyer = Trader.get(Trader.account == buyer_id)
        listing_id = data['listing']
        listing = Listing.get(Listing.id == listing_id)
        verifier_id = data.get('verifier')
        verifier = None
        if verifier_id:
            verifier = Trader.get(Trader.account == verifier_id)
        num_verifiers = 1 if verifier else 0
        rewards = int(abs(int(data.get('rewards', 1)))) if verifier else 0
        # convert % to actual reward, truncates towards 0
        rewards = int((listing.price / 100) * rewards)
        check_purchase(buyer, verifier_id, listing)
        ch = data.get('createBlock')
        auth_buyer = data.get('buyerAuth')

        po = PurchaseOrder(buyer=buyer, listing=listing,
                           verifier=verifier,
                           create_block=ch,
                           needs_verification=True if verifier else False,
                           needs_closure=True,
                           buyer_auth=auth_buyer,
                           rewards=rewards)

        po.save()
        return jsonify(model_to_dict(po, exclude=[Listing.cid]))

    @app.route('/verifier/sign', methods=['POST'])
    @login_required
    def verify():
        data = json.loads(request.data)
        LOG.info("verify: {}".format(data))
        # get  order ID
        po = PurchaseOrder.get(PurchaseOrder.id == data['item'])

        # TODO: make sure verification is pending
        if (po.needs_verification is False):
            raise ConstraintError("Order does not need verification")
        if (po.needs_closure is False):
            raise ConstraintError("Order has already Been closed")

        owner_cs = to_checksum_address(po.listing.owner.account)

        # constraint check will make sure of this
        assert (po.verifier is not None)

        po.verifier_auth = data.get('verifierAuth')
        po.needs_verification = False
        po.save()
        notify({
            "event": "ChannelVerified",
            "args": {"sender": po.verifier.account, "receiver": po.listing.owner.account},
            'blockNumber': po.create_block,
        })
        return jsonify(model_to_dict(po, exclude=[Listing.cid]))

    @app.route('/seller/close', methods=['POST'])
    @login_required
    def close():
        js = json.loads(request.data)
        LOG.info("close: {}".format(js))
        # get  order ID
        po = PurchaseOrder.get(PurchaseOrder.id == js['id'])

        if (po.needs_verification):
            raise ConstraintError("Order needs Verification")
        if (po.needs_closure is False):
            raise ConstraintError("Order has already been Closed")

        receipt = ops.raw_txn(web3, js['data'])

        po.needs_closure = False

        po.save()
        return jsonify({'create_block': receipt['blockNumber'], 'purchase': model_to_dict(po)})

    @app.route('/rawTx', methods=['POST'])
    @login_required
    def rawTx():
        js = json.loads(request.data)
        LOG.info("raw request: {}".format(js))
        receipt = ops.raw_txn(web3, js['data'])
        return jsonify({'create_block': receipt['blockNumber']})

    # chainId, gasPrice
    @app.route('/chainInfo', methods=['GET'])
    @login_required
    def chainInfo():
        return jsonify({
            'gasPrice': ops.gas_price(web3),
            'chainId': ops.chain_id(web3),
        })

    # nonce
    @app.route('/nonce/<account>', methods=['GET'])
    @login_required
    def nonce(account):
        account = to_checksum_address(account)
        return jsonify({
            'nonce': ops.nonce(web3, account)
        })

    @app.route('/listing/<id>', methods=['GET'])
    @login_required
    def listing(id):
        res = Listing.get(Listing.id == id)
        return jsonify(model_to_dict(res))

    @app.route('/listings', methods=['GET'])
    @login_required
    def sale_items():
        owner = request.args.get("owner", None)
        res = []
        if owner:
            trader = Trader.get(Trader.account == owner)
            for listing in trader.listings:
                n_sold = len(listing.sales)
                listing = model_to_dict(listing, exclude=[Listing.cid])
                listing['sold'] = n_sold
                res.append(listing)
            return jsonify(res)

        query = Listing.select()
        for listing in query:
            listing = model_to_dict(listing, exclude=[Listing.cid])
            res.append(listing)
        return jsonify(res)

    @app.route('/seller/upload', methods=['POST'])
    @login_required
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
            LOG.info("listing created: {}".format(listing))
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

        listing.save()

        m2dict = model_to_dict(listing)
        notify({"event": "Upload",
                'args': m2dict,
                'blockNumber': None})

        return jsonify(m2dict)

    @app.route('/seller/download', methods=['GET'])
    @login_required
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
    @login_required
    def verify_balance():
        buyer = request.args.get('buyer')
        seller = request.args.get('seller')

        amount = int(request.args.get('amount', 100))
        balance_sig = request.args.get('balance_sig')
        create_block = int(request.args.get('create_block'))
        ops.verify_balance_sig(buyer, seller, create_block,
                               amount, balance_sig, contract)
        return jsonify({'verification': 'OK'})

    @app.route("/info/channel", methods=['GET'])
    @login_required
    def info_channel():
        po = PurchaseOrder.get(PurchaseOrder.id == request.args.get('id'))
        # checksum address for eth
        buyer = to_checksum_address(po.buyer.account)
        seller = to_checksum_address(po.listing.owner.account)
        ret = ops.channel_info(contract, buyer, seller, po.create_block)
        return jsonify(ret)

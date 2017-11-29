import binascii
import sys
from flask import Flask, request, jsonify, current_app
from populus import Project
from populus.utils.wait import wait_for_transaction_receipt


class TransactionFailed(Exception):
    status_code = 400

    def __init__(self, gas, gasUsed):
        Exception.__init__(self)


def check_txn(chain, txid):
    receipt = wait_for_transaction_receipt(chain.web3, txid)
    print(f"receipt: {receipt}")
    # post BZ : status is 1 for success
    if receipt.status == '0x1':
        return receipt
    # 0 for fail with REVERT (for THROW gasused == gas)
    txinfo = chain.web3.eth.getTransaction(txid)
    print(f"fund txn: {txinfo}")
    raise TransactionFailed(txinfo['gas'], receipt['gasUsed'])


def run_app(app):

    @app.errorhandler(TransactionFailed)
    def transaction_failed(error):
        message = {
            'message': 'Transaction Failed',
        }
        resp = jsonify(message)
        resp.status_code = error.status_code
        return resp

    with Project().get_chain('scrychain') as chain:
        def on_transfer(args):
            print(f"new transfer: {args}")

        def on_channel(args):
            print(f"new channel: {args}")

        def on_settle(args):
            print(f"new settlement: {args}")

        # accounts need to be unlocked
        accounts = {}
        try:
            (owner, buyer, seller, verifier) = chain.web3.eth.accounts[:4]
            accounts['owner'] = owner
            accounts['buyer'] = buyer
            accounts['seller'] = seller
            accounts['verifier'] = verifier
        except ConnectionRefusedError as e:
            print(f"Cannot connect to geth: {e}", file=sys.stderr)
            raise

        print(f"accounts: {accounts}")

        token, _ = chain.provider.get_or_deploy_contract(
            'ScryToken',
            deploy_args=[1000],
            deploy_transaction={'from': owner})
        print(f"token: {token.address}")

        token.on('Transfer', {}, on_transfer)

        contract, _ = chain.provider.get_or_deploy_contract(
            'Scry',
            deploy_args=[token.address],
            deploy_transaction={'from': owner})
        print(f"contract: {contract.address}")
        accounts['contract'] = contract.address

        contract.on('ChannelCreated', {}, on_channel)
        contract.on('ChannelSettled', {}, on_settle)

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
            return jsonify({'balance': token.call().balanceOf(buyer)})

        # create channel to seller
        @app.route('/buyer/channel')
        def channel():
            amount = int(request.args.get('amount', 100))
            txid = token.transact({"from": buyer}).transfer(
                contract.address, amount, bytes.fromhex(seller[2:].zfill(40)))
            print(f"channel amount {amount} txid: {txid}")
            receipt = check_txn(chain, txid)
            return jsonify({'create_block': receipt['blockNumber']})

        # authorize string
        @app.route('/buyer/authorize')
        def authorize():
            amount = int(request.args.get('amount', 100))
            create_block = int(request.args.get('create_block'))
            msg = contract.call().getBalanceMessage(seller, create_block, amount)
            return jsonify(
                {'balance_sig': chain.web3.eth.sign(buyer, msg)[2:]})

        # verification string
        @app.route('/verifier/sign')
        def verify():
            cid = request.args.get('CID')
            # verifier does its thing
            verification = contract.call().getVerifyMessage(seller, cid)
            return jsonify(
                {'verification_sig': chain.web3.eth.sign(verifier, verification)[2:]})

        @app.route("/seller/verify_balance")
        def verify_balance():
            amount = int(request.args.get('amount', 100))
            balance_sig = request.args.get('balance_sig')
            create_block = int(request.args.get('create_block'))
            msg = contract.call().getBalanceMessage(seller, create_block, amount)
            print(f"msg: {msg}")
            proof = contract.call().verifyBalanceProof(
                seller, create_block, amount, binascii.unhexlify(balance_sig))
            print(f"proof: {proof}")
            if(proof.lower() == buyer):
                response = jsonify({'verification': 'OK'})
            else:
                response = jsonify({'verification': "!!"})
            return response

        @app.route('/seller/close')
        def close():
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


flask = Flask(__name__)
with flask.app_context():
    run_app(current_app)

if __name__ == "__main__":
    flask.run(threaded=False, debug=True)

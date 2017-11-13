from flask import Flask, request, jsonify, abort
from http import HTTPStatus
from populus import Project
import binascii
from populus.utils.wait import wait_for_transaction_receipt


app = Flask('app')
project = Project()

with project.get_chain('scrychain') as chain:
    # accounts need to be unlocked
    (owner, buyer, seller, verifier) = chain.web3.eth.accounts[:4]

    token, _ = chain.provider.get_or_deploy_contract(
        'ScryToken',
        deploy_args=[1000],
        deploy_transaction={'from': owner})
    print(f"token: {token.address}")

    contract, _ = chain.provider.get_or_deploy_contract(
        'Scry',
        deploy_args=[token.address],
        deploy_transaction={'from': owner})
    print(f"contract: {contract.address}")

    @app.route('/buyer/fund')
    def fund():
        txid = token.transact({"from": owner}).transfer(buyer, 100)
        print("buyer fund txid:" + txid)
        receipt = wait_for_transaction_receipt(chain.web3, txid)
        print(f"buyer receipt: {receipt}")
        response = jsonify({'balance': token.call().balanceOf(buyer)})
        return response

    @app.route('/buyer/channel')
    def channel():
        txid = token.transact({"from": buyer}).transfer(
            contract.address, 100, bytes.fromhex(seller[2:].zfill(40)))
        print("channel txid:" + txid)
        receipt = wait_for_transaction_receipt(chain.web3, txid)
        print(f"channel receipt: {receipt}")
        response = jsonify({'create_block': receipt['blockNumber']})
        return response

    @app.route('/buyer/authorize')
    def authorize():
        create_block = int(request.args.get('block', 5))
        msg = contract.call().getBalanceMessage(seller, create_block, 100)
        response = jsonify(
            {'balance_sig': chain.web3.eth.sign(buyer, msg)[2:]})
        return response

    @app.route('/verifier/sign')
    def verify():
        cid = request.args.get('CID')
        # verifier does its thing
        verification = contract.call().getVerifyMessage(seller, cid)
        response = jsonify(
            {'verification_sig': chain.web3.eth.sign(verifier, verification)[2:]})
        return response

    @app.route('/seller/close')
    def close():
        balance_sig = request.args.get('balance_sig')
        verify_sig = request.args.get('verification_sig')
        cid = request.args.get('CID')
        create_block = int(request.args.get('block', 5))

        txid = contract.transact({"from": seller}).close(
            buyer, create_block, 100, binascii.unhexlify(balance_sig), verifier, cid, binascii.unhexlify(verify_sig))
        print("close txid:" + txid)
        receipt = wait_for_transaction_receipt(chain.web3, txid)
        print(f"close receipt: {receipt}")
        response = jsonify({'close_block': receipt['blockNumber']})
        return response

    app.run(use_reloader=True, threaded=False, debug=True)

import logging

import web3
import inspect

from txn import check_txn

LOG = logging.getLogger('app')


class BalanceVerificationError(Exception):
    status_code = 400


class UnknownChannelError(Exception):
    status_code = 400


def send_eth(web3, sender, receiver, value):
    txid = web3.eth.sendTransaction(
        {'from': sender, 'to': receiver, 'value': web3.toWei(value, "ether")})
    return check_txn(web3, txid)


def gas_price(web3):
    return web3.eth.gasPrice


def chain_id(web3):
    return int(web3.net.version)


def nonce(web3, account):
    return web3.eth.getTransactionCount(account)


def raw_txn(web3, data):
    txid = web3.eth.sendRawTransaction(data)
    # LOG.info("channel txid: {}".format(txid.hex()))
    return check_txn(web3, txid)


def send_token(web3, token, sender, receiver, amount):
    txid = token.transact({"from": sender}).transfer(receiver, amount)
    return check_txn(web3, txid)


def account_balance(web3, account, token):
    if not web3.isAddress(account):
        return {}
    return {
        'balance': token.call().balanceOf(account),
        'eth': web3.fromWei(web3.eth.getBalance(account), "ether")
    }


def channel_info(contract, buyer, seller, open_block):
    try:
        return contract.call().getChannelInfo(buyer, seller, open_block)
    except web3.exceptions.BadFunctionCallOutput:
        raise UnknownChannelError()


def open_channel(web3, amount, buyer, seller, reward, num_verifiers, token, contract):
    amount = int(amount)
    LOG.info("channel amount:{} from:{} to:{}".format(amount, buyer, seller))
    # unlock acct
    web3.personal.unlockAccount(buyer, "asdf")
    # open a channel: send tokens to contract
    nonce = web3.eth.getTransactionCount(buyer)
    hx = seller[2:] + hex(reward)[2:].zfill(8) + \
        hex(num_verifiers)[2:].zfill(8)
    data = bytes.fromhex(hx)
    txid = token.transact({
        "from": buyer,
        "nonce": nonce
    }).transfer(
        contract.address, amount, data)
    receipt = check_txn(web3, txid)
    return {'create_block': receipt['blockNumber']}


def close_channel(web3, buyer, seller, verifier, create_block, cid, amount, balance_sig, verify_sig, contract):
    LOG.info(inspect.getargvalues(inspect.currentframe()))
    amount = int(amount)
    create_block = int(create_block)
    LOG.info("close channel amount:{} from:{} to:{}".format(
        amount, seller, buyer))

    web3.personal.unlockAccount(seller, "asdf")
    nonce = web3.eth.getTransactionCount(seller)
    txid = contract.transact({
        "from": seller,
        "nonce": nonce
    }).close(buyer,
             create_block,
             amount,
             bytes.fromhex(balance_sig[2:]),
             verifier,
             cid,
             bytes.fromhex(verify_sig[2:]))
    receipt = check_txn(web3, txid)
    return {'close_block': receipt['blockNumber'], 'cid': cid}


def buyer_authorization(web3, buyer, seller, create_block, amount, contract):
    amount = int(amount)
    create_block = int(create_block)
    LOG.info("buyer_authorization:{} from:{} to:{} block:{}".format(
        amount, buyer, seller, create_block))

    msg = contract.call().getBalanceMessage(seller, create_block, amount)
    # unlock acct
    web3.personal.unlockAccount(buyer, "asdf")
    return {'balance_sig': web3.eth.sign(buyer, msg)[2:]}


def verifier_authorization(web3, seller, verifier, cid, contract):
    LOG.info("verifier_authorization:{} seller:{} cid:{}".format(
        verifier, seller, cid))
    # unlock acct
    web3.personal.unlockAccount(verifier, "asdf")
    verification = contract.call().getVerifyMessage(seller, cid)
    return {'verification_sig': web3.eth.sign(verifier, verification)[2:]}


def verify_balance_sig(buyer, seller, create_block, amount, balance_sig, contract):
    msg = contract.call().getBalanceMessage(seller, create_block, amount)
    LOG.info("msg: {}".format(msg))
    proof = contract.call().verifyBalanceProof(
        seller, create_block, amount, bytes.fromhex(balance_sig))
    LOG.info("proof: {}".format(proof))
    if(proof.lower() != buyer.lower()):
        raise BalanceVerificationError("Cannot Verify Balance signature")

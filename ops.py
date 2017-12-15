import binascii
import logging

from txn import check_txn

LOG = logging.getLogger('app')


class BalanceVerificationError(Exception):
    status_code = 400


def account_balance(web3, account, token):
    return {
        'balance': token.call().balanceOf(account),
        'eth': web3.eth.getBalance(account)
    }


def open_channel(web3, amount, buyer, seller, token, contract):
    amount = int(amount)
    LOG.info("channel amount:{} from:{} to:{}".format(
        amount, buyer, seller))
    # unlock acct
    web3.personal.unlockAccount(buyer, "asdf")
    # open a channel: send tokens to contract
    nonce = web3.eth.getTransactionCount(buyer)
    txid = token.transact({
        "from": buyer,
        "nonce": nonce
    }).transfer(
        contract.address, amount, bytes.fromhex(seller[2:].zfill(40)))
    receipt = check_txn(web3, txid)
    return {'create_block': receipt['blockNumber']}


def close_channel(web3, buyer, seller, verifier, create_block, cid, amount, balance_sig, verify_sig, contract):
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
             binascii.unhexlify(balance_sig),
             verifier,
             cid,
             binascii.unhexlify(verify_sig))
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
    verification = contract.call().getVerifyMessage(seller, cid)
    return {'verification_sig': web3.eth.sign(verifier, verification)[2:]}


def verify_balance_sig(buyer, seller, create_block, amount, balance_sig, contract):
    msg = contract.call().getBalanceMessage(seller, create_block, amount)
    LOG.info("msg: {}".format(msg))
    proof = contract.call().verifyBalanceProof(
        seller, create_block, amount, binascii.unhexlify(balance_sig))
    LOG.info("proof: {}".format(proof))
    if(proof.lower() != buyer.lower()):
        raise BalanceVerificationError("Cannot Verify Balance signature")

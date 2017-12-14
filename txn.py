import logging

from populus.utils.wait import wait_for_transaction_receipt

LOG = logging.getLogger('app')


class TransactionFailed(Exception):
    status_code = 400

    def __init__(self, gas, gasUsed):
        Exception.__init__(self)


def check_txn(web3, txid):
    LOG.info("waiting for: {}".format(txid.hex()))
    receipt = wait_for_transaction_receipt(web3, txid)
    LOG.info("receipt: {}".format(receipt))
    # post BZ : status is 1 for success
    if receipt.status == '0x1':
        return receipt
    if receipt.status == 1:
        return receipt
    # 0 for fail with REVERT (for THROW gasused == gas)
    txinfo = web3.eth.getTransaction(txid)
    LOG.info("txn: {}".format(txinfo))
    raise TransactionFailed(txinfo['gas'], receipt['gasUsed'])

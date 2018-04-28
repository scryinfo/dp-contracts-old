import logging


LOG = logging.getLogger('app')


class TransactionFailed(Exception):
    status_code = 400


def check_txn(web3, txid):
    LOG.info("waiting for: {}".format(txid))
    receipt = web3.eth.waitForTransactionReceipt(txid)
    LOG.info("receipt: {}".format(receipt))
    # post BZ : status is 1 for success
    if receipt.status == '0x1':
        return receipt
    if receipt.status == 1:
        return receipt
    # 0 for fail with REVERT (for THROW gasused == gas)
    txinfo = web3.eth.getTransaction(txid)
    LOG.warn("failed: {}".format(txinfo))
    raise TransactionFailed(txinfo['gas'], receipt['gasUsed'])

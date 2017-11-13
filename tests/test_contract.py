import binascii
from populus.utils.wait import wait_for_transaction_receipt
from fixtures import (print_logs, create_contract,
                      create_token, create_channel)


def test_create_contract(project, create_contract):
    with project.get_chain('tester') as chain:
        token, contract = create_contract(chain, 'ScryToken', [1000], 'Scry')
        # assert token.call().balanceOf(chain.web3.eth.coinbase) == 1000
        assert token.call().balanceOf(contract.address) == 0


def test_create_channel(project, create_contract, create_channel):
    with project.get_chain('tester') as chain:
        token, contract = create_contract(chain, 'ScryToken', [1000], 'Scry')

        # get accounts
        (owner, buyer, seller) = chain.web3.eth.accounts[:3]
        print(f'owner:{owner} buyer:{buyer} seller:{seller}')

        # accounts need to be unlocked
        block = create_channel(chain, token, contract,
                               owner, buyer, seller, 100)
        print(f"channel create block: {block}")

        key, deposit = contract.call().getChannelInfo(buyer, seller, block)
        print(f"channel: {binascii.b2a_hex(key.encode())} deposit {deposit}")
        assert deposit == 100
        print(f"create block: {block}")

        print_logs(token, "Transfer", "Transfer")
        print_logs(contract, "ChannelCreated", "ChannelCreated")


def test_contract_msgs(project, create_contract):
    with project.get_chain('scrychain') as chain:
        token, contract = create_contract(chain, 'ScryToken', [1000], 'Scry')
        web3 = chain.web3
        msg = contract.call().getBalanceMessage(web3.eth.coinbase, 10, 20)
        print("msg:" + msg)
        # doesn't work with test chain, need a geth chain
        sig = web3.eth.sign(web3.eth.accounts[1], msg)
        print("sig:" + sig)

        proof = web3.personal.ecRecover(msg, sig)
        print("proof:" + proof)
        assert proof == web3.eth.accounts[1]

        proof = contract.call().verifyBalanceProof(
            web3.eth.coinbase, 10, 20, binascii.unhexlify(sig[2:]))
        print("proof:" + proof)
        assert proof.lower() == web3.eth.accounts[1]


def test_verify_proof(project, create_contract):
    with project.get_chain('scrychain') as chain:
        token, contract = create_contract(chain, 'ScryToken', [1000], 'Scry')
        # get accounts
        (owner, buyer, seller, verifier) = chain.web3.eth.accounts[:4]
        print(f'owner:{owner} buyer:{buyer} seller:{seller} verifier:{verifier}')

        msg = contract.call().getVerifyMessage(
            seller, "QmPrafFmEqqQDUgepoVShKUDzdxWtd8UtwA211RE47LBZd")
        sig = binascii.unhexlify(chain.web3.eth.sign(verifier, msg)[2:])
        assert contract.call().verifyVerificationProof(
            seller, "QmPrafFmEqqQDUgepoVShKUDzdxWtd8UtwA211RE47LBZd", sig).lower() == verifier


CID = "QmPrafFmEqqQDUgepoVShKUDzdxWtd8UtwA211RE47LBZd"


def test_close_channel(project, create_contract, create_channel):
    with project.get_chain('scrychain') as chain:
        token, contract = create_contract(chain, 'ScryToken', [1000], 'Scry')
        # get accounts
        (owner, buyer, seller, verifier) = chain.web3.eth.accounts[:4]
        print(f'owner:{owner} buyer:{buyer} seller:{seller}')

        # accounts need to be unlocked
        block = create_channel(chain, token, contract,
                               owner, buyer, seller, 100)
        print(f"channel create block: {block}")

        # buyer -> seller
        balance = contract.call().getBalanceMessage(seller, block, 20)
        balance_sig = binascii.unhexlify(
            chain.web3.eth.sign(buyer, balance)[2:])
        assert contract.call().verifyBalanceProof(
            seller, block, 20, balance_sig).lower() == buyer

        # verifier -> seller
        verification = contract.call().getVerifyMessage(seller, CID)
        verify_sig = binascii.unhexlify(
            chain.web3.eth.sign(verifier, verification)[2:])
        assert contract.call().verifyVerificationProof(
            seller, CID, verify_sig).lower() == verifier

        # close with balance msg (transferred out-of-band)
        txid = contract.transact({"from": seller}).close(
            buyer, block, 20, balance_sig, verifier, CID, verify_sig)
        print("close txid:" + txid)
        receipt = wait_for_transaction_receipt(chain.web3, txid)
        print(f"close receipt: {receipt}")

        assert token.call().balanceOf(buyer) == 80
        assert token.call().balanceOf(seller) == 20

        print_logs(token, "Transfer", "Transfer")
        print_logs(contract, "ChannelCreated", "ChannelCreated")
        print_logs(contract, "ChannelSettled", "ChannelSettled")

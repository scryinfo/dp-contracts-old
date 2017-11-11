import binascii
from fixtures import (print_logs, create_contract,
                      create_token, create_channel)


def test_create_contract(project, create_contract):
    with project.get_chain('scrychain') as chain:
        token, contract = create_contract(chain, 'ScryToken', [1000], 'Scry')
        # assert token.call().balanceOf(chain.web3.eth.coinbase) == 1000
        assert token.call().balanceOf(contract.address) == 0


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


def test_create_channel(project, create_channel):
    with project.get_chain('scrychain') as chain:
        token, contract = create_channel(chain, 'ScryToken', [1000], 'Scry')

        print_logs(token, "Transfer", "Transfer")
        print_logs(contract, "ChannelCreated", "ChannelCreated")

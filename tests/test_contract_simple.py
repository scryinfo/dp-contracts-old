import binascii
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

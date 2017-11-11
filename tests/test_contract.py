from fixtures import (print_logs, create_contract, create_token)


def test_create_contract(chain, project, web3, create_contract):
    token, contract = create_contract('ScryToken', [1000], 'Scry')

    assert token.call().balanceOf(contract.address) == 0


def test_create_channel(chain, project, web3, create_contract):
    token, contract = create_contract('ScryToken', [1000], 'Scry')

    (owner, buyer, seller) = web3.eth.accounts[:3]
    print(f'owner:{owner} buyer:{buyer} seller:{seller}')
    # create buyer with 100 tokens
    token.transact({"from": owner}).transfer(buyer, 100)
    assert token.call().balanceOf(buyer) == 100

    # create channel to seller
    txdata = seller[2:].zfill(40)
    token.transact({"from": buyer}).transfer(
        contract.address, 100, bytes.fromhex(txdata))

    print_logs(token, "Transfer", "Transfer")
    print_logs(contract, "ChannelCreated", "ChannelCreated")

    assert token.call().balanceOf(buyer) == 0
    assert token.call().balanceOf(contract.address) == 100

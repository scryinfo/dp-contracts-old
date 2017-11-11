from fixtures import (print_logs, create_contract,
                      create_token, create_channel)


def test_create_contract(chain, project, web3, create_contract):
    token, contract = create_contract('ScryToken', [1000], 'Scry')

    assert token.call().balanceOf(contract.address) == 0


def test_create_channel(chain, project, web3, create_channel):
    token, contract = create_channel('ScryToken', [1000], 'Scry')

    print_logs(token, "Transfer", "Transfer")
    print_logs(contract, "ChannelCreated", "ChannelCreated")

    msg = contract.call().getBalanceMessage(web3.eth.coinbase, 10, 20)
    print("msg:" + msg)
    # doesn't work with test chain, need a geth chain
    # sig = web3.eth.sign(web3.eth.coinbase, msg)
    # print("sig:" + sig)

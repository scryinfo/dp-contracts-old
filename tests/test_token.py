def test_deploy(chain):
    token, _ = chain.provider.get_or_deploy_contract(
        'ScryToken', deploy_args=[1000])

    total = token.call().totalSupply()
    assert total == 1000


def test_transfer(chain, web3):
    token, _ = chain.provider.get_or_deploy_contract(
        'ScryToken', deploy_args=[1000])

    token.transact().transfer(web3.eth.accounts[1], 100)

    assert token.call().balanceOf(web3.eth.accounts[1]) == 100
    assert token.call().balanceOf(web3.eth.accounts[0]) == 900

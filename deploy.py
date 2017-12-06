from populus import Project
import sys

with Project().get_chain('parity') as chain:

    try:
        owner = chain.web3.eth.accounts[0]
    except (ConnectionRefusedError, FileNotFoundError) as e:
        print("Cannot connect to chain: {}".format(e))
        sys.exit(-1)

    token, _ = chain.provider.get_or_deploy_contract(
        'ScryToken',
        deploy_args=[1000000],
        deploy_transaction={'from': owner})
    print("token: {}".format(token.address))
    contract, _ = chain.provider.get_or_deploy_contract(
        'Scry',
        deploy_args=[token.address],
        deploy_transaction={'from': owner})
    print("contract: {}".format(contract.address))

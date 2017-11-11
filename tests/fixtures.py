import pytest


@pytest.fixture
def create_token(chain):
    def get(token_type, arguments):
        token, _ = chain.provider.get_or_deploy_contract(
            token_type, deploy_args=arguments)
        return token
    return get


@pytest.fixture()
def create_contract(chain, create_token):
    def get(token_type, token_args, contract_type):
        token = create_token(token_type, token_args)
        contract, _ = chain.provider.get_or_deploy_contract(
            contract_type, deploy_args=[token.address])
        return token, contract
    return get


@pytest.fixture()
def create_channel(chain, create_contract, web3):
    def get(token_type, token_args, contract_type):
        token, contract = create_contract(
            token_type, token_args, contract_type)
        (owner, buyer, seller) = web3.eth.accounts[:3]
        print(f'owner:{owner} buyer:{buyer} seller:{seller}')
        # create buyer with 100 tokens
        token.transact({"from": owner}).transfer(buyer, 100)
        assert token.call().balanceOf(buyer) == 100

        # create channel to seller
        txdata = seller[2:].zfill(40)
        token.transact({"from": buyer}).transfer(
            contract.address, 100, bytes.fromhex(txdata))

        assert token.call().balanceOf(buyer) == 0
        assert token.call().balanceOf(seller) == 0
        assert token.call().balanceOf(contract.address) == 100
        return token, contract

    return get


def print_logs(contract, event, name=''):
    transfer_filter_past = contract.pastEvents(event)
    past_events = transfer_filter_past.get()
    if len(past_events):
        print('--(', name, ') past events for ', event, past_events)

    transfer_filter = contract.on(event)
    events = transfer_filter.get()
    if len(events):
        print('--(', name, ') events for ', event, events)

    transfer_filter.watch(lambda x: print(
        '--(', name, ') event ', event, x['args']))

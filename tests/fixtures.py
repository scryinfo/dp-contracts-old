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

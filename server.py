import sys
import logging

from flask import Flask, current_app, jsonify, g
from flask.sessions import SecureCookieSessionInterface
from flask_cors import CORS
from flask_login import LoginManager, user_loaded_from_header
import jwt

from web3 import Web3, WebsocketProvider, HTTPProvider
import ipfsapi
import simplejson as json

import ops
from handler import run_app
from model import db, Trader

if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()

LOG = logging.getLogger('app')
LOG.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
# handler.setFormatter(logging.Formatter(LOG_FORMAT))
LOG.addHandler(handler)

ipfs = {}
try:
    ipfs = ipfsapi.connect('127.0.0.1', 5001)
except Exception as ex:
    LOG.error("cannot connect to ipfs: {}".format(ex))
    raise
LOG.info("connected to IPFS: {}".format(ipfs.id()['ID']))

app = Flask(__name__)
# 1G file upload limit
app.config.update(MAX_CONTENT_LENGTH=1024 * 1024 * 1024)
# session
app.config.update(SECRET_KEY=b'\xd2>i\xbfDv\n29\x15\xe7\x827OZ\x03')
# allow login with remember-me
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.init_app(app)

# dont use cookies


class CustomSessionInterface(SecureCookieSessionInterface):
    """Prevent creating session from API requests."""

    def save_session(self, *args, **kwargs):
        if g.get('login_via_header'):
            return
        return super(CustomSessionInterface, self).save_session(*args, **kwargs)


app.session_interface = CustomSessionInterface()


@user_loaded_from_header.connect
def user_loaded_from_header(self, user=None):
    g.login_via_header = True


# allow all domains on all routes
CORS(app, supports_credentials=True)

app.config.from_envvar('APP_SETTINGS', silent=True)


@app.before_request
def before_request():
    db.connect()


@app.teardown_request
def after_request(response):
    db.close()
    return response


@login_manager.request_loader
def load_user_from_request(request):
    api_key = request.headers.get('JWT')
    if api_key:
        api_key = jwt.decode(api_key, 'secret', algorithms=['HS256'])
        return Trader.get(Trader.id == int(api_key['user_id']))
    return None


_token = json.load(open("build/contracts/ScryToken.json"))
_scry = json.load(open("build/contracts/Scry.json"))
_deployments = json.load(open("deployments.json"))


def load_contract(web3):
    netversion = web3.version.network
    LOG.info("version: {} : {} : {}".format(web3.version.api,
                                            web3.version.node,
                                            netversion))
    try:
        address = _deployments[netversion]['ScryToken']
    except KeyError:
        LOG.error("token not on network")
        raise
    address = Web3.toChecksumAddress(address)
    token = web3.eth.contract(address=address, abi=_token['abi'])
    LOG.info("owner balance:{}".format(token.call().balanceOf(address)))

    try:
        address = _deployments[netversion]['Scry']
    except KeyError:
        LOG.error("contract not on network")
        raise
    contract = web3.eth.contract(
        address=Web3.toChecksumAddress(address), abi=_scry['abi'])
    # LOG.info("contract owner:{}".format(token.call().balanceOf(address)))

    return token, contract


with app.app_context():
    provider = WebsocketProvider('ws://localhost:8546')
    # provider = HTTPProvider('http://localhost:9545')
    if not provider.isConnected():
        raise Exception("Cannot connect to Ethereum")
    web3 = Web3(provider)
    token, contract = load_contract(web3)
    LOG.info('token:{}'.format(token.address))
    LOG.info('contract:{}'.format(contract.address))
    run_app(current_app, web3, token, contract, ipfs, login_manager)

if __name__ == '__main__':
    from gevent.wsgi import WSGIServer

    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()

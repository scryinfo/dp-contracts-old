import sys
import logging

from flask import Flask, current_app, jsonify
from flask.logging import PROD_LOG_FORMAT
from flask_cors import CORS
from flask_login import LoginManager

from populus import Project
import ipfsapi
import simplejson as json

from handler import run_app
from model import db, Listing

if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()

LOG = logging.getLogger('app')
LOG.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(PROD_LOG_FORMAT))
LOG.addHandler(handler)

ipfs = {}
try:
    ipfs = ipfsapi.connect('127.0.0.1', 5001)
except Exception as ex:
    LOG.error("cannot connect to ipfs: {}".format(ex))
    sys.exit(-1)
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
# allow all domains on all routes
CORS(app, supports_credentials=True)

app.config.from_envvar('APP_SETTINGS', silent=True)


@app.before_request
def before_request():
    db.connect()


@app.after_request
def after_request(response):
    db.close()
    return response


@login_manager.user_loader
def load_user(id):
    return Listing.query.get(int(id))


_registrar = json.load(open("registrar.json"))


@app.route("/registrar.json", methods=['GET'])
def registrar():
    return jsonify(_registrar)


_contracts = json.load(open("build/contracts.json"))


@app.route("/contracts.json", methods=['GET'])
def contracts():
    return jsonify(_contracts)


def load_contract(web3):
    LOG.info("version: {} : {} : {}".format(web3.version.api,
                                            web3.version.node,
                                            web3.version.network))

    for _, ctr in _registrar['deployments'].items():
        # token[] = dep[]
        name = list(ctr)[0]
        addr = ctr[name]
        abi = _contracts[name]['abi']
        # print(name, addr, abi)
        ct = web3.eth.contract(address=addr, abi=abi)
        if name == "ScryToken":
            token = ct
        if name == "Scry":
            contract = ct
    return token, contract


with app.app_context():
    with Project().get_chain('parity') as chain:
        if not chain.web3.providers[0].isConnected():
            LOG.error("Cannot connect to Ethereum")
            sys.exit(-1)

        token, contract = load_contract(chain.web3)
        LOG.info('token:{}'.format(token.address))
        LOG.info('contract:{}'.format(contract.address))

        run_app(current_app, chain.web3, token, contract, ipfs, login_manager)

if __name__ == '__main__':
    from gevent.wsgi import WSGIServer

    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()

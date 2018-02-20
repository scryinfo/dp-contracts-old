import sys
import logging
from flask import Flask, current_app
from flask.logging import PROD_LOG_FORMAT
from flask_cors import CORS
from populus import Project
import ipfsapi
import simplejson as json

from flask_jwt import JWT, jwt_required, current_identity
from werkzeug.security import safe_str_cmp
from datetime import datetime, timedelta

from handler import run_app
from model import db

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
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024

app.config['SECRET_KEY'] = 'super-secret'

app.config['JWT_DEFAULT_REALM'] = 'Login Required'

app.config['JWT_AUTH_URL_RULE'] = '/auth'
app.config['JWT_AUTH_ENDPOINT'] = 'jwt'
app.config['JWT_AUTH_USERNAME_KEY'] = 'username'
app.config['JWT_AUTH_PASSWORD_KEY'] = 'password'
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_LEEWAY'] = timedelta(seconds=10)
app.config['JWT_AUTH_HEADER_PREFIX'] = 'JWT'
app.config['JWT_EXPIRATION_DELTA'] = timedelta(seconds=300)
app.config['JWT_NOT_BEFORE_DELTA'] = timedelta(seconds=0)
app.config['JWT_VERIFY_CLAIMS'] = ['signature', 'exp', 'nbf', 'iat']
app.config['JWT_REQUIRED_CLAIMS'] = ['exp', 'iat', 'nbf']



class User(object):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def __str__(self):
        return "User(id='%s')" % self.id

users = [
    User(1, 'user1', 'abcxyz'),
    User(2, 'user2', 'abcxyz'),
]

username_table = {u.username: u for u in users}
userid_table = {u.id: u for u in users}

def authenticate(username, password):
    user = username_table.get(username, None)
    if user and safe_str_cmp(user.password.encode('utf-8'), password.encode('utf-8')):
        return user
def identity(payload):
    user_id = payload['identity']
    return userid_table.get(user_id, None)

jwt = JWT(app, authenticate, identity)



logging.getLogger('flask_cors').level = logging.DEBUG

# allow all domains on all routes
CORS(app)

#CORS(app, origins="http://127.0.0.1:3000",allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials", "Access-Control-Allow-Origin"], supports_credentials=True)






@app.before_request
def before_request():
    db.connect()


@app.after_request
def after_request(response):
    db.close()
    return response


def load_contract(web3):
    LOG.info("version: {} : {} : {}".format(web3.version.api,
                                            web3.version.node,
                                            web3.version.network))
    with open("registrar.json") as reg:
        registry = json.load(reg)
        with open("build/contracts.json") as f:
            abis = json.load(f)
            for _, ctr in registry['deployments'].items():
                # token[] = dep[]
                name = list(ctr)[0]
                addr = ctr[name]
                abi = abis[name]['abi']
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

        run_app(current_app, chain.web3, token, contract, ipfs)



if __name__ == '__main__':
    from gevent.wsgi import WSGIServer


    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()

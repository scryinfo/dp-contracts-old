import sys
import logging
from flask import Flask, current_app
from flask.logging import PROD_LOG_FORMAT
from flask_cors import CORS
from populus import Project
import ipfsapi
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
# allow all domains on all routes
CORS(app)


@app.before_request
def before_request():
    db.connect()


@app.after_request
def after_request(response):
    db.close()
    return response


with app.app_context():
    with Project().get_chain('parity') as chain:
        provider = chain.web3.providers[0]
        if not provider.isConnected():
            LOG.error("Cannot connect to Ethereum")
            sys.exit(-1)

        run_app(current_app, chain, ipfs)

if __name__ == '__main__':
    from gevent.wsgi import WSGIServer

    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()

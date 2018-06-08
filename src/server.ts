const express: any = require('express');
import http from 'http';
import ws from 'ws';

import 'reflect-metadata';
import {
  useExpressServer,
  Action,
  UnauthorizedError
} from 'routing-controllers';

import { LoginController } from './loginController';
import { dbConnection } from './model';
import { tokenUser } from './auth';
import { ChainController } from './chainController';
import { initChain, contractEvents } from './chainOps';
import { TraderController } from './traderController';
import { ListingController, initIpfs } from './listingController';
import { PurchaseController } from './poController';
import { verifyToken } from './jwt';

const debug = require('debug')('server');
const bodyParser = require('body-parser');
const morgan = require('morgan');

const app = express();
app.use(morgan('dev'));
app.use(bodyParser.json());

async function init() {
  await dbConnection().catch(ex => {
    debug('db', ex);
    throw new Error(ex.message);
  });
  await initChain().catch(ex => {
    debug('chain', ex);
    throw new Error(ex.message);
  });
  await initIpfs().catch(ex => {
    debug('ipfs', ex);
    throw new Error(ex.message);
  });
  debug('initialized');
}

process.on('unhandledRejection', (reason, p) => {
  debug('Unhandled Rejection at: Promise', p, 'reason:', reason);
});

function checkToken(token: string | string[] | undefined): string | null {
  if (!token) {
    debug('missing token');
    return null;
  }
  if (token instanceof Array) {
    token = token[0];
  }
  try {
    return verifyToken(token);
  } catch (ex) {
    debug(ex.message);
    return null;
  }
}

useExpressServer(app, {
  // routePrefix: '/api2',
  cors: true,
  authorizationChecker: (action: Action, roles: string[]) => {
    return checkToken(action.request.headers['jwt']) == null ? false : true;
  },
  currentUserChecker: async (action: Action) => {
    const token = action.request.headers['jwt'];
    if (!token) {
      throw new UnauthorizedError('missing token');
    }
    return tokenUser(token);
  },
  controllers: [
    LoginController,
    ChainController,
    TraderController,
    ListingController,
    PurchaseController
  ]
});

const server = http.createServer(app);

type Request = { [key: string]: any };

const wss = new ws.Server({
  server: server,
  path: '/ws',
  verifyClient: (info, done) => {
    const token = info.req.headers['jwt'];
    const user = checkToken(token);
    if (user == null) {
      done(false);
      return;
    }
    const req = info.req as Request;
    req.user = user;
    done(true);
  }
});

wss.on('connection', (ws, req) => {
  const user = (req as Request).user;
  debug(`WS connection from user:`, user.name, user.account);
  // drop messages
  // ws.on('message', message => {
  //   debug(`WS message ${message} from user:`, (req as Request).user);
  // });
});

init()
  .then(() => {
    const events = contractEvents();
    debug(events);
    events.ChannelCreated({ fromBlock: 'latest' }, (_: any, event: any) => {
      wss.clients.forEach(function(client) {
        // {"address":"0x39358f9b1810f8d4f2449dD50308047905F522c0","blockHash":"0xc36485a7ef225d6fa384db4bd45b25b21c0445ad903bdc452188646ace6b1cfc","blockNumber":250,"logIndex":0,"transactionHash":"0xd2f898ea984f6952813151a06d498a401fbf9da44bc451ce3ecb36fad35447f6","transactionIndex":0,"transactionLogIndex":"0x0","type":"mined","id":"log_1b76e279","returnValues":{"0":"0xF446cEEba827959C0801208EBE497932F081f6BC","1":"0x974db6114CAB44Ab555C97Df523B407D7D9B9Dd8","2":"2","sender":"0xF446cEEba827959C0801208EBE497932F081f6BC","receiver":"0x974db6114CAB44Ab555C97Df523B407D7D9B9Dd8","deposit":"2"},"event":"ChannelCreated","signature":"0xf546321371cf888804d4095bcba54ee6da6c8da478d2f2393c5510a8b95e9445","raw":{"data":"0x0000000000000000000000000000000000000000000000000000000000000002","topics":["0xf546321371cf888804d4095bcba54ee6da6c8da478d2f2393c5510a8b95e9445","0x000000000000000000000000f446ceeba827959c0801208ebe497932f081f6bc","0x000000000000000000000000974db6114cab44ab555c97df523b407d7d9b9dd8"]}}
        client.send(JSON.stringify(event));
      });
    });
    events.ChannelSettled({ fromBlock: 'latest' }, (_: any, event: any) => {
      wss.clients.forEach(function(client) {
        // {"address":"0x39358f9b1810f8d4f2449dD50308047905F522c0","blockHash":"0x47763b179f569e206c9c8265c95746ca3ae1e62fd2df35d156ed9e7390aa8d4f","blockNumber":277,"logIndex":2,"transactionHash":"0xe687c759e08ec4d539d39a8135861c3d265cd68bc135528d0a55933ba801a30d","transactionIndex":0,"transactionLogIndex":"0x2","type":"mined","id":"log_937152f2","returnValues":{"0":"0xF446cEEba827959C0801208EBE497932F081f6BC","1":"0x974db6114CAB44Ab555C97Df523B407D7D9B9Dd8","2":"0x5C127124670d01725C7b59fb85328fcD8FF89D92","3":"276","4":"2","sender":"0xF446cEEba827959C0801208EBE497932F081f6BC","receiver":"0x974db6114CAB44Ab555C97Df523B407D7D9B9Dd8","verifier":"0x5C127124670d01725C7b59fb85328fcD8FF89D92","open_block_number":"276","balance":"2"},"event":"ChannelSettled","signature":"0x354beb2e9eeaebe1c2567132309c77eaf5d6bdc51aa37ef8c5bee297cd60eefa","raw":{"data":"0x00000000000000000000000000000000000000000000000000000000000001140000000000000000000000000000000000000000000000000000000000000002","topics":["0x354beb2e9eeaebe1c2567132309c77eaf5d6bdc51aa37ef8c5bee297cd60eefa","0x000000000000000000000000f446ceeba827959c0801208ebe497932f081f6bc","0x000000000000000000000000974db6114cab44ab555c97df523b407d7d9b9dd8","0x0000000000000000000000005c127124670d01725c7b59fb85328fcd8ff89d92"]}}    });
        client.send(JSON.stringify(event));
      });
    });
  })
  .catch(error => {
    debug('initialization', error);
    process.exit(-1);
  });

const port = process.env.PORT || 1234;
server.listen(port, () => debug(`Listening on port ${port}`));

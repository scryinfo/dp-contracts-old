const express: any = require('express');

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
import { initChain } from './chainOps';
import { TraderController } from './traderController';
import { ListingController, initIpfs } from './listingController';
import { PurchaseController } from './poController';
import { verifyToken } from './jwt';

const debug = require('debug')('server');
const bodyParser = require('body-parser');
const morgan = require('morgan');

const app = express();
app.use(morgan('combined'));
app.use(bodyParser.json());

dbConnection();
initChain();
initIpfs();

useExpressServer(app, {
  // routePrefix: '/api2',
  cors: true,
  authorizationChecker: (action: Action, roles: string[]) => {
    const token = action.request.headers['jwt'];
    if (!token) {
      debug('missing token');
      return false;
    }
    try {
      verifyToken(token);
    } catch (ex) {
      debug(ex.message);
      return false;
    }
    // const _ = await tokenUser(token);
    return true;
  },
  currentUserChecker: async (action: Action) => {
    const token = action.request.headers['jwt'];
    if (!token) {
      throw new UnauthorizedError('invalid token');
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

const port = process.env.PORT || 1234;
app.listen(port, () => debug(`Listening on port ${port}`));

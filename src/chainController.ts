import {
  JsonController,
  CurrentUser,
  Get,
  Res,
  QueryParam,
  Authorized,
  Post
} from 'routing-controllers';
import { Response } from 'express';

import { Trader } from './model';
import * as ops from './chainOps';

const debug = require('debug')('server:chain');

@JsonController()
export class ChainController {
  @Get('/contract')
  _contract() {
    return ops.contractDetails();
  }

  @Get('/token')
  token() {
    return ops.tokenDetails();
  }

  @Authorized()
  @Get('/chainInfo')
  async chainInfo() {
    return {
      gasPrice: await ops.gasPrice(),
      chainId: await ops.chainId()
    };
  }

  @Get('/balance')
  async balance(
    @CurrentUser({ required: true })
    trader: Trader,
    @QueryParam('account') account?: string
  ) {
    if (!account) {
      account = trader.account;
    }
    return {
      balance: await ops.tokenBalance(account),
      eth: await ops.ethBalance(account)
    };
  }

  @Authorized()
  @Post('/fund')
  async fund(
    @CurrentUser({ required: true })
    trader: Trader,
    @QueryParam('amount') amount: number,
    @QueryParam('account') account?: string
  ) {
    if (!account) {
      account = trader.account;
    }
    // bootstrap new account with some ether
    let receipt = await ops.sendEth(ops.owner(), account, '0.01');
    debug(
      `fund eth:${0.01} from:${ops.owner()} to:${account} receipt:`,
      receipt
    );

    receipt = await ops.sendToken(ops.owner(), account, amount);
    debug(
      `fund token:${amount} from:${ops.owner()} to:${account} receipt:`,
      receipt
    );
    return {
      balance: await ops.tokenBalance(account),
      eth: await ops.ethBalance(account)
    };
  }
}

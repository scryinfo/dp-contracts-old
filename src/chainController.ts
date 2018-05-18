import {
  JsonController,
  CurrentUser,
  Get,
  Res,
  QueryParam,
  Authorized
} from 'routing-controllers';
import { Response } from 'express';

import { Trader } from './model';
import * as ops from './chainOps';

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

  @Authorized()
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
}

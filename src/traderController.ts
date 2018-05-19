import {
  JsonController,
  Get,
  CurrentUser,
  Authorized,
  QueryParam
} from 'routing-controllers';

import { Repository } from 'typeorm';

import { Trader, traders } from './model';
import * as ops from './chainOps';

const debug = require('debug')('server:trader');

@JsonController('')
export class TraderController {
  _traders: Repository<Trader>;

  constructor() {
    this._traders = traders();
  }

  @Authorized()
  @Get('/trader')
  async all() {
    const _traders: Trader[] = await this._traders.find();
    const map = _traders.map(async it => {
      delete it.password_hash;
      return {
        ...it,
        balance: await ops.tokenBalance(it.account),
        eth: await ops.ethBalance(it.account)
      };
    });
    return Promise.all(map);
  }

  @Get('/trader/me')
  getOne(
    @CurrentUser({ required: true })
    trader: Trader
  ) {
    delete trader.password_hash;
    return { trader };
  }
}

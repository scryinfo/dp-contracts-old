import {
  JsonController,
  Get,
  CurrentUser,
  Authorized} from 'routing-controllers';

import { getRepository } from 'typeorm';

import { Trader } from './model';
import * as ops from './chainOps';


@JsonController('')
export class TraderController {

  @Authorized()
  @Get('/trader')
  async all() {
    const _traders: Trader[] = await getRepository(Trader).find();
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

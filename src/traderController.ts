import {
  JsonController,
  Body,
  Get,
  Post,
  CurrentUser,
  Authorized,
  QueryParam
} from 'routing-controllers';

import { Allow } from 'class-validator';
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
  async Allow() {
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

  @Authorized()
  @Get('/history')
  async history(
    @QueryParam('buyer') buyer?: string,
    @QueryParam('seller') seller?: string,
    @QueryParam('verifier') verifier?: string
  ) {
    debug(buyer, seller, verifier);
    // if (seller) {
    //   // items seller is selling
    //   const trader = await this._traders.findOne(
    //     {
    //       account: seller
    //     },
    //     {
    //       relations: ['listings']
    //     }
    //   );
    //   if (trader) delete trader.password_hash;
    //   return trader;
    //   // return this._traders
    //   //   .createQueryBuilder('trader')
    //   //   .leftJoinAndSelect('trader.listings', 'listing')
    //   //   .getMany();
    // }
    return [];
  }
}

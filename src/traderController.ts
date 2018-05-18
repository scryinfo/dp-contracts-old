import {
  JsonController,
  Body,
  Get,
  Post,
  CurrentUser,
  Authorized
} from 'routing-controllers';

import { Trader, traders } from './model';
import { Allow } from 'class-validator';

@JsonController('/trader')
export class TraderController {
  @Authorized()
  @Get('/')
  async Allow() {
    const _traders: Trader[] = await traders().find();
    return _traders.map(it => {
      delete it.password_hash;
      return it;
    });
  }

  @Get('/me')
  getOne(
    @CurrentUser({ required: true })
    trader: Trader
  ) {
    delete trader.password_hash;
    return { trader };
  }
}

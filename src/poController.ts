import {
  JsonController,
  Authorized,
  Post,
  Body,
  Get,
  Param,
  NotFoundError,
  BadRequestError
} from 'routing-controllers';
import { PurchaseOrder, Trader, Listing } from './model';
import { getRepository } from 'typeorm';
import { rawTx } from './chainOps';

const debug = require('debug')('server:purchase');

class PurchaseParams {
  buyer!: string;
  listing!: number;
  verifier?: string;
  rewards!: string;
  createBlock!: number;
  buyerAuth!: string;
}

class CloseParams {
  id!: number;
  data!: string;
}

@JsonController()
export class PurchaseController {
  @Authorized()
  @Post('/buyer/purchase')
  async purchaes(@Body() purchase: PurchaseParams) {
    const buyer = await getRepository(Trader).findOne({
      account: purchase.buyer
    });
    const listing = await getRepository(Listing).findOne({
      id: purchase.listing
    });
    const verifier = purchase.verifier
      ? await getRepository(Trader).findOne({ account: purchase.verifier })
      : null;
    // TODO check_purchase(buyer, verifier_id, listing)
    let rewards = verifier ? parseInt(purchase.rewards) : 0;
    // covert to %
    rewards = listing!.price / 100 * rewards;
    const po = new PurchaseOrder();
    po.buyer = buyer!;
    po.listing = listing!;
    po.verifier = verifier!;
    po.create_block = purchase.createBlock;
    po.needs_verification = verifier ? true : false;
    po.needs_closure = true;
    po.buyer_auth = purchase.buyerAuth;
    po.rewards = rewards;

    return await getRepository(PurchaseOrder).save(po);
  }

  @Authorized()
  @Post('/verifier/sign')
  async verify() {}

  @Authorized()
  @Post('/seller/close')
  async close(@Body() close: CloseParams) {
    const po = await getRepository(PurchaseOrder).findOne({ id: close.id });
    if (!po) throw new NotFoundError('Order was not found.');
    if (po.needs_verification)
      throw new BadRequestError('Order cannot be closed, needs Verification.');
    if (!po.needs_closure)
      throw new BadRequestError('Order has already been closed.');
    const receipt = await rawTx(close.data);
    debug('close receipt:', receipt);
    if (!receipt.status) {
      throw new BadRequestError('Close Transaction Failed.');
    }
    po.needs_closure = false;
    const closed = await getRepository(PurchaseOrder).save(po);
    return { create_block: receipt.blockNumber, purchase: closed };
  }

  @Authorized()
  @Get('/history/:id')
  getOne(@Param('id') id: number) {
    return getRepository(PurchaseOrder)
      .createQueryBuilder('po')
      .leftJoinAndSelect('po.listing', 'listing')
      .leftJoinAndSelect('po.buyer', 'buyer')
      .leftJoinAndSelect('listing.owner', 'owner')
      .where('po.id = :id', { id: id })
      .getOne();
  }
}

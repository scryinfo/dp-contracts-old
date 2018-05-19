import {
  JsonController,
  Authorized,
  Post,
  Body,
  Get,
  Param,
  NotFoundError,
  BadRequestError,
  CurrentUser,
  QueryParam
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

class VerifyParams {
  item!: number;
  verifierAuth!: string;
}

@JsonController()
export class PurchaseController {
  @Authorized()
  @Post('/buyer/purchase')
  async purchase(@Body() purchase: PurchaseParams) {
    const buyer = await getRepository(Trader).findOne({
      account: purchase.buyer
    });
    if (!buyer) throw new NotFoundError('Buyer was not found.');
    const listing = await getRepository(Listing).findOne({
      id: purchase.listing
    });
    if (!listing) throw new NotFoundError('Listing was not found.');
    const verifier = purchase.verifier
      ? await getRepository(Trader).findOne({ account: purchase.verifier })
      : null;
    // TODO check_purchase(buyer, verifier_id, listing)
    const rewardPct = verifier ? parseInt(purchase.rewards) : 0;
    // covert % to token value, round towards 0
    const rewards = Math.floor(listing.price / 100 * rewardPct);
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
  async verify(@Body() verify: VerifyParams) {
    const order = await loadOrder(verify.item);
    if (!order) throw new NotFoundError('Order was not found.');
    if (!order.needs_verification)
      throw new NotFoundError('Order does not need verification.');
    if (!order.needs_closure)
      throw new BadRequestError('Order has already been closed.');
    // TODO - check that the verifier is the desired one
    order.verifier_auth = verify.verifierAuth;
    order.needs_verification = false;
    const verified = await getRepository(PurchaseOrder).save(order);
    delete verified.listing.cid;
    // TODO - event
    return verified;
  }

  @Authorized()
  @Post('/seller/close')
  async close(@Body() close: CloseParams) {
    const order = await getRepository(PurchaseOrder).findOne({ id: close.id });
    if (!order) throw new NotFoundError('Order was not found.');
    if (order.needs_verification)
      throw new BadRequestError('Order cannot be closed, needs Verification.');
    if (!order.needs_closure)
      throw new BadRequestError('Order has already been closed.');
    const receipt = await rawTx(close.data);
    debug('close receipt:', receipt);
    if (!receipt.status) {
      throw new BadRequestError('Close Transaction Failed.');
    }
    order.needs_closure = false;
    const closed = await getRepository(PurchaseOrder).save(order);
    return { create_block: receipt.blockNumber, purchase: closed };
  }

  @Get('/history')
  async history(
    @CurrentUser({ required: true })
    trader: Trader,
    @QueryParam('buyer') buyer?: string,
    @QueryParam('seller') seller?: string,
    @QueryParam('verifier') verifier?: string
  ) {
    if (seller) {
      return getRepository(PurchaseOrder)
        .createQueryBuilder('po')
        .leftJoinAndSelect('po.listing', 'listing')
        .leftJoinAndSelect('listing.owner', 'owner')
        .where('owner.account = :account', { account: seller })
        .getMany();
    } else if (verifier) {
      return getRepository(PurchaseOrder)
        .createQueryBuilder('po')
        .leftJoinAndSelect('po.listing', 'listing')
        .leftJoinAndSelect('listing.owner', 'owner')
        .leftJoinAndSelect('po.verifier', 'verifier')
        .where('verifier.account = :account', { account: verifier })
        .getMany();
    }
    debug('TODO'); // TODO
    return [];
  }

  @Authorized()
  @Get('/history/:id')
  getOne(@Param('id') id: number) {
    return loadOrder(id);
  }
}

function loadOrder(id: number) {
  return getRepository(PurchaseOrder)
    .createQueryBuilder('po')
    .leftJoinAndSelect('po.listing', 'listing')
    .leftJoinAndSelect('po.buyer', 'buyer')
    .leftJoinAndSelect('listing.owner', 'owner')
    .where('po.id = :id', { id: id })
    .getOne();
}

import { JsonController, Authorized, Post, Body } from 'routing-controllers';
import { traders, PurchaseOrder, purchases, listings } from './model';

class PurchaseParams {
  buyer!: string;
  listing!: number;
  verifier?: string;
  rewards!: string;
  createBlock!: number;
  buyerAuth!: string;
}

@JsonController()
export class PurchaseController {
  @Authorized()
  @Post('/buyer/purchase')
  async purchaes(@Body() purchase: PurchaseParams) {
    const buyer = await traders().findOne({ account: purchase.buyer });
    const listing = await listings().findOne({ id: purchase.listing });
    const verifier = purchase.verifier
      ? await traders().findOne({ account: purchase.verifier })
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

    return await purchases().save(po);
  }
}

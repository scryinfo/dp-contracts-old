import {
  JsonController,
  Authorized,
  Get,
  Param,
  Post,
  QueryParam,
  CurrentUser,
  UploadedFile
} from 'routing-controllers';

import { Listing, Trader } from './model';
import { getRepository } from 'typeorm';

const debug = require('debug')('server:listing');

const ipfsApi = require('ipfs-api');
let ipfs: any;

export async function initIpfs() {
  ipfs = ipfsApi('/ip4/127.0.0.1/tcp/5001');
  debug('ipfs:', await ipfs.id());
}

@JsonController()
export class ListingController {
  @Authorized()
  @Get('/listing/:id')
  getOne(@Param('id') id: number) {
    return getRepository(Listing).findOne({ id });
  }

  @Authorized()
  @Get('/listings')
  async getAll(@QueryParam('owner') owner?: string) {
    if (owner) {
      const all = await getRepository(Listing)
        .createQueryBuilder('listing')
        .leftJoinAndSelect('listing.owner', 'owner')
        .where('owner.account = :account', { account: owner })
        .getMany();
      return all.map(it => {
        delete it.cid;
        return it;
      });
    }
    let all = await getRepository(Listing).find({ relations: ['owner'] });
    return all.map(it => {
      delete it.cid;
      return it;
    });
  }

  @Post('/seller/upload')
  async upload(
    @CurrentUser({ required: true })
    trader: Trader,
    @QueryParam('price') price: number,
    @UploadedFile('data') file: Express.Multer.File
  ) {
    debug(file);
    debug(trader.account);
    // upload to ipfs
    const [added] = await ipfs.files.add(file.buffer);
    debug(added);
    const listing = new Listing();
    listing.cid = added.hash;
    listing.size = added.size;
    listing.owner = trader;
    listing.name = file.originalname;
    listing.price = price;
    return getRepository(Listing).save(listing);
  }
}

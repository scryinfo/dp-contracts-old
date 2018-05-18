import {
  JsonController,
  Authorized,
  Get,
  Param,
  Post,
  QueryParam,
  CurrentUser,
  UploadedFile,
  UploadedFiles
} from 'routing-controllers';

import { Listing, listings, Trader } from './model';
import { Repository } from 'typeorm';

const debug = require('debug')('server:listing');

const ipfsApi = require('ipfs-api');
let ipfs: any;

export async function initIpfs() {
  ipfs = ipfsApi('/ip4/127.0.0.1/tcp/5001');
  debug('ipfs:', await ipfs.id());
}

@JsonController()
export class ListingController {
  _listings: Repository<Listing>;

  constructor() {
    this._listings = listings();
  }

  @Authorized()
  @Get('/listing/:id')
  getOne(@Param('id') id: number) {
    return this._listings.findOne({ id });
  }

  @Authorized()
  @Get('/listings')
  async getAll(@QueryParam('owner') owner?: string) {
    let all = await this._listings.find();
    const map = all.map(async it => {
      const sales = await it.sales;
      debug(it.sales);
      //   it.sold = sales.length;
      delete it.cid;
      return it;
    });
    return Promise.all(map);
  }

  @Post('/seller/upload')
  async upload(
    @CurrentUser({ required: true })
    trader: Trader,
    @QueryParam('price') price: number,
    @QueryParam('size') size: number,
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
    return this._listings.save(listing);
  }
}

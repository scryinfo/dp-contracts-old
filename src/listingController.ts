import {
  JsonController,
  Authorized,
  Get,
  Param,
  Post,
  QueryParam,
  CurrentUser,
  UploadedFile,
  NotFoundError,
  Res
} from 'routing-controllers';

import { Listing, Trader } from './model';
import { getRepository } from 'typeorm';
import { Response } from 'express';

const config = require('./config');

const debug = require('debug')('server:listing');

const ipfsApi = require('ipfs-api');
let ipfs: any;

export async function initIpfs() {
  ipfs = ipfsApi(config.ipfsHost, config.ipfsPort, {protocol: config.ipfsProtocol});
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
      return getRepository(Listing)
        .createQueryBuilder('listing')
        .select(['listing', 'owner.name', 'owner.account', 'category'])
        .leftJoin('listing.owner', 'owner')
        .leftJoin('listing.category', 'category')
        .where('owner.account = :account', { account: owner })
        .getMany();
    }
    return getRepository(Listing)
      .createQueryBuilder('listing')
      .select(['listing', 'owner.name', 'owner.account', 'category'])
      .leftJoin('listing.owner', 'owner')
      .leftJoin('listing.category', 'category')
      .getMany();
  }

  @Post('/seller/upload')
  async upload(
    @CurrentUser({ required: true })
    trader: Trader,
    @QueryParam('price') price: number,
    @UploadedFile('data') file: Express.Multer.File
  ) {
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

  @Get('/seller/download')
  async download(
    @QueryParam('CID', { required: true })
    cid: string,
    @Res() response: Response
  ) {
    // check if either user is owner,
    // has paid for it,
    // or has been assigned as verifier - TODO
    let raw = '';
    try {
      [raw] = await ipfs.files.get(cid);
      debug(raw);
      response.setHeader('Content-Type', 'application/octet-stream');
      response.setHeader('Content-Disposition', 'inline; filename=' + raw.path);
      response.send(raw.content);
    } catch (ex) {
      debug(ex.message);
      throw new NotFoundError(`File was not found.`);
    }
  }
}

import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  Repository,
  createConnection,
  getConnection,
  Index,
  CreateDateColumn,
  ManyToOne,
  OneToMany
} from 'typeorm';

import { PostgresConnectionOptions } from 'typeorm/driver/postgres/PostgresConnectionOptions';

const debug = require('debug')('server:model');

@Entity()
export class Trader {
  @PrimaryGeneratedColumn() id!: number;

  @Index({ unique: true })
  @Column({ length: 128 })
  name!: string;

  @Index({ unique: true })
  @Column({ length: 128 })
  account!: string;

  @CreateDateColumn({ type: 'timestamp' })
  created_at!: Date;

  @Column({ length: 128 })
  password_hash!: string;

  @OneToMany(type => Listing, listing => listing.owner)
  listings!: Listing[];

  @OneToMany(type => PurchaseOrder, po => po.buyer)
  purchases!: PurchaseOrder[];

  @OneToMany(type => PurchaseOrder, po => po.verifier)
  verifications!: PurchaseOrder[];
}

@Entity()
export class Listing {
  @PrimaryGeneratedColumn() id!: number;

  @Column({ length: 128 })
  name!: string;

  @Column({ length: 128 })
  cid!: string;

  @Column({ length: 10 })
  size!: string;

  @ManyToOne(type => Trader, trader => trader.listings)
  owner!: Trader;

  @Column({ type: 'int' })
  price!: number;

  @CreateDateColumn({ type: 'timestamp' })
  created_at!: Date;

  @OneToMany(type => PurchaseOrder, po => po.listing)
  sales!: PurchaseOrder[];
}

@Entity()
export class PurchaseOrder {
  @PrimaryGeneratedColumn() id!: number;

  @ManyToOne(type => Trader, trader => trader.purchases)
  buyer!: Trader;

  @ManyToOne(type => Listing, listing => listing.sales)
  listing!: Listing;

  @ManyToOne(type => Trader, trader => trader.verifications)
  verifier!: Trader;

  @Column({ type: 'int' })
  create_block!: number;

  @Column() needs_verification!: boolean;

  @Column() needs_closure!: boolean;

  @Column({ length: 256 })
  buyer_auth!: string;

  @Column({ length: 256, nullable: true })
  verifier_auth?: string;

  @Column({ type: 'int' })
  rewards!: number;

  @CreateDateColumn({ type: 'timestamp' })
  created_at!: Date;
}

const config: PostgresConnectionOptions = {
  type: 'postgres',
  database: 'scry',
  schema: 'scry2',
  entities: [Trader, Listing, PurchaseOrder],
  synchronize: true,
  logging: true
};

export async function dbConnection() {
  await createConnection(config);
  debug('db connected');
}

export function traders(): Repository<Trader> {
  return getConnection().getRepository(Trader);
}

export function listings(): Repository<Listing> {
  return getConnection().getRepository(Listing);
}

export function purchases(): Repository<PurchaseOrder> {
  return getConnection().getRepository(PurchaseOrder);
}

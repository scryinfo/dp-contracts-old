import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  Repository,
  createConnection,
  getConnection,
  Connection,
  Index,
  CreateDateColumn,
  ManyToOne
} from 'typeorm';

import { PostgresConnectionOptions } from 'typeorm/driver/postgres/PostgresConnectionOptions';

const debug = require('debug')('server:model');

@Entity({ schema: 'scry' })
export class Trader {
  @PrimaryGeneratedColumn() id!: number;

  @Index({ unique: true })
  @Column()
  name!: string;

  @Index({ unique: true })
  @Column()
  account!: string;

  @CreateDateColumn({ type: 'timestamp' })
  created_at!: number;

  @Column({ length: 128 })
  password_hash!: string;
}

@Entity({ schema: 'scry' })
export class Listing {
  @PrimaryGeneratedColumn() id!: number;

  @Column() cid!: string;

  @Column() size!: string;

  @ManyToOne(type => Trader)
  owner!: Trader;

  @Column({ type: 'decimal' })
  price!: number;

  @CreateDateColumn({ type: 'timestamp' })
  created_at!: number;
}

@Entity({ schema: 'scry' })
export class PurchaseOrder {
  @PrimaryGeneratedColumn() id!: number;

  @ManyToOne(type => Trader)
  buyer!: Trader;

  @ManyToOne(type => Listing)
  listing!: Listing;

  @ManyToOne(type => Trader)
  verifier!: Trader;

  @Column() create_block!: number;

  @Column() needs_verification!: boolean;

  @Column() needs_closure!: boolean;

  @Column() buyer_auth!: string;

  @Column() verifier_auth!: string;

  @Column() rewards!: number;

  @CreateDateColumn({ type: 'timestamp' })
  created_at!: number;
}

const config: PostgresConnectionOptions = {
  type: 'postgres',
  host: 'localhost',
  database: 'scry',
  // schema: 'scry',
  entities: [Trader, Listing, PurchaseOrder],
  synchronize: true,
  logging: false
};

export async function dbConnection() {
  await createConnection(config);
  debug('db connected');
}

export function traders(): Repository<Trader> {
  return getConnection().getRepository(Trader);
}

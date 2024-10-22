import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  createConnection,
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

  @OneToMany(() => Listing, listing => listing.owner)
  listings!: Listing[];

  @OneToMany(() => PurchaseOrder, po => po.buyer)
  purchases!: PurchaseOrder[];

  @OneToMany(() => PurchaseOrder, po => po.verifier)
  verifications!: PurchaseOrder[];
}

@Entity()
export class Categories {
  @PrimaryGeneratedColumn() id!: number;

  @Column({ length: 256, unique: true  })
  name!: string;

  @OneToMany(() => Listing, listing => listing.category_id)
  listings!: Listing[];

  @Column({ type: "jsonb" })
  metadata!;

  @CreateDateColumn({ type: 'timestamp' })
  created_at!: Date;

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

  @ManyToOne(() => Trader, trader => trader.listings)
  owner!: Trader;

  @ManyToOne(() => Categories, category => category.listings)
  category!: Categories;

  @Column({ type: 'int' })
  price!: number;

  @CreateDateColumn({ type: 'timestamp' })
  created_at!: Date;

  @OneToMany(() => PurchaseOrder, po => po.listing)
  sales!: PurchaseOrder[];

  @Column({ nullable: true})
  isstructured!: boolean;

  @Column({ length: 255, nullable: true  })
  keywords!: string;


}

@Entity()
export class PurchaseOrder {
  @PrimaryGeneratedColumn() id!: number;

  @ManyToOne(() => Trader, trader => trader.purchases)
  buyer!: Trader;

  @ManyToOne(() => Listing, listing => listing.sales)
  listing!: Listing;

  @ManyToOne(() => Trader, trader => trader.verifications)
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
  database: process.env.PG_DB,
  schema: process.env.PG_DB_SCHEMA,
  host: process.env.PG_HOST,
  username: process.env.PG_USER,
  password: process.env.PG_PASSWORD,
  entities: [Trader, Listing, PurchaseOrder, Categories],
  synchronize: true,
  logging: true
};

export async function dbConnection() {
  await createConnection(config);
  debug('db connected');
}

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
export class CategoryTree {
  @PrimaryGeneratedColumn() id!: number;

  @Column({ length: 256, unique: true  })
  name!: string;

  @OneToMany(() => Listing, listing => listing.id)
  listings!: Listing[];

  @Column()
  parent_id!:number;

  @Column()
  is_structured!: boolean;

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

  @ManyToOne(() => CategoryTree, category => CategoryTree.listings)
  category!: Categories;

  @Column({ type: 'int' })
  price!: number;

  @CreateDateColumn({ type: 'timestamp' })
  created_at!: Date;

  @OneToMany(() => PurchaseOrder, po => po.listing)
  sales!: PurchaseOrder[];

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
  created_at!: i;
}



const config: PostgresConnectionOptions = {
  type: 'postgres',
  database: 'scry',
  schema: 'scry2',
  host: process.platform === 'linux' ? '/var/run/postgresql' : '/tmp',
  entities: [Trader, Listing, PurchaseOrder, CategoryTree],
  synchronize: true,
  logging: true
};

export async function dbConnection() {
  await createConnection(config);
  debug('db connected');
}

import {
  Entity,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
  Column,
  Repository,
  createConnection,
  getConnection,
  Connection
} from 'typeorm';
import { PostgresConnectionOptions } from 'typeorm/driver/postgres/PostgresConnectionOptions';

const debug = require('debug')('server:model');

@Entity({ schema: 'scry' })
export class Trader {
  @PrimaryGeneratedColumn() id!: number;

  @Column() name!: string;
  @Column() account!: string;
  @UpdateDateColumn({ type: 'timestamp' })
  created_at!: number;
  @Column() password_hash!: string;
}

const config: PostgresConnectionOptions = {
  type: 'postgres',
  host: 'localhost',
  database: 'scry',
  // schema: 'scry',
  entities: [Trader],
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

import { UnauthorizedError } from 'routing-controllers';
import { Trader } from './model';
import { newToken, verifyToken } from './jwt';
import { getRepository } from 'typeorm';

import auth from 'passport-local-authenticate';

const debug = require('debug')('server:auth');

const options = {
  digestAlgorithm: 'SHA256',
  iterations: 50000,
  keylen: 32,
  saltlen: 8,
  encoding: 'hex'
};

export async function authenticate(
  username: string,
  password: string
): Promise<any> {
  const trader = await getRepository(Trader).findOne({ name: username });
  if (!trader) {
    throw new UnauthorizedError('user does not exist');
  }
  const [, salt, hash] = trader!.password_hash.split('$', 3);

  return new Promise<any>((resolve, reject) => {
    auth.verify(password, { salt, hash }, options, function(
      err: any,
      verified: boolean
    ) {
      if (err || !verified) {
        reject(new UnauthorizedError('bad password')); // bad username or password
      }
      const jwt = newToken(trader);
      resolve({ trader, jwt });
    });
  });
}

function hashPassword(password: string) {
  return new Promise<string>((resolve, reject) => {
    auth.hash(password, options, (error: any, hashed: any) => {
      if (error) {
        reject('bad username or password');
      }
      const { salt, hash } = hashed;
      resolve(`pbkdf2:sha256:50000$${salt}$${hash}`);
    });
  });
}

async function newTrader(
  username: string,
  password: string,
  account: string
): Promise<Trader> {
  const pw = await hashPassword(password);
  let trader = new Trader();
  trader.name = username;
  trader.account = account;
  trader.password_hash = pw;
  return getRepository(Trader).save(trader);
}

export async function signup(
  username: string,
  password: string,
  account: string
): Promise<any> {
  const exists = await getRepository(Trader).count({ name: username });
  if (exists !== 0) {
    throw 'User exists';
  }
  const trader = await newTrader(username, password, account);
  const jwt = newToken(trader);
  return { trader, jwt };
}

export function tokenUser(token: string): Promise<Trader | undefined> {
  try {
    const { user_id } = verifyToken(token);
    return getRepository(Trader).findOne(user_id);
  } catch (ex) {
    debug(ex.message);
    throw new UnauthorizedError(ex.message);
  }
}

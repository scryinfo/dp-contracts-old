import * as jwt from 'jsonwebtoken';

import { Trader } from './model';

const JWT_SECRET = 'secret';
const JWT_ALGORITHM = 'HS256';
const JWT_EXP_DELTA_SECONDS = 60 * 60 * 60;

export function verifyToken(token: string): any {
  return jwt.verify(token, JWT_SECRET, {
    algorithms: [JWT_ALGORITHM]
  });
}

export function newToken(trader: Trader): string {
  return jwt.sign(
    {
      user_id: trader.id,
      name: trader.name,
      account: trader.account
    },
    JWT_SECRET,
    { expiresIn: 60 * 60 }
  );
}

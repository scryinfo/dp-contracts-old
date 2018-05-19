import { JsonController, Body, Post, CurrentUser } from 'routing-controllers';

import { MinLength } from 'class-validator';

import { Trader } from './model';
import { authenticate, signup } from './auth';

class LoginParams {
  @MinLength(2)
  username!: string;

  @MinLength(2)
  password!: string;
}

class SignupParams {
  @MinLength(2)
  username!: string;

  @MinLength(2)
  password!: string;

  @MinLength(20)
  account!: string;
}

@JsonController()
export class LoginController {
  @Post('/signup')
  async signup(@Body() user: SignupParams): Promise<any> {
    const { trader, jwt } = await signup(
      user.username,
      user.password,
      user.account
    );
    delete trader.password_hash;
    return { token: jwt, ...trader };
  }

  @Post('/login')
  async login(@Body() user: LoginParams): Promise<any> {
    const { trader, jwt } = await authenticate(user.username, user.password);
    delete trader.password_hash;
    return { token: jwt, ...trader };
  }

  @Post('/logout')
  logout(
    @CurrentUser({ required: true })
    trader: Trader
  ) {
    return { message: 'logged out ' + trader.name };
  }
}

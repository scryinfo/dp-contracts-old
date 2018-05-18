import Web3 from 'web3';
import { WSAENAMETOOLONG } from 'constants';

const debug = require('debug')('server:contract');

let token: any;
let contract: any;
let web3: Web3;

const _token = require('../../build/contracts/ScryToken.json');
const _contract = require('../../build/contracts/Scry.json');
const _deployments = require('../../deployments.json');

export async function initChain() {
  const provider = new Web3.providers.WebsocketProvider('ws://localhost:8546');
  web3 = new Web3(provider);
  const network = await web3.eth.net.getId();
  debug('network:', network);

  const coinbase = await web3.eth.getCoinbase();
  debug('coinbase:', coinbase);

  let address = _deployments[network]['ScryToken'];
  token = new web3.eth.Contract(_token.abi, address);
  debug('token:', token._address);

  address = _deployments[network]['Scry'];
  contract = new web3.eth.Contract(_contract.abi, address);
  debug('contract:', contract._address);
  //   debug('owner balance: ', await token.methods.balanceOf(coinbase).call());
}

export function contractDetails() {
  return { abi: _contract.abi, address: contract._address };
}

export function tokenDetails() {
  return { abi: _token.abi, address: token._address };
}

export function gasPrice() {
  return web3.eth.getGasPrice();
}

export function chainId() {
  return web3.eth.net.getId();
}

export function nonce(account: string) {
  return web3.eth.getTransactionCount(account);
}

export function sendToken(sender: string, receiver: string, amount: number) {
  return token.methods.transfer(receiver, amount).send({
    from: sender
  });
}

export function tokenBalance(account: string) {
  return token.methods
    .balanceOf(account)
    .call()
    .then((str: string) => parseFloat(str));
}
export function ethBalance(account: string) {
  return web3.eth
    .getBalance(account)
    .then(wei => parseFloat(web3.utils.fromWei(wei, 'ether')));
}

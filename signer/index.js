"use strict";

const axios = require("axios");
const Web3 = require("web3");
const { toWei, toHex, padLeft, hexToBytes } = require("web3-utils");
const contracts = require("../build/contracts.json");
const deployments = require("../registrar.json").deployments;
const provider = new Web3.providers.WebsocketProvider("ws://localhost:8546");
const web3 = new Web3(provider);

// converts { "blockchain..":{"key":"val"}} to {"key":"val"}
const registry = Object.values(deployments).reduce(
  (acc, ele) => (acc = Object.assign(acc, ele)),
  {}
);

const token = new web3.eth.Contract(
  contracts["ScryToken"].abi,
  registry["ScryToken"]
);
console.info("token:", token._address);
const contract = new web3.eth.Contract(contracts["Scry"].abi, registry["Scry"]);
console.info("contract:", contract._address);

// event subscriptions
function onEvt(err, evt) {
  console.info(`event: ${evt.event} : ${JSON.stringify(evt.returnValues)}`);
}
token.events.Transfer({}, onEvt);
contract.events.ChannelCreated({}, onEvt);
contract.events.ChannelSettled({}, onEvt);

const buyerKey =
  "0xa518652e06e57e6d9e9ff93ad5eef2892415a9735ff14c246eff301342c8e0f7";
const buyer = web3.eth.accounts.privateKeyToAccount(buyerKey);
console.info("buyer:", buyer.address);

const sellerKey =
  "0x80ea726eaa53b661b558c9be7d752c8521719b9f018fd7c3d102020580a61d0f";
const seller = web3.eth.accounts.privateKeyToAccount(sellerKey);
console.info("seller:", seller.address);

const verifierKey =
  "0x4948deb9bd1ce66e05dcfe500583220b252ac221bae030cde498ba6732e5d58d";
const verifier = web3.eth.accounts.privateKeyToAccount(verifierKey);
console.info("verifier:", verifier.address);

const cid = "QmZ3gZXbckAxfJafysmmoNPwx67WiaLdqoYCxrnVWNeJ7R";

async function main() {
  const coinbase = await web3.eth.getCoinbase();
  console.info("coinbase:", coinbase);

  // await sendTokenFromCoinbase(coinbase, buyer.address);
  // await sendEth(coinbase, seller.address);
  // await sendEth(coinbase, buyer.address);

  console.info("buyer eth: ", await web3.eth.getBalance(buyer.address));
  console.info("seller eth: ", await web3.eth.getBalance(seller.address));

  // send from address to coinbase
  // await sendToken(buyer, coinbase);

  const createBlock = await openChannel2(10, buyer, seller, 1, 1);
  console.info("opened @:", createBlock);
  const ba = await buyerAuthorization(buyer, seller, createBlock, 10);
  console.info("ba:", ba);
  const va = await verifierAuthorization(seller, verifier, cid);
  console.info("va:", va);
  const closed = await closeChannel(
    buyer,
    seller,
    verifier,
    createBlock,
    cid,
    10,
    ba.signature,
    va.signature
  );
  console.info("closed @:", closed);
}

async function sendEth(from, to) {
  const tx = await web3.eth.sendTransaction({
    from: from,
    to: to,
    value: 1
  });
  console.info("send @ ", tx.blockNumber);
}

async function tokenBalance(address) {
  return await token.methods.balanceOf(address).call();
}

async function sendToken(from, to) {
  // console.info("tokens:", await tokenBalance(from.address));

  const nonce = await web3.eth.getTransactionCount(from.address);
  console.info("nonce:", nonce);

  const payload = token.methods.transfer(to, 1).encodeABI();
  console.info("pld", payload);
  const tx = new Tx({
    nonce: nonce,
    from: from.address,
    to: token._address,
    gas: 38121,
    data: payload
  });
  tx.sign(Buffer.from(buyer.privateKey.slice(2), "hex"));
  const signed = "0x" + tx.serialize().toString("hex");
  console.info("signed", signed);

  const receipt = await web3.eth.sendSignedTransaction(signed);
  console.info("tfr:", receipt.blockNumber, receipt.gasUsed, receipt.status);
  console.info("tokens:", await tokenBalance(from.address));
}

// send from coinbase to address
async function sendTokenFromCoinbase(coinbase, address) {
  const receipt1 = await token.methods.transfer(address, 100).send({
    from: coinbase
  });
  console.info("tokens:", await token.methods.balanceOf(address).call());
  // console.info("token receipt:", receipt1);
}

async function openChannel2(amount, buyer, seller, reward, verifiers) {
  console.info("buyer tokens:", await tokenBalance(buyer.address));
  console.info("seller tokens:", await tokenBalance(seller.address));

  const hx =
    "0x" +
    seller.address.slice(2) +
    padLeft(reward, 8).slice(2) +
    padLeft(verifiers, 8).slice(2);

  const payload = token.methods
    .transfer(contract._address, amount, hx)
    .encodeABI();

  const nonce = await web3.eth.getTransactionCount(buyer.address);
  const tx = {
    nonce: nonce,
    from: buyer.address,
    to: token._address,
    gas: 198579,
    data: payload
  };
  const signed = await web3.eth.accounts.signTransaction(tx, buyer.privateKey);
  console.info("signed", signed);

  const resp = await axios({
    method: "post",
    url: "http://localhost:5000/rawTx",
    data: { data: signed.rawTransaction }
  });
  if (resp.status != 200) {
    console.error("error:", resp.statusText);
    return resp.statusText;
  }
  console.info("resp:", resp.data);
  return resp.data.create_block;
}

async function openChannel(amount, buyer, seller, reward, verifiers) {
  console.info("buyer tokens:", await tokenBalance(buyer.address));
  console.info("seller tokens:", await tokenBalance(seller.address));

  const hx =
    "0x" +
    seller.address.slice(2) +
    padLeft(reward, 8).slice(2) +
    padLeft(verifiers, 8).slice(2);

  const payload = token.methods
    .transfer(contract._address, amount, hx)
    .encodeABI();

  const nonce = await web3.eth.getTransactionCount(buyer.address);
  const tx = {
    nonce: nonce,
    from: buyer.address,
    to: token._address,
    gas: 198579,
    data: payload
  };
  const signed = await web3.eth.accounts.signTransaction(tx, buyer.privateKey);
  const receipt = await web3.eth.sendSignedTransaction(signed.rawTransaction);
  console.info("tfr:", receipt);
  console.info("buyer tokens:", await tokenBalance(buyer.address));
  return receipt.blockNumber;
}

async function closeChannel(
  buyer,
  seller,
  verifier,
  createBlock,
  cid,
  amount,
  balanceSig,
  verifySig
) {
  const payload = contract.methods
    .close(
      buyer.address,
      parseInt(createBlock),
      parseInt(amount),
      balanceSig,
      verifier.address,
      cid,
      verifySig
    )
    .encodeABI();
  const nonce = await web3.eth.getTransactionCount(seller.address);
  const tx = {
    nonce: nonce,
    from: seller.address,
    to: contract._address,
    gas: 315058,
    data: payload
  };
  const signed = await web3.eth.accounts.signTransaction(tx, seller.privateKey);
  const receipt = await web3.eth.sendSignedTransaction(signed.rawTransaction);
  console.info("tfr:", receipt);
  console.info("seller tokens:", await tokenBalance(seller.address));
  return receipt.blockNumber;
}

async function buyerAuthorization(buyer, seller, createBlock, amount) {
  const msg = await contract.methods
    .getBalanceMessage(seller.address, createBlock, amount)
    .call();
  return web3.eth.accounts.sign(msg, buyer.privateKey);
}

async function verifierAuthorization(seller, verifier, cid) {
  const msg = await contract.methods
    .getVerifyMessage(seller.address, cid)
    .call();
  return web3.eth.accounts.sign(msg, verifier.privateKey);
}

main().catch(error => {
  console.error(error);
});

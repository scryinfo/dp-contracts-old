"use strict";

const Web3 = require("web3");
const contracts = require("../build/contracts.json");
const deployments = require("../registrar.json").deployments;
const provider = new Web3.providers.HttpProvider("http://localhost:8545");
const web3 = new Web3(provider);
var Tx = require("ethereumjs-tx");

const registry = Object.values(deployments).reduce(
  (acc, ele) => (acc = Object.assign(acc, ele)),
  {}
);

const token = new web3.eth.Contract(
  contracts["ScryToken"].abi,
  registry["ScryToken"]
);
console.info("token:", token._address);

const privateKey =
  "0x3686e245890c7f997766b73a21d8e59f6385e1208831af3862574790cbc3d158";

const acct = web3.eth.accounts.privateKeyToAccount(privateKey);
console.info("acct:", acct.address);

async function main() {
  const coinbase = await web3.eth.getCoinbase();
  console.info("coinbase", coinbase);

  // send from coinbase to address
  // console.info("tokens:", await token.methods.balanceOf(acct.address).call());
  // const receipt1 = await token.methods
  //   .transfer(acct.address, 100)
  //   .send({
  //     from: coinbase
  //   });
  // console.info("token receipt:", receipt1);

  console.info("tokens:", await token.methods.balanceOf(acct.address).call());

  const nonce = await web3.eth.getTransactionCount(acct.address);
  console.info("nonce:", nonce);

  // send from address to coinbase
  const payload = token.methods.transfer(coinbase, 100).encodeABI();
  console.info("pld", payload);
  const tx = new Tx({
    nonce: nonce,
    from: acct.address,
    to: token._address,
    gas: 38121,
    // gasPrice: web3.utils.toWei("20", "gwei"),
    data: payload
  });
  tx.sign(Buffer.from(privateKey.slice(2), "hex"));
  const signed = "0x" + tx.serialize().toString("hex");
  // const signed = await web3.eth.signTransaction(tx, coinbase);
  console.info("signed", signed);

  const receipt = await web3.eth.sendSignedTransaction(signed);
  console.info("token receipt:", receipt);
  console.info("tokens:", await token.methods.balanceOf(acct.address).call());
}

main().catch(error => {
  console.error("error", error);
});

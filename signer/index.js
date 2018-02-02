"use strict";

const Contract = require("truffle-contract");
const Web3 = require("web3");
const Transaction = require("ethereumjs-tx");
const coder = require("web3/lib/solidity/coder");
const CryptoJS = require("crypto-js");
const Utils = require("ethereumjs-util");

const contracts = require("../build/contracts.json");
const deployments = Object.values(require("../registrar.json").deployments);
const provider = new Web3.providers.HttpProvider("http://localhost:8545");
const web3 = new Web3(provider);

const reg = deployments.reduce(
  (acc, ele) => (acc = Object.assign(acc, ele)),
  {}
);

async function main(args) {
  const Token = Contract(contracts["ScryToken"]);
  Token.setProvider(provider);
  const token = await Token.at(reg["ScryToken"]);

  const Scry = Contract(contracts["Scry"]);
  Scry.setProvider(provider);
  const scry = await Scry.at(reg["Scry"]);

  console.info("coinbase: ", web3.eth.coinbase);
  console.info(
    "coinbase token bal:",
    (await token.balanceOf.call(web3.eth.coinbase)).toNumber()
  );

  const privateKey =
    "0x3686e245890c7f997766b73a21d8e59f6385e1208831af3862574790cbc3d158";

  const acct = "0x" + Utils.privateToAddress(privateKey).toString("hex");
  console.info("acct:", acct);

  // give it an eth
  const fundHash = await web3.eth.sendTransaction({
    from: web3.eth.coinbase,
    value: 1,
    to: acct
  });
  console.info("fund receipt:", await web3.eth.getTransactionReceipt(fundHash));
  console.info("eth bal:", await web3.eth.getBalance(acct).toNumber());

  // give it some token
  console.info("token bal:", (await token.balanceOf.call(acct)).toNumber());
  const tfrHash = await token.transfer(acct, 100, { from: web3.eth.coinbase });
  console.info("token receipt:", tfrHash.receipt);
  console.info("token bal:", (await token.balanceOf.call(acct)).toNumber());

  const nonce = await web3.eth.getTransactionCount(acct);
  console.info("nonce:", nonce);

  const data = "0x" + encodeFunctionTxData("register", ["uint256"], [888]);
  console.info(data);

  const tx = new Transaction({
    to: acct,
    value: 0,
    nonce: nonce,
    data: data,
    gasLimit: 2000000
  });
  tx.sign(Buffer.from(privateKey.slice(2), "hex"));
  const signedRawTx = "0x" + tx.serialize().toString("hex");
  const txHash = await web3.eth.sendRawTransaction(signedRawTx);
  console.info("txHash:", txHash);

  const receipt = await web3.eth.getTransactionReceipt(txHash);
  console.info("receipt:", receipt);
}

function encodeFunctionTxData(functionName, types, args) {
  const fullName = functionName + "(" + types.join() + ")";
  const signature = CryptoJS.SHA3(fullName, { outputLength: 256 })
    .toString(CryptoJS.enc.Hex)
    .slice(0, 8);
  const dataHex = signature + coder.encodeParams(types, args);

  return dataHex;
}

main(process.argv)
  .then(done => {
    console.info("Done:", done);
  })
  .catch(error => {
    console.error("error", error);
  });

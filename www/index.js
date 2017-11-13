"use strict";

const Web3 = require("web3");
const Contracts = require("../build/contracts.json");
const Registrar = require("../registrar.json");

var _scry;
var _token;
Object.values(Registrar.deployments).forEach(element => {
  if (element.hasOwnProperty("Scry")) {
    _scry = element["Scry"];
  }
  if (element.hasOwnProperty("ScryToken")) {
    _token = element["ScryToken"];
  }
});
const http = "http://localhost:8545";
const ws = "ws://127.0.0.1:8546";
const ipc = "../chains/scrychain/chain_data/geth.ipc";

async function main() {
  // const web3 = new Web3(new Web3.providers.HttpProvider(http));
  // const web3 = new Web3(new Web3.providers.WebsocketProvider(ws));
  const web3 = new Web3(new Web3.providers.IpcProvider(ipc, require("net")));
  const acct = await web3.eth.getAccounts();
  console.log("acct:", acct);

  console.log("scry@", _scry);
  const scry = new web3.eth.Contract(Contracts.Scry.abi, _scry);

  console.log("token@", _token);
  const token = new web3.eth.Contract(Contracts.ScryToken.abi, _token);

  //   const bal = await scry.methods.getBalanceMessage(acct[0], 30, 10).call();
  //   console.log(bal);

  token.events.Transfer({}, (err, event) => {
    console.log(`Transfer:${JSON.stringify(event.returnValues)} err:${err}`);
  });

  scry.events.ChannelCreated({}, (err, event) => {
    console.log(
      `Created:${JSON.stringify(event.returnValues)}, 
      block:${event.blockNumber} err:${err}`
    );
  });
  scry.events.ChannelSettled({}, (err, event) => {
    console.log(`Settled:${JSON.stringify(event.returnValues)} err:${err}`);
  });
}

main().catch(console.error.bind(console));

const fs = require('fs');
const Web3 = require('web3');

const provider = new Web3.providers.WebsocketProvider('ws://blockchain:8546');
const web3 = new Web3(provider);

web3.eth.getBlock("latest").then(block => {
    console.log("gasLimit: " + block.gasLimit);
});

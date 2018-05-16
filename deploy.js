const fs = require('fs');
const Web3 = require('web3');

const provider = new Web3.providers.WebsocketProvider('ws://localhost:8546');
const web3 = new Web3(provider);

let coinbase = ""

async function deploy(cname, args) {
    const js = require("./build/contracts/" + cname + ".json");
    const contract = new web3.eth.Contract(js.abi);
    const deployment = await contract.deploy({
            data: js.bytecode,
            arguments: args,
        }).send({
            from: coinbase,
            gas: 4712388,
        }, function (error, transactionHash) {})
        .on('error', function (error) {
            throw error;
        })
        .on('transactionHash', function (transactionHash) {
            console.log('hash:', transactionHash)
        })
        .on('receipt', function (receipt) {
            console.log('receipt:', receipt)
        })
        .on('confirmation', function (confirmationNumber, receipt) {
            console.log('confirm"', confirmationNumber, 'receipt', receipt)
        });
    return deployment._address
}

async function main() {
    const network = await web3.eth.net.getId();
    console.log("network:", network)

    coinbase = await web3.eth.getCoinbase();
    console.log("coinbase:", coinbase)

    // deploy contracts
    const deployed = {}
    deployed['ScryToken'] = await deploy("ScryToken", [1000000])
    deployed['Scry'] = await deploy('Scry', [deployed['ScryToken']])

    // load deployments file
    let deployments = {};
    try {
        deployments = JSON.parse(fs.readFileSync("./deployments.json").toString());
    } catch (ex) {
        console.warn(ex.message)
    }

    deployments[network] = deployed;
    fs.writeFileSync("./deployments.json", JSON.stringify(deployments));
    console.log("deployed:", deployments);
    process.exit(0);
}

main();
const Web3 = require('web3');
const {
    padLeft
} = require('web3-utils');

const ops = require("../build/js/chainOps");

const debug = require('debug')('test');

const buyerKey =
    '0xa518652e06e57e6d9e9ff93ad5eef2892415a9735ff14c246eff301342c8e0f7';
const sellerKey =
    '0x80ea726eaa53b661b558c9be7d752c8521719b9f018fd7c3d102020580a61d0f';

const verifierKey =
    '0x4948deb9bd1ce66e05dcfe500583220b252ac221bae030cde498ba6732e5d58d';

const cid = 'QmZ3gZXbckAxfJafysmmoNPwx67WiaLdqoYCxrnVWNeJ7R';

let web3;
let token;
let contract;
let coinbase;

async function main() {
    const chain = await ops.initChain();
    web3 = chain.web3;
    token = chain.token;
    contract = chain.contract;

    coinbase = await web3.eth.getCoinbase();

    const buyer = web3.eth.accounts.privateKeyToAccount(buyerKey);
    debug('buyer:', buyer.address);

    const seller = web3.eth.accounts.privateKeyToAccount(sellerKey);
    debug('seller:', seller.address);
    const verifier = web3.eth.accounts.privateKeyToAccount(verifierKey);
    debug('verifier:', verifier.address);

    // debug("token gift:", await sendToken(coinbase, buyer.address, 100));
    // debug("eth gift", await sendEth(coinbase, buyer.address, "0.1"));

    const createBlock = await openChannel(10, buyer, seller, 1, 1);
    debug('opened @:', createBlock);

    const ba = await buyerAuthorization(buyer, seller, createBlock, 10);
    debug('ba:', ba);
    const va = await verifierAuthorization(seller, verifier, cid);
    debug('va:', va);

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
    debug('closed @:', closed);
}

async function openChannel(amount, buyer, seller, reward, verifiers) {
    debug('buyer balance:', await ops.tokenBalance(buyer.address), await ops.ethBalance(buyer.address));
    debug('seller balance:', await ops.tokenBalance(seller.address), await ops.ethBalance(seller.address));

    const hx =
        '0x' +
        seller.address.slice(2) +
        padLeft(reward, 8).slice(2) +
        padLeft(verifiers, 8).slice(2);

    const payload = token.methods
        .transfer(contract._address, amount, hx)
        .encodeABI();

    const receipt = await signAndSend(buyer.address, buyer.privateKey, token._address, 198579, payload)
    debug('open receipt:', receipt);
    debug('buyer balance:', await ops.tokenBalance(buyer.address), await ops.ethBalance(buyer.address));
    debug('seller balance:', await ops.tokenBalance(seller.address), await ops.ethBalance(seller.address));
    return receipt.blockNumber;
}

async function closeChannel(buyer,
    seller,
    verifier,
    createBlock,
    cid,
    amount,
    balanceSig,
    verifySig
) {
    debug('buyer balance:', await ops.tokenBalance(buyer.address), await ops.ethBalance(buyer.address));
    debug('seller balance:', await ops.tokenBalance(seller.address), await ops.ethBalance(seller.address));
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
    // debug('payload:', payload);

    const receipt = await signAndSend(seller.address, seller.privateKey, contract._address, 315058, payload)
    debug('close receipt:', receipt);
    debug('buyer balance:', await ops.tokenBalance(buyer.address), await ops.ethBalance(buyer.address));
    debug('seller balance:', await ops.tokenBalance(seller.address), await ops.ethBalance(seller.address));
    debug('verifier balance:', await ops.tokenBalance(verifier.address), await ops.ethBalance(verifier.address));
    return receipt.blockNumber;
}

async function signAndSend(from, fromKey, to, gas, payload) {
    const _nonce = await ops.nonce(from);
    const tx = {
        nonce: _nonce,
        from: from,
        to: to,
        gas: gas,
        data: payload
    };
    const signed = await web3.eth.accounts.signTransaction(tx, fromKey);
    debug('signed:', signed);
    return await ops.rawTx(signed.rawTransaction);
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
    debug(error);
    process.exit(-1)
})
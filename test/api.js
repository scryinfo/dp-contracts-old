const Web3 = require('web3');
const axios = require('axios');

const {
    padLeft
} = require('web3-utils');

const ops = require("../build/js/chainOps");

const debug = require('debug')('server:test');

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
let gasPrice;
let chainId;

let jwt;

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

    // debug("token gift:", await ops.sendToken(coinbase, buyer.address, 100));
    // debug("eth gift", await ops.sendEth(coinbase, buyer.address, "0.1"));

    // register
    // const accounts = await Promise.all([
    //     await register('buyer', 'seller', buyer.address),
    //     await register("seller", 'seller', seller.address),
    //     await register('verifier', 'verifier', verifier.address),
    // ]);

    // login
    const accounts = await Promise.all([
        await login('buyer', 'seller'),
        await login("seller", 'seller'),
        await login('verifier', 'verifier'),
    ]);
    jwt = accounts.map((it) => it.data).reduce((acc, it) => {
        acc[it.account] = it.token;
        return acc
    }, {})
    debug("jwt", jwt);

    chainInfo(buyer.address)
    const amt = "2";
    const reward = 1;

    const createBlock = await openChannel(amt, buyer, seller, reward, 1);
    debug('opened @:', createBlock);

    const ba = await buyerAuthorization(buyer, seller, createBlock, amt);
    debug('ba:', ba.signature);

    // create po
    const purchase = await savePurchase(7, buyer.address, seller.address, reward, createBlock, ba.signature);
    debug('purchase', purchase.data)

    const va = await verifierAuthorization(seller, verifier, cid);
    debug('va:', va.signature);
    // save verification
    const saveVa = await saveVerification(verifier.address, purchase.data.id, va.signature)
    debug('purchase', saveVa.data)

    const closed = await closeChannel(purchase.data.id,
        buyer.address,
        seller,
        verifier.address,
        createBlock,
        cid,
        amt,
        ba.signature,
        va.signature
    );
    debug('closed @:', closed);
}

// api calls
const HOST = 'http://127.0.0.1:1234';

const login = (username, password) =>
    axios.post(`${HOST}/login`, {
        username,
        password,
    });

const register = (username, password, account) =>
    axios.post(`${HOST}/signup`, {
        username,
        password,
        account,
    });

async function nonce(from) {
    const {
        data: {
            nonce
        }
    } = await axios.get(`${HOST}/nonce/${from}`, {
        headers: {
            JWT: jwt[from]
        },
    });
    debug(`nonce:${from}`, nonce)
    return nonce;
}

async function chainInfo(account) {
    ({
        data: {
            gasPrice,
            chainId
        }
    } = await axios.get(`${HOST}/chainInfo`, {
        headers: {
            JWT: jwt[account]
        },
    }));
    debug(`gas:${gasPrice} chain:${chainId}`);
}
async function rawTx(raw, from) {
    const resp = await axios({
        method: 'post',
        url: `${HOST}/rawTx`,
        data: {
            data: raw,
        },
        headers: {
            JWT: jwt[from]
        },
    });
    return resp.data
}

async function closeTx(id, data, from) {
    const resp = await axios({
        method: 'post',
        url: `${HOST}/seller/close`,
        data: {
            id,
            data,
        },
        headers: {
            JWT: jwt[from]
        },
    });
    return resp.data
}

const savePurchase = (listing, buyer, verifier, rewards, createBlock, buyerAuth) => axios({
    method: 'post',
    url: `${HOST}/buyer/purchase`,
    data: {
        listing,
        buyer,
        verifier,
        rewards,
        createBlock,
        buyerAuth,
    },
    headers: {
        JWT: jwt[buyer]
    },
});

const saveVerification = (verifier, item, verifierAuth) => axios({
    method: 'post',
    url: `${HOST}/verifier/sign`,
    data: {
        item,
        verifierAuth
    },
    headers: {
        JWT: jwt[verifier]
    },
});

async function closeChannel(id,
    buyerAddress,
    seller,
    verifierAddress,
    createBlock,
    cid,
    amount,
    balanceSig,
    verifySig
) {
    debug('buyer balance:', await ops.tokenBalance(buyerAddress), await ops.ethBalance(buyerAddress));
    debug('seller balance:', await ops.tokenBalance(seller.address), await ops.ethBalance(seller.address));
    debug('verifier balance:', await ops.tokenBalance(verifierAddress), await ops.ethBalance(verifierAddress));
    const payload = contract.methods
        .close(
            buyerAddress,
            createBlock,
            amount,
            balanceSig,
            verifierAddress,
            cid,
            verifySig
        )
        .encodeABI();
    // debug('payload:', payload);

    // sing
    const _nonce = await nonce(seller.address);
    const tx = {
        chainId,
        gasPrice,
        nonce: _nonce,
        from: seller.address,
        to: contract._address,
        gas: 315058,
        data: payload
    };
    const signed = await web3.eth.accounts.signTransaction(tx, seller.privateKey);
    // debug('signed:', signed);
    const {
        purchase,
        receipt
    } = await closeTx(id, signed.rawTransaction, seller.address);
    debug('close purchase', purchase)
    debug('close receipt:', receipt.transactionHash, receipt.blockNumber, receipt.gasUsed);

    debug('buyer balance:', await ops.tokenBalance(buyerAddress), await ops.ethBalance(buyerAddress));
    debug('seller balance:', await ops.tokenBalance(seller.address), await ops.ethBalance(seller.address));
    debug('verifier balance:', await ops.tokenBalance(verifierAddress), await ops.ethBalance(verifierAddress));
    return receipt.blockNumber;
}

// direct calls

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
    debug('open receipt:', receipt.transactionHash, receipt.blockNumber, receipt.gasUsed);
    debug('buyer balance:', await ops.tokenBalance(buyer.address), await ops.ethBalance(buyer.address));
    debug('seller balance:', await ops.tokenBalance(seller.address), await ops.ethBalance(seller.address));
    return receipt.blockNumber;
}

async function signAndSend(from, fromKey, to, gas, payload) {
    const _nonce = await nonce(from);
    const tx = {
        chainId,
        gasPrice,
        nonce: _nonce,
        from: from,
        to: to,
        gas: gas,
        data: payload
    };
    const signed = await web3.eth.accounts.signTransaction(tx, fromKey);
    // debug('signed:', signed);
    return rawTx(signed.rawTransaction, from);
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
    console.dir(error);
    process.exit(-1)
})
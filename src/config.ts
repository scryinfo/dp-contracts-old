require('dotenv').config();

const config = {
 parityUri: process.env.PARITY_URI,
 ipfsHost: process.env.IPFS_HOST,
 ipfsPort: process.env.IPFS_PORT,
 ipfsProtocol: process.env.IPFS_PROTOCOL
};

module.exports = config;

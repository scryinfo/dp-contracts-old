module.exports = {
  networks: {
    development: {
      host: 'localhost',
      port: 9545,
      network_id: '*' // Match any network id
    },
    dev: {
      host: '127.0.0.1',
      port: 8545,
      network_id: '*', // Match any network id
      gas: 4712388,
      from: '0x84de23c456c5a9cbd377a35ad3b0d9360191f42f'
    }
  }
};

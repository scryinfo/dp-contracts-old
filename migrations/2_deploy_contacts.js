const Token = artifacts.require('ScryToken');
const Scry = artifacts.require('Scry');

module.exports = function(deployer) {
  deployer.deploy(Token, 1000000000);
  console.log('Done');
};

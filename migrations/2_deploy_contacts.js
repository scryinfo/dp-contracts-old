const Token = artifacts.require('ScryToken');
const Scry = artifacts.require('Scry');

module.exports = function(deployer) {
  deployer
    .deploy(Token, 1000)
    .then(() => {
      console.log(`Token@: ${Token.address}`);
      return deployer.deploy(Scry, Token.address);
    })
    .then(() => {
      console.log(`Scry@: ${Scry.address}`);
    });
  console.log('Done');
};

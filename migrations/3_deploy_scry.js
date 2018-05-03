const Token = artifacts.require('ScryToken');
const Scry = artifacts.require('Scry');

module.exports = function(deployer) {
  console.log(`Token@: ${Token.address}`);
  deployer.deploy(Scry, Token.address).then(() => {
    console.log(`Scry@: ${Scry.address}`);
  });
  console.log('Done');
};

const Token = artifacts.require("ScryToken");
const Scry = artifacts.require("Scry");

module.exports = function(deployer, accounts) {
  deployer.deploy(Token, 1000).then(() => {
    deployer.deploy(Scry, Token.address);
  });
};

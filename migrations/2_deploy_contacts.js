const Token = artifacts.require("ScryToken");

module.exports = function(deployer, accounts) {
  deployer.deploy(Token, 1000);
};

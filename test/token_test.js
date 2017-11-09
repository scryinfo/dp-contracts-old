const Token = artifacts.require("ScryToken");

contract("ScryToken", accounts => {
  it("should deploy and have correct balances", async () => {
    const deployed = await Token.deployed();
    console.info("deployed at: ", deployed.address);
    const owner = await deployed.owner();
    console.info("deployed by: ", owner);
    const total = await deployed.totalSupply.call();
    const balance = await deployed.balanceOf.call(owner);
    console.info("bal:", balance.toNumber());
    assert.equal(balance.toNumber(), total.toNumber(), "bad balance");
  });

  it("should transfer to another account", async accounts => {
    const deployed = await Token.deployed();
    console.info("deployed at: ", deployed.address);

    const res = await deployed.transfer(accounts[1], 100, {
      from: accounts[0]
    });
    console.info("res:", res);
    assert.equal(res, true);
    const bal = await deployed.balanceOf.call(accounts[1]);
    assert.equal(bal.toNumber(), 100, "correct balance");
  });
});

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

  it("should transfer to another account", done => {
    let deployed;
    return Token.deployed()
      .then(res => {
        deployed = res;
        console.info("deployed at: ", deployed.address);
      })
      .then(() => {
        return deployed.balanceOf.call(accounts[0]).then(bal => {
          console.info(`balance: ${bal}`);
        });
      })
      .then(() => {
        const to = accounts[1];
        console.info("send to: ", to);
        return deployed.transfer(to, 100);
      })
      .then(res => {
        console.info("res:", res);
        assert.equal(res, true);
        return deployed.balanceOf.call(to);
      })
      .then(bal => {
        assert.equal(bal.toNumber(), 100, "correct balance");
      });
  });
});

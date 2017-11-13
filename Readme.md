This directory contains the Proof Of Concept for some of the ideas put forth in the Scry.Info whitepaper.

# Development

We use the python framework populus.
```
pip[3] install -U populus
```
See basic [tutorials](http://populus.readthedocs.io/en/latest/tutorial.html) for usage 

## Running the tests
The tests in test_contract_simple.py run with with in-built 'tester' chain.

The tests in test_contract.py require a 'Geth' based external chain that needs to be started separately. 'Geth' needs to installed using [insctructions](https://github.com/ethereum/go-ethereum/wiki/Building-Ethereum).
A 'reset.sh' script will start a locally configured chain with the setup required for the tests.

Why exactly was a Geth based chain required? 

The local 'tester' chain uses a python implementation of ethereum that does not implement the 'eth_sign' message.

A problem with using Geth solo is that transactions get stuck [Bug](https://github.com/ethereum/go-ethereum/issues/3694). We should probably figure out a way to use Parity.

## Imported Code
Contracts/Token directory contains standard erc223 token imported from github.com/Dexaran/ERC223-token-standard.git .

It was imported using a subtree merge
```
git subtree add --prefix contracts/token erc223-token-standard Recommended --squash
```
and can be updated using
```
subtree pull --prefix contracts/token erc223-token-standard Recommended --squash
```

Scry.sol contract borrows code from the Raiden & MicroRaiden projects.
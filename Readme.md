# Development

Truffle is required.
```
npm -g install truffle
```
 See basic [tutorials](http://truffleframework.com/tutorials/debugging-a-smart-contract) for usage 

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

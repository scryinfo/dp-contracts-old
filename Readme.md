This directory contains the Proof Of Concept for some of the ideas put forth in the Scry.Info whitepaper.

# Development

We use the python framework populus.
```
pip[3] install -U populus
```
See basic [tutorials](http://populus.readthedocs.io/en/latest/tutorial.html) for usage 

# REST endpoints

The python server *sever.py* provides REST endpoints.

The server require a *Geth* based external chain that needs to be started separately. 'Geth' needs to installed using [insctructions](https://github.com/ethereum/go-ethereum/wiki/Building-Ethereum).
A *reset.sh* script will start a locally configured chain with the setup required for the tests.

Why exactly was a Geth based chain required? 

The local *tester* chain uses a python implementation of ethereum that does not implement the *eth_sign* message.

A problem with using Geth solo is that transactions get stuck [Bug](https://github.com/ethereum/go-ethereum/issues/3694). We should probably figure out a way to use Parity.

An example session can work like this:

- Buyer acquires SCRY tokens:
```
curl localhost:5000/buyer/fund
{
  "balance": 100
}
```
- Buyer opens channel to Seller:
```
curl localhost:5000/buyer/channel
{
  "create_block": 1418
}
```
- Buyer signs authorization to pay Seller
```
curl localhost:5000/buyer/sign?block=1418
{
  "balance_sig": "aabc0673229de2bb056a8745b93636128483812a0cc66da3c8b95ae91c47f055522b9a3d13f92ddb87d08319a2cd4b10d6b845b1b705391e7fa3f610b7f1f7d41b"
}
```
- Buyer's authorization is transferred to Seller, and he verifies that it is correct
```
curl localhost:5000/seller/verify_balance?create_block=1418&balance_sig=aabc0673229de2bb056a8745b93636128483812a0cc66da3c8b95ae91c47f055522b9a3d13f92ddb87d08319a2cd4b10d6b845b1b705391e7fa3f610b7f1f7d41b
{
    "verification":"OK"
}
```
- Seller creates the data, and uploads it to IPFS. Seller's asks the Verifier to verify and sign the ipfs CID
```
curl localhost:5000/verifier/sign?CID=QmPrafFmEqqQDUgepoVShKUDzdxWtd8UtwA211RE47LBZd
{
  "verification_sig": "4471e812f37b3d50808fde347e21f8c838df657da29a1ac126a2f85bbd4847b71de516f4ca8d2b26587f4ddc0ac2b78cf18cb03a12097800cbb281f26e5c2ada1b"
}
```
- Seller verifies if the signature is OK - TODO
- Seller takes both signatures and closes the transaction. The Buyer's rewards are distributed
```
curl "localhost:5000/seller/close?CID=QmPrafFmEqqQDUgepoVShKUDzdxWtd8UtwA211RE47LBZd&balance_sig=aabc0673229de2bb056a8745b93636128483812a0cc66da3c8b95ae91c47f055522b9a3d13f92ddb87d08319a2cd4b10d6b845b1b705391e7fa3f610b7f1f7d41b&verification_sig=4471e812f37b3d50808fde347e21f8c838df657da29a1ac126a2f85bbd4847b71de516f4ca8d2b26587f4ddc0ac2b78cf18cb03a12097800cbb281f26e5c2ada1b&create_block=1418"
{
  "close_block": 1778
}
```

**TODO**
- Add ability to check buyer, seller & verifier accounts
- Add UI

## Running the tests
The tests in test_contract_simple.py run with with in-built *tester* chain.

The tests in test_contract.py require a *Geth* based external chain that needs to be started separately. 

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
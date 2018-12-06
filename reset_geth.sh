# This was used when we were using geth as ethereum client.
rm -rf chains/scrychain/chain_data/geth/chaindata
rm -rf chains/scrychain/chain_data/geth/nodekey
rm registrar.json
./chains/scrychain/init_chain.sh
./chains/scrychain/run_chain.sh

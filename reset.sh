rm -rf chains/scrychain/chain_data/geth/chaindata
rm -rf chains/scrychain/chain_data/geth/nodekey
rm registrar.json
./chains/scrychain/init_chain.sh
./chains/scrychain/run_chain.sh
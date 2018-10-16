#!/bin/sh
geth \
    --rpc --rpcaddr 0.0.0.0 --rpcport 8545 --rpccorsdomain="*" \
    --rpcapi admin,debug,eth,miner,net,personal,shh,txpool,web3,ws \
    --ws --wsaddr 0.0.0.0 --wsport 8546 --wsorigins="*" \
    --wsapi admin,debug,eth,miner,net,personal,shh,txpool,web3,ws \
    --datadir /root/chains/scrychain/chain_data \
    --maxpeers 0 --networkid 1234 --port 30303 \
    --ipcpath /root/chains/scrychain/chain_data/geth.ipc \
    --unlock 0xcb85348529b63dae26f343459d2ab3e01fcce1ca,0x299d98f2e85f08437399c1d8136b25d4cd36fde8,0xe9f3c5f986a26125ee033205bbe33e4ecaeb83a6,0xa6bcf5ab7e2266bff59cc3eab4cf01c1326694e4 \
    --password /root/chains/scrychain/password \
    --nodiscover --mine --minerthreads 1 \
    --targetgaslimit '9000000000000' \
    $*
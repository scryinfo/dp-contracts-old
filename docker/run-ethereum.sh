#!/bin/sh
DIRNAME=`dirname $0`
export ethereum_data=`realpath -m $DIRNAME/../ethereum/data`

mkdir -p $ethereum_data 

docker run -d \
    --name ethereum-node \
    -v $ethereum_data:/root \
	-p 8545:8545 -p 30303:30303 \
    ethereum/client-go
    
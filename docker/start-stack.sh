#!/bin/sh
DIRNAME=`dirname $0`
mkdir -p $DIRNAME/data/ipfs/staging $DIRNAME/data/ipfs/data $DIRNAME/data/ethereum $DIRNAME/data/postgres
docker stack deploy -c $DIRNAME/docker-compose.yml scryinfo
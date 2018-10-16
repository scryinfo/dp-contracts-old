#!/bin/sh
DIRNAME=`dirname $0`
export ipfs_staging=`realpath -m $DIRNAME/../ipfs/staging`
export ipfs_data=`realpath -m $DIRNAME/../ipfs/data`

mkdir -p $ipfs_staging
mkdir -p $ipfs_data 

docker run -d \
    --name ipfs_host \
    -v $ipfs_staging:/export \
    -v $ipfs_data:/data/ipfs \
    -p 4001:4001 -p 127.0.0.1:8080:8080 -p 127.0.0.1:5001:5001 \
    ipfs/go-ipfs:latest
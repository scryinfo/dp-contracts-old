#!/bin/bash
CONTAINER=`docker ps -q --filter="name=scryinfo_blockchain"`
if test -z "$CONTAINER"; then echo "no container found"; exit 1; fi
docker exec -it \
    --workdir=/root \
    $CONTAINER \
    /bin/sh
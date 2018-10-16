#!/bin/sh
DIRNAME=`dirname $0`
export data=`realpath -m $DIRNAME/../postgres/data`

mkdir -p $data 
export PGDATA=/var/lib/postgresql/data/pgdata
docker run -d \
    --name postgres \
    -e PGDATA=$PGDATA \
    -v $data:$PGDATA \
   postgres
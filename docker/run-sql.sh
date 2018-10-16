#!/bin/sh
CONTAINER=`docker ps -a -q --filter="name=scryinfo_db"`
docker cp ./$1 $CONTAINER:/tmp/$1
docker exec -u postgres $CONTAINER psql postgres -f /tmp/$1
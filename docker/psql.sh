#!/bin/sh

CONTAINER=`docker ps -q --filter="name=scryinfo_db"`
docker exec -it $CONTAINER psql -U scry scry

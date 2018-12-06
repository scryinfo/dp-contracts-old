#!/bin/sh
docker cp ./$1 $CONTAINER:/tmp/$1
docker exec -u postgres postgres psql postgres -f /tmp/$1

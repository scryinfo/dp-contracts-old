#!/bin/bash
docker run -it \
    -e "NODE_ENV=production" \
    --workdir=/root/scry \
    --link scryinfo_blockchain \
    --link scryinfo_dfs \
    --link scryinfo_db \
    --init \
    scryinfo/scry
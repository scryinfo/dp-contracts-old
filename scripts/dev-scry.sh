#!/bin/bash
docker run -it \
    --name=scry \
    --entrypoint=/bin/bash \
    --mount type=bind,source="$(pwd)",target="/root/scry" \
    --network scryinfo_default \
    scryinfo/scry
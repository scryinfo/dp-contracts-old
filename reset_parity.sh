rm -rf chains/p/chain_data/
docker run -ti -p 8180:8180 -p 8545:8545 -p 8546:8546 -p 30303:30303 -p 30303:30303/udp parity/parity:v1.8.3 --config chains/p/parity.toml --peers 0 --unlock 0x84de23c456c5a9cbd377a35ad3b0d9360191f42f,0xa77082957d1345f19d0a05050f49f5a76e31a055,0xb484d10180d7893bad4825299b09b66bb6929ea9,0xd372eab3c4e20442431652123bbaa8c4d9700313 --password chains/p/password
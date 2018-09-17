This directory contains the Proof Of Concept for some of the ideas put forth in
the Scry.Info whitepaper.

# Requirements

- Node JS LTS +
- yarn
- Parity 1.10+
- Postgresql 10.x
- [IPFS](https://github.com/ipfs/go-ipfs) should be installed & running as deamon.


# Development

Install node deps :

```bash
yarn
yarn global add truffle
psql
   CREATE DATABASE scry;
   \connect scry;
   CREATE SCHEMA scry2;
```


Run IPFS

```bash
ipfs daemon
```

Run ethereum client:

```bash
./reset_parity.sh
```

Compile contract:

```bash
truffle compile
```

Deploy contracts:

```bash
node deploy.js
```

Start server:

```bash
yarn dev
```
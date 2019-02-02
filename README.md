# Overview
The Proof Of Concept for some of the ideas put forth in the Scry.Info whitepaper is implemented in following three projects: 
- scry-server [scryInfo/scry](https://github.com/scryInfo/scry) 
- frontend [cryInfo/scry-frontend](https://github.com/scryInfo/scry-frontend)
- publishing backend [publisher-backend](https://github.com/scryInfo/publisher-backend)

# Running with docker

Preferred way to run the scry-server is in docker. The docker-compose.yml file here creates an environment with scry-server and all its dependencies (ipfs, parity, postgresql)

1. Install Docker: https://docs.docker.com/install/. If you are on Ubuntu 16.04, do not use docker contained in the Ubuntu repositories, it is too old. Follow this howto: https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-16-04
2. Copy the `.env.example` configuration file to `.env` (for local runs) and to `.env.docker` (will be used in the scry-server container:
```
cp .env.example .env
cp .env.example .env.docker
[and edit them with your favourite text editor to match your environment]
```
2. Create directories for permanent storage:
```
bash docker/create-data-dirs.sh
```
3. Build+start the environment using docker-compose. Important notes:
- **docker-compose must always be run in the directory where the docker-compose.yml is located**
- **If you have local instance of parity, postgresql or ipfs running, stop them before starting those containers**
- -d means "detached" - the containers will continue to run in background and will not block your terminal
```
docker-compose up -d
```
This will create four containers (check docker-compose.yml for more details):
* **postgres**, with postresql user "scry", password "scry", owning database "scry" with schema "scry2". Permanent storage in directory `docker/data/postgres/`
* **ipfs**, permanent storage in directory `docker/data/ipfs/`
* **parity**, permanent storage in `chains/` (this repo's `chains/` directory is attached to the container's `/root/chains/`)
* **scry-server**, which is built using the Dockerfile in the current working directory (which should be the root of this repo). No permanent storage, the content of this repo is copied into the container when it is being built
4. Deploy the contracts:
```
docker-compose exec scry-server node /home/node/scry-server/deploy.js
```

## stopping and restarting the stack

The containers create files in the persistent folders that can not be read by the user you run docker with (only by root). To be able to rebuild the containers (after a change), you have to clean the data dirs as root (using sudo):

```
docker-compose down // stop the environment
sudo bash docker/clean-data-dirs.sh
docker-compose up --build
```

## developing with docker

### useful docker commands

**docker-compose must always be run in the directory where the docker-compose.yml is located**

* `docker-compose ps` - shows current status of the services
* `docker-compose logs --tail 5 -f scry-server` - will show last 5 log entries of scry-server, and will follow the log output
* `docker-compose exec container_name /bin/bash` - get shell inside the container. `container_name` can be scry-server, postgres, ipfs, parity. Instead of /bin/bash you can run any command you want.
* `docker-compose stop scry-server` - will stop only one container
* `docker-compose up -d scry-server --build` - will rebuild and start only one container
* `docker-compose down` - take the whole stack down

### clean run

The postgres, ipfs and parity containers use permanent storage by attaching host (your computer) directories into the containers. If you want to start clean, first take the environment down, then clean the data dirs, and bring the environment back up:

```
docker-compose down
sudo bash docker/clean-data-dirs.sh    // removes ipfs, postgres and parity's chain_data with rm -rf
docker-compose up -d --build      // rebuilds the containers if there were any changes
                                  // in code or in docker-compose.yml and starts the environment again
```

### attaching the repo you are working on locally into the scry-server container

Should be possible, haven't tried. Uncomment following lines in docker-compose.yml:
```
#    volumes:
#      - .:/home/node
```

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

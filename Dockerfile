# look at best practices document to understand why we use multi-stage build: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/

#
# ---- Base Node Image ----
FROM node:8 AS base
# use non-root "node user"
USER node
# set working directory
RUN mkdir -p /home/node/scry-server
WORKDIR /home/node/scry-server
# copy project file
COPY --chown=node:node package.json .

#
# ---- Dependencies ----
FROM base AS dependencies
# install node packages
RUN npm set progress=false && npm config set depth 0
RUN npm install --only=production
# copy production node_modules aside
RUN cp -R node_modules prod_node_modules
# install ALL node_modules, including 'devDependencies'
RUN npm install

#
# ---- Tests ----
# run linters, setup and tests
#FROM dependencies AS test
#COPY . .
#RUN npm run build
#RUN  npm run lint && npm run setup && npm run test
#RUN ./node_modules/.bin/truffle compile

#
# ---- Release ----
FROM base AS release
# copy production node_modules
COPY --chown=node:node --from=dependencies /home/node/scry-server/prod_node_modules ./node_modules
# copy app sources
COPY --chown=node:node . .
# put the correct .env file in place
RUN cp .env.docker .env
# compile contract - should this be here?
RUN ./node_modules/.bin/truffle compile
# expose port and define ENTRYPOINT and default CMD
EXPOSE 1234
ENTRYPOINT ["yarn"]
CMD ["dev"]

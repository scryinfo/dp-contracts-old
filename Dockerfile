# ---- Base Node ----
FROM node:8 AS base
# set working directory
WORKDIR /root/scry
# copy project file
COPY package.json .
 
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
# ---- Test ----
# run linters, setup and tests
FROM dependencies AS test
COPY . .
RUN npm run build
#RUN  npm run lint && npm run setup && npm run test
RUN ./node_modules/.bin/truffle compile
 
#
# ---- Release ----
FROM base AS release
# copy production node_modules
COPY --from=dependencies /root/scry/prod_node_modules ./node_modules
# copy app sources
COPY . .
# expose port and define CMD
EXPOSE 1234
CMD npm start
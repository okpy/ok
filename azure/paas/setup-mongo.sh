#!/usr/bin/env bash

. ./utils.sh; az_login

if [ -f ./secrets/mongo.env ]; then log "Already exists: mongo"; exit 0; fi

#
# verify inputs
#

mongo_name="${OK_NAME}mongo"
mongo_database="ok"
deployment_log="$(mktemp)"

#
# create resource
#

log "Creating resource ${mongo_name}"

az group deployment create \
  --name "${mongo_name}" \
  --template-file './arm/mongo.deploy.json' \
  --parameters \
      "mongoAccountName=${mongo_name}" \
| tee "${deployment_log}"

mongo_host="$(jq -r '.properties.outputs.mongoHost.value' "${deployment_log}")"
mongo_password="$(jq -r '.properties.outputs.mongoPassword.value' "${deployment_log}")"

az cosmosdb database create \
  --db-name "${mongo_database}" \
  --key "${mongo_password}" \
  --url-connection "https://${mongo_host}"

#
# store secrets
#

cat > ./secrets/mongo.env << EOF
MONGO_DATABASE=${mongo_database}
MONGO_USERNAME=${mongo_name}
MONGO_PASSWORD=${mongo_password}
MONGO_HOST=${mongo_host}
MONGO_PORT=10255
EOF

log "Done with ${mongo_name}"

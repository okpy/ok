#!/usr/bin/env bash

. ./utils.sh; az_login

if [ -f ./secrets/storage.env ]; then log "Already exists: storage"; exit 0; fi

#
# verify inputs
#

storage_name="${OK_NAME}storage"
deployment_log="$(mktemp)"

#
# create resource
#

log "Creating resource ${storage_name}"

az group deployment create \
  --name "${storage_name}" \
  --template-file './arm/storage.deploy.json' \
  --parameters \
      "storageAccountName=${storage_name}" \
| tee "${deployment_log}"

#
# store secrets
#

storage_key="$(jq -r '.properties.outputs.storageKey.value' "${deployment_log}")"
storage_connection_string="DefaultEndpointsProtocol=https;AccountName=${storage_name};AccountKey=${storage_key};EndpointSuffix=core.windows.net"

cat > ./secrets/storage.env << EOF
STORAGE_ACCOUNT_NAME=${storage_name}
STORAGE_ACCOUNT_KEY=${storage_key}
STORAGE_CONNECTION_STRING=${storage_connection_string}
EOF

log "Done with ${storage_name}"

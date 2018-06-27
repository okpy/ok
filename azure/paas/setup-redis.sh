#!/usr/bin/env bash

. ./utils.sh; az_login

if [ -f ./secrets/redis.env ]; then log "Already exists: redis"; exit 0; fi

#
# verify inputs
#

redis_name="${OK_NAME}redis"
deployment_log="$(mktemp)"

#
# create resource
#

log "Creating resource ${redis_name}"

az group deployment create \
  --name "${redis_name}" \
  --template-file './arm/redis.deploy.json' \
  --parameters \
      "redisAccountName=${redis_name}" \
| tee "${deployment_log}"

#
# store secrets
#

redis_host="$(jq -r '.properties.outputs.redisHost.value' "${deployment_log}")"
redis_password="$(jq -r '.properties.outputs.redisPassword.value' "${deployment_log}")"

cat > ./secrets/redis.env << EOF
REDIS_PASSWORD=${redis_password}
REDIS_HOST=${redis_host}
REDIS_PORT=6380
EOF

log "Done with ${redis_name}"

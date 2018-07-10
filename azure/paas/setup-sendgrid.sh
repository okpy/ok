#!/usr/bin/env bash

. ./utils.sh; az_login

if [ -f ./secrets/sendgrid.env ]; then log "Already exists: sendgrid"; exit 0; fi

#
# verify inputs
#

sendgrid_name="${OK_NAME}mail"
sendgrid_password="$(generate_password 32)"
deployment_log="$(mktemp)"
sendgrid_log="$(mktemp)"

#
# create resource
#

log "Creating resource ${sendgrid_name}"

az group deployment create \
  --name "${sendgrid_name}" \
  --template-file './arm/sendgrid.deploy.json' \
  --parameters \
      "sendgridAccountName=${sendgrid_name}" \
      "sendgridPassword=${sendgrid_password}" \
| tee "${deployment_log}"

#
# store secrets
#

sendgrid_username="$(jq -r '.properties.outputs.sendgridUserName.value' "${deployment_log}")"

curl \
  --fail \
  --data '{"name": "'"${sendgrid_name}"'", "scopes": ["mail.send"]}'  \
  --header 'Content-Type: application/json' \
  --user "${sendgrid_username}:${sendgrid_password}" \
  'https://api.sendgrid.com/v3/api_keys' \
| tee "${sendgrid_log}"

sendgrid_key="$(jq -r '.api_key' "${sendgrid_log}")"

cat > ./secrets/sendgrid.env << EOF
SENDGRID_KEY=${sendgrid_key}
SENDGRID_USERNAME=${sendgrid_username}
SENDGRID_PASSWORD=${sendgrid_password}
EOF

log "Done with ${sendgrid_name}"

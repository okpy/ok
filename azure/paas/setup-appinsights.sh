#!/usr/bin/env bash

. ./utils.sh; az_login

if [ -f ./secrets/appinsights.env ]; then log "Already exists: appinsights"; exit 0; fi

#
# verify inputs
#

appinsights_name="${OK_NAME}logs"
deployment_log="$(mktemp)"

#
# create resource
#

log "Creating resource ${appinsights_name}"

az group deployment create \
  --name "${appinsights_name}" \
  --template-file './arm/appinsights.deploy.json' \
  --parameters \
      "appinsightsAccountName=${appinsights_name}" \
| tee "${deployment_log}"

#
# store secrets
#

appinsights_key="$(jq -r '.properties.outputs.appinsightsInstrumentationKey.value' "${deployment_log}")"

cat > ./secrets/appinsights.env << EOF
APPLICATION_INSIGHTS_KEY=${appinsights_key}
EOF

log "Done with ${appinsights_name}"

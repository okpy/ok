#!/usr/bin/env bash

. ./utils.sh; az_login

log "Creating okpy database"

okpy_createdb="${OK_NAME}createdb"
acr_server="${ACR_NAME}.azurecr.io"

okpy_mysql_uri="$(get_dotenv ./secrets/okpyconf.env MYSQL_URI)"
acr_password="$(az acr credential show --name "${ACR_NAME}" --resource-group "${ACR_RESOURCE_GROUP}" --query "passwords[0].value" --output tsv)"

az container create \
  --name "${okpy_createdb}" \
  --registry-login-server "${acr_server}" \
  --registry-username "${ACR_NAME}" \
  --registry-password "${acr_password}" \
  --image "${acr_server}/cs61a/ok-server:${DOCKER_TAG}" \
  --restart-policy "Never" \
  --command-line "sh -c './manage.py createdb'" \
  --environment-variables "DB_ROW_FORMAT=default" "DATABASE_URL=${okpy_mysql_uri}"

while :; do
  okpy_createdb_state="$(az container show --name "${okpy_createdb}" --output tsv --query instanceView.state)"
  if [ "${okpy_createdb_state}" != "Succeeded" ]; then log "Waiting for ${okpy_createdb}, current state ${okpy_createdb_state}"; sleep 30s; else break; fi
done

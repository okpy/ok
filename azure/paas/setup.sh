#!/usr/bin/env bash

. ./utils.sh; az_login

#
# setup environment
#

log "Creating resource group"
az group create --name "${RESOURCE_GROUP_NAME}" --location "${RESOURCE_GROUP_LOCATION}"
mkdir -p ./secrets

#
# setup resources
#

declare -A pids

./setup-aks.sh & pids[aks]="$!"
./setup-appinsights.sh & pids[appinsights]="$!"
./setup-mongo.sh & pids[mongo]="$!"
./setup-mysql.sh & pids[mysql]="$!"
./setup-redis.sh & pids[redis]="$!"
./setup-sendgrid.sh & pids[sendgrid]="$!"
./setup-storage.sh & pids[storage]="$!"

#
# wait for resources
#

for taskname in "${!pids[@]}"; do
  taskpid="${pids[${taskname}]}"
  wait "${taskpid}"
  taskstatus="$?"
  log "Setup step ${taskname} completed with exit code ${taskstatus}"
  if [ "${taskstatus}" -gt 0 ]; then exit "${taskstatus}"; fi
done

#
# backup credentials
#

storage_account_name="$(get_dotenv ./secrets/storage.env STORAGE_ACCOUNT_NAME)"
storage_account_key="$(get_dotenv ./secrets/storage.env STORAGE_ACCOUNT_KEY)"
secrets_container="secrets-$(date +'%Y-%m-%d-%H-%M')"

log "Backing up credentials to ${secrets_container}"

az storage container create \
  --account-name "${storage_account_name}" \
  --account-key "${storage_account_key}" \
  --name "${secrets_container}"

az storage blob upload-batch \
  --account-name "${storage_account_name}" \
  --account-key "${storage_account_key}" \
  --destination "${secrets_container}" \
  --pattern "[!.]*" \
  --source "./secrets"

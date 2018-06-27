#!/usr/bin/env bash

. ./utils.sh; az_login

storage_account_name="$(get_dotenv ./secrets/storage.env STORAGE_ACCOUNT_NAME)"
storage_account_key="$(get_dotenv ./secrets/storage.env STORAGE_ACCOUNT_KEY)"
okpy_container="$(get_dotenv ./secrets/okpyconf.env STORAGE_CONTAINER)"

log "Creating okpy storage container ${okpy_container}"

az storage container create \
  --account-name "${storage_account_name}" \
  --account-key "${storage_account_key}" \
  --name "${okpy_container}"

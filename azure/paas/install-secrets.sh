#!/usr/bin/env bash

. ./utils.sh; az_login

log "Creating secrets for ${OK_NAME}"

kubectl create namespace "${OK_NAME}"

for secret in appinsights sendgrid storage serviceprincipal okpyconf autopyconf login; do
  kubectl create secret generic "${secret}" \
    --namespace "${OK_NAME}" \
    --from-env-file "./secrets/${secret}.env"
done

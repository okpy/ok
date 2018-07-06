#!/usr/bin/env bash

. ./utils.sh; az_login

log "Deploying helm chart to ${OK_NAME}"

ingress_domain="${OK_NAME}.${RESOURCE_GROUP_LOCATION}.cloudapp.azure.com"
acr_server="${ACR_NAME}.azurecr.io"

helm init --wait

helm install \
  --namespace "${OK_NAME}" \
  --name "${OK_NAME}" \
  --set "dockerTag=${DOCKER_TAG}" \
  --set "dockerRegistry=${acr_server}" \
  --set "letsencryptDomain=${ingress_domain}" \
  --set "kube-lego.config.LEGO_EMAIL=${CONTACT_EMAIL}" \
  --set "okEnv=prod" \
  ./helm

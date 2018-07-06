#!/usr/bin/env bash

. ./utils.sh; az_login

log "Setting up dns for ${OK_NAME}"

while :; do
  ingress_ip="$(kubectl get service --namespace "${OK_NAME}" --selector app=nginx-ingress,component=controller --output jsonpath={..ip})"
  if [ -z "${ingress_ip}" ]; then log "Waiting for public IP"; sleep 30s; else break; fi
done

az configure --defaults group='' location=''
publicip_id="$(az network public-ip list --query "[?ipAddress!=null]|[?contains(ipAddress,'$ingress_ip')].[id]" --output tsv)"
az network public-ip update --ids "${publicip_id}" --dns-name "${OK_NAME}"

ingress_domain="${OK_NAME}.${RESOURCE_GROUP_LOCATION}.cloudapp.azure.com"
log "The service is now available at ${ingress_domain}"

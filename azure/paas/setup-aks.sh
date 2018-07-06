#!/usr/bin/env bash

. ./utils.sh; az_login

if [ -f ./secrets/kubeconfig ]; then log "Already exists: aks"; exit 0; fi

#
# verify inputs
#

aks_name="${OK_NAME}aks"

#
# create resource
#

log "Creating resource ${aks_name}"

az provider register --wait --namespace Microsoft.Network
az provider register --wait --namespace Microsoft.Storage
az provider register --wait --namespace Microsoft.Compute
az provider register --wait --namespace Microsoft.ContainerService

az aks create \
  --service-principal "${SP_APP_ID}" \
  --client-secret "${SP_APP_KEY}" \
  --name "${aks_name}" \
  --node-count "$(jq -r '.parameters.nodeCount.defaultValue' ./arm/aks.deploy.json)" \
  --node-vm-size "$(jq -r '.parameters.nodeVmSize.defaultValue' ./arm/aks.deploy.json)" \
  --generate-ssh-keys

az aks get-credentials --name "${aks_name}"

#
# store secrets
#

cp ~/.kube/config ./secrets/kubeconfig
cp ~/.ssh/id_rsa.pub ./secrets/id_rsa.pub
cp ~/.ssh/id_rsa ./secrets/id_rsa

log "Done with ${aks_name}"

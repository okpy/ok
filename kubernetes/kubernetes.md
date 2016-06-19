# Kubernetes

## Deployment

## Setup

### Setup secrets
kubectl create secret generic ok-secrets --from-file=../ok-secrets/key.txt
kubectl create secret generic ok-login --from-file=../secret/google-id --from-file=../secret/google-secret

### Setup Pods
- Setup redis (See [Redis Instruction](https://github.com/kubernetes/kubernetes/blob/release-1.3/examples/guestbook/README.md))
- Setup web pods
- Setup web service

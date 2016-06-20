# Kubernetes

## Deployment

Rolling updates the running service one pod at a time, allowing for zero downtime updates.

- Build a docker image for the latest version of ok.
`docker build -t cs61a/ok-server:latest .`
- Push the image to Docker Hub
`docker push cs61a/ok-server:latest`
`docker push cs61a/ok-server:<version number>`

- Tell Kubernetes to do a rolling update.

1. Delete the autoscaler (see section below)
2. Run the rolling update:
> `kubectl rolling-update ok-web-rc --image=cs61a/ok-server:<version number>`

3. Recreate the autoscaler

If that's too slow add `--update-period 15s`

- Check on the status of the rolling update
In another shell:
`watch kubectl get pods`

### Notes for developers

Using version numbers instead of the `latest` tag for docker makes it easier to rollback changes. Check the current tag version on [Docker Hub](https://hub.docker.com/r/cs61a/ok-server/)

## Scaling

### Pod Scaling

Horizontal Pod Scaling is not compatible with rolling updates.
Temporary solution is to delete the HPA and recreate it after the rolling update

`kubectl get hpa` # Verify we current load status
`kubectl delete hpa ok-web-rc`
`kubectl autoscale rc ok-web-rc --min=5 --max=15 --cpu-percent=75`

To manually scale replicas:
`kubectl scale rc ok-web-rc --replicas=<count>`

### Node Scaling

Node scaling (the actual machines the cluster runs on) is set to autoscale through
the Google Web Scaling through the instance group.

## Setup
- Setup the k8s cluster using the web console or command line.

> `gcloud container clusters create ok-v3-prod --zone <zone> --machine-type=n1-highcpu-2 --network <network_name> --disk-size 50 --num-nodes=2`

- Authenticate with the cluster

> `gcloud container clusters get-credentials <cluster_name>`

### Setup secrets

```
kubectl create secret generic ok-secrets --from-file=./secret/key
kubectl create secret generic ok-login --from-file=./secret/google-id --from-file=./secret/google-secret
kubectl create secret generic ok-db --from-file=./secret/db
kubectl create -f ./secret/ok-services.yaml
kubectl create -f ./secret/ok-tls.yaml (if TLS)
```

If you get errors/containers are not launching, it could be because the secrets are misconfigured.
To confirm, ssh into the nodes and checkout /var/log/kubelet.log

### Setup Pods
- Setup redis (See [Redis Instruction](https://github.com/kubernetes/kubernetes/blob/release-1.3/examples/guestbook/README.md))
- Setup web replication controller
- Setup Web Service to expose ports
- Setup Ingress (Load Balancer)

```
# Redis + Secondary
kubectl create -f kubernetes/redis-master-controller.yaml
kubectl create -f kubernetes/redis-master-service.yaml
kubectl create -f kubernetes/redis-secondary.yaml

kubectl create -f kubernetes/ok-web-rc.yaml
kubectl create -f kubernetes/ok-web-direct.yaml

# Open up the firewall for the ports configured above for the load balancer IP range.
# EX: $ gcloud compute firewall-rules create allow-130-211-0-0-22 \
#  --source-ranges 130.211.0.0/22 \
#  --allow tcp:<ports above>
#  --tags <from the tags of the nodes>

kubectl create -f kubernetes/ok-web-ingress.yaml
```

Now checkout the status of your pods with : `watch kubectl get pods`

The load balancer will spin up and get configured (takes a few minutes to pass health checks etc)
`watch kubectl get ing`

## Future Work

@okpy: Automate this deployment process (wercker?)
@k8s Coming in v1.3 - Use Multi zone clusters (`ubernetes-lite`) when Ingress supports it. (See: https://github.com/kubernetes/contrib/pull/1133, https://github.com/kubernetes/contrib/issues/983)

> Honestly both ubernetes-lite and ingress were developed in beta, in parallel, so I'm not surprised they don't play well together. We should definitely make this work.

@k8s - Setup cloud CDN settings right from ingress

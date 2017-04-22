# Kubernetes

## Setup

- Install [Docker](https://docker.com) on your local environment
    - [Mac](https://store.docker.com/editions/community/docker-ce-desktop-mac?tab=description)
    - [PC](https://store.docker.com/editions/community/docker-ce-desktop-windows?tab=description)
    - [Ubuntu](https://store.docker.com/editions/community/docker-ce-server-ubuntu?tab=description)
- Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/)

- Install Kubectl

    `$ gcloud components install kubectl`

- Set the zone for gcloud

    `$ gcloud config set compute/zone s-central1-f`

- Login to Google Cloud

    `$ gcloud auth application-default login`

- Create a [Docker Hub account](https://hub.docker.com) and get a developer to add you to the `cs61a` organization.

## Permissions

- Google Cloud Permissions on the `ok-server` project
- Docker Hub for the `cs61a` organization

## Deployment

### Deploy Script

To deploy you can use the deploy script which will perform the steps necessary to deploy.

    $ ./kubernetes/deploy.sh <version-name>

This will create a tag. OK version names use `vMAJOR.MINOR.PATCH` format (for example `v3.4.20`).

Be sure to push up your tags after a deploy to production

    $ git push origin master --tags

### Manual Instructions
Rolling updates the running service one pod at a time, allowing for zero downtime updates.

- Build a docker image for the latest version of ok.
`docker build -t cs61a/ok-server:latest .`
- Push the image to Docker Hub
`docker push cs61a/ok-server:latest`
`docker push cs61a/ok-server:<version number>`

- Tell Kubernetes to do a rolling update.

1. Run the rolling update:
> `kubectl set image deployment/ok-web-deployment ok-v3-deploy=cs61a/ok-server:<version number>`

2. Check on the status of the rolling update
`kubectl rollout status deployment/ok-web-deployment`
In another shell:
`watch kubectl get pods`

4. Create the autoscaler (if it doesn't exist)
`kubectl autoscale deployment ok-web-deployment --min=4 --max=15 --cpu-percent=75`

The kubernetes documentations on deployments is useful. [Deployment Info](http://kubernetes.io/docs/user-guide/deployments/)

## Migrations

Use a local MySQL DB that is based off the latest deployed version (checkout the git tag/commit).

    $ export DATABASE_URL=mysql://okdev@localhost:5436/db
    $ # checkout the models that are in production
    $ git checkout <commit-that-was-last-deployed>
    $ ./manage.py resetdb
    $ git checkout <your-new-branch>

Once you are on your branch with the changes to the models, run `./manage.py db migrate -m 'short description'` to generate the migration. Inspect the generated files.

Commit, push, and deploy to staging.

1. Deploy the new branch/image into the staging environment.
> `./kubernetes/deploy.sh <dev-migration-name>` (and deploy to staging - _not_ production)

2. Run a command in that pod
> `kubectl get pod # to get the name of the staging pod`
> `k exec -ti ok-staging-deployment-number-something -- ./manage.py db upgrade`

It may hang for a bit - stay patient.

3. Immediately ship it to production.

Merge the branch master on Github, pull the latest code from master and then:

> git checkout master
> git pull origin master # after merging the PR on github
> `./kubernetes/deploy.sh <v3.X.Y>`

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

## Cluster Setup
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

kubectl create -f kubernetes/ok-web-deployment.yaml
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

## Docker Images

- Every branch and tag is automatically built into an image on Docker Hub under the cs61a/ok image
    - [Link](https://hub.docker.org/r/cs61a/ok)
- As a secondary image host - we use [Quay.io] (https://quay.io/repository/cs61a/ok-server) automated builds for the master branch

## Future Work

@okpy: Automate this deployment process (circleCI?)
@k8s Coming in v1.3 - Use Multi zone clusters (`ubernetes-lite`) when Ingress supports it. (See: https://github.com/kubernetes/contrib/pull/1133, https://github.com/kubernetes/contrib/issues/983)

> Honestly both ubernetes-lite and ingress were developed in beta, in parallel, so I'm not surprised they don't play well together. We should definitely make this work.

@k8s - Setup cloud CDN settings right from ingress

#!/bin/bash
# Deploy to Kubernetes from docker image ID.

# Confirm from: http://stackoverflow.com/a/1885534/411514
tag_name=$1

echo "Build image cs61a/ok-server:"$tag_name
read -p "Do you want to build the image? (Should be in repo root): " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Building the image"
    docker build -t cs61a/ok-server:$tag_name .
    docker tag cs61a/ok-server:$tag_name cs61a/ok-server:latest
    docker push cs61a/ok-server:$tag_name
    echo "Done building. Run git tag "$tag_name
fi

echo "Deploying image cs61a/ok-server:"$tag_name
read -p "Deploy to staging? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Watch with 'watch kubectl get pods'"
    kubectl set image deployment/ok-staging-deployment ok-v3-staging=cs61a/ok-server:$tag_name
    kubectl rollout status deployment/ok-staging-deployment
    kubectl set image deployment/ok-worker-deployment ok-v3-worker=cs61a/ok-server:$tag_name
    kubectl rollout status deployment/ok-worker-deployment
    kubectl get pods
    echo "Deployed to staging. Run command again if you want to deploy to production"
else
    read -p "Are you sure you want to deploy to production? " -n 1 -r
    echo    # (optional) move to a new line
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo "Pushing to docker, ok-server:latest"
        docker push cs61a/ok-server:latest
        echo "Watch with 'watch kubectl get pods'"
        kubectl set image deployment/ok-web-deployment ok-v3-deploy=cs61a/ok-server:$tag_name
        kubectl rollout status deployment/ok-web-deployment
        kubectl set image deployment/ok-worker-deployment ok-v3-worker=cs61a/ok-server:$tag_name
        kubectl rollout status deployment/ok-worker-deployment
        kubectl get pods
        echo "Done"
    fi
fi

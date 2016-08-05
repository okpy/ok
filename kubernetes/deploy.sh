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
    docker push cs61a/ok-server:latest
    echo "Done building. Run git tag "$tag_name
fi

echo "Deploying image cs61a/ok-server:"$tag_name
read -p "Are you sure you want to deploy? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Watch with 'watch kubectl get pods'"
    kubectl set image deployment/ok-web-deployment ok-v3-deploy=cs61a/ok-server:$tag_name
    kubectl rollout status deployment/ok-web-deployment
    kubectl get pods
    echo "Done"
fi

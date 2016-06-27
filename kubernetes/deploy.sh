#!/bin/bash
# Deploy to Kubernetes from docker image ID.

# Confirm from: http://stackoverflow.com/a/1885534/411514
image_name=$1

echo "Deploying image cs61a/ok-server:"$image_name
read -p "Are you sure? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Watch with 'watch kubectl get pods'"
    kubectl delete hpa ok-web-rc
    kubectl rolling-update ok-web-rc --update-period 10s --image=cs61a/ok-server:$image_name
    kubectl autoscale rc ok-web-rc --min=5 --max=15 --cpu-percent=75
    echo "Done"
fi


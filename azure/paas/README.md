# Deploy to Azure PaaS

These templates and scripts deploy [Ok.py](www.okpy.org) to Azure. In a production environment you may wish to customize these templates to share resources between environments and to adjust resource sizing. For example you may wish to use a single mySQL server with multiple databases, rather than one server per environment.

## Architecture

The provided templates deploy everything within the Resource Group outlined below. Items outside the resource group are an indication as to how Ok.py can integrate with additional Azure services:

![Azure PaaS Architecture](https://user-images.githubusercontent.com/1086421/43547159-75306220-95a8-11e8-8059-58c355fc32d0.png)

## Setup

Prior to deploying the template the terms and conditions for SendGrid must be accepted.

Using PowerShell:

```
Get-AzureRmMarketplaceTerms -Publisher "sendgrid" -Product "sendgrid_azure" -Name "free" | Set-AzureRmMarketplaceTerms -Accept
```

If you do not have access to PowerShell this can be run in the cloud shell via the Azure Portal.

Next, you'll need to create a Service Principal following the instructions [here](https://aka.ms/create-sp). The Service Principal is a credential to your Azure subscription that will enable the OKpy deployment to create Azure resources on your behalf.

Finally, grant read permissions to your Azure Container Registry instance to the Service Principal. This will enable the OKpy deployment to access Docker images for okpy and autopy in your registry and deploy them to the infrastructure set up by the template:

```
SP_APP_ID=<insert the app id of your okpy service principal here>
ACR_NAME=<insert name of your container registry here>
RESOURCE_GROUP=<insert the resource group of your container registry here>

az role assignment create \
  --assignee "${SP_APP_ID}" \
  --role Reader \
  --scope "$(az acr show --name "${ACR_NAME}" --resource-group "${ACR_RESOURCE_GROUP}" --query "id" --output tsv)"
```

## Deployment

To deploy [Ok.py](www.okpy.org) to Azure use the deploy button below. If you are not familiar with the configuration of Azure resources please check our [integration guide](../README.md).

[![Deploy to Azure](https://azuredeploy.net/deploybutton.svg)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fokpy%2Fok%2Fmaster%2Fazure%2Fpaas%2Farm%2Fazure.deploy.json)

You can also run the deployment locally:

```
mkdir -p azure/paas/secrets
docker build -t ok-setup azure/paas
docker run -v $PWD/azure/paas/secrets:/app/secrets ok-setup
```

Note that the deployment can take upwards of 30 minutes to complete. After the deployment is done, remember to update your Active Directory application to include `https://<app-name>.<location>.cloudapp.azure.com/login/authorized/` as a redirect URL.

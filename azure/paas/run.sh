#!/usr/bin/env bash
##
## Required environment variables:
##
##   SP_APP_ID
##   SP_APP_KEY
##   SP_TENANT_ID
##   SP_SUBSCRIPTION_ID
##   RESOURCE_GROUP_LOCATION
##   RESOURCE_GROUP_NAME
##   OK_NAME
##   ACR_RESOURCE_GROUP
##   ACR_NAME
##   CONTACT_EMAIL
##   ADMIN_USERNAME
##   ADMIN_PASSWORD
##   AD_APP_ID
##   AD_APP_KEY
##   AD_TENANT_ID
##   DOCKER_TAG
##

. ./utils.sh

#
# verify inputs
#

scriptname="${BASH_SOURCE[0]}"
required_env "${scriptname}" "SP_APP_ID"
required_env "${scriptname}" "SP_APP_KEY"
required_env "${scriptname}" "SP_TENANT_ID"
required_env "${scriptname}" "SP_SUBSCRIPTION_ID"
required_env "${scriptname}" "RESOURCE_GROUP_LOCATION"
required_env "${scriptname}" "RESOURCE_GROUP_NAME"
required_env "${scriptname}" "OK_NAME"
required_env "${scriptname}" "ACR_RESOURCE_GROUP"
required_env "${scriptname}" "ACR_NAME"
required_env "${scriptname}" "CONTACT_EMAIL"
required_env "${scriptname}" "ADMIN_USERNAME"
required_env "${scriptname}" "ADMIN_PASSWORD"
required_env "${scriptname}" "AD_APP_ID"
required_env "${scriptname}" "AD_APP_KEY"
required_env "${scriptname}" "AD_TENANT_ID"
required_env "${scriptname}" "DOCKER_TAG"

#
# setup application
#

./setup.sh
./install.sh

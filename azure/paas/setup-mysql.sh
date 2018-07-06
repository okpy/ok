#!/usr/bin/env bash

. ./utils.sh; az_login

if [ -f ./secrets/mysql.env ]; then log "Already exists: mysql"; exit 0; fi

#
# verify inputs
#

mysql_name="${OK_NAME}mysql"
mysql_database="ok"
mysql_username="okpy"
mysql_password="$(generate_password 64)"
deployment_log="$(mktemp)"

#
# create resource
#

log "Creating resource ${mysql_name}"

az group deployment create \
  --name "${mysql_name}" \
  --template-file './arm/mysql.deploy.json' \
  --parameters \
      "mysqlAccountName=${mysql_name}" \
      "mysqlDatabaseName=${mysql_database}" \
      "mysqlUserName=${mysql_username}" \
      "mysqlPassword=${mysql_password}" \
| tee "${deployment_log}"

#
# store secrets
#

mysql_host="$(jq -r '.properties.outputs.mysqlHost.value' "${deployment_log}")"

cat > ./secrets/mysql.env << EOF
MYSQL_USERNAME=${mysql_username}@${mysql_name}
MYSQL_PASSWORD=${mysql_password}
MYSQL_DATABASE=${mysql_database}
MYSQL_HOST=${mysql_host}
MYSQL_PORT=3306
EOF

log "Done with ${mysql_name}"

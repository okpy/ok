#!/usr/bin/env bash

. ./utils.sh; az_login

log "Installing app configs"

mysql_database="$(get_dotenv ./secrets/mysql.env MYSQL_DATABASE)"
mysql_username="$(get_dotenv ./secrets/mysql.env MYSQL_USERNAME)"
mysql_password="$(get_dotenv ./secrets/mysql.env MYSQL_PASSWORD)"
mysql_host="$(get_dotenv ./secrets/mysql.env MYSQL_HOST)"
mysql_port="$(get_dotenv ./secrets/mysql.env MYSQL_PORT)"
okpy_mysql_uri="mysql://${mysql_username}:${mysql_password}@${mysql_host}:${mysql_port}/${mysql_database}?"

mongo_database="$(get_dotenv ./secrets/mongo.env MONGO_DATABASE)"
mongo_username="$(get_dotenv ./secrets/mongo.env MONGO_USERNAME)"
mongo_password="$(get_dotenv ./secrets/mongo.env MONGO_PASSWORD)"
mongo_host="$(get_dotenv ./secrets/mongo.env MONGO_HOST)"
mongo_port="$(get_dotenv ./secrets/mongo.env MONGO_PORT)"
autopy_mongo_uri="mongodb://${mongo_username}:${mongo_password}@${mongo_host}:${mongo_port}/${mongo_database}?ssl=true&replicaSet=globaldb"

redis_password="$(get_dotenv ./secrets/redis.env REDIS_PASSWORD)"
redis_host="$(get_dotenv ./secrets/redis.env REDIS_HOST)"
redis_port="$(get_dotenv ./secrets/redis.env REDIS_PORT)"
okpy_redis_uri="rediss://:${redis_password}@${redis_host}:${redis_port}/0"
autopy_redis_uri="rediss://:${redis_password}@${redis_host}:${redis_port}/1"

cat > ./secrets/okpyconf.env << EOF
MYSQL_URI=${okpy_mysql_uri}
REDIS_URI=${okpy_redis_uri}
STORAGE_CONTAINER=okpyfiles
FLASK_SECRET_KEY=$(generate_password 32)
EOF

cat > ./secrets/autopyconf.env << EOF
MONGO_URI=${autopy_mongo_uri}
REDIS_URI=${autopy_redis_uri}
FLASK_SECRET_KEY=$(generate_password 32)
AGFILES_KEY=$(generate_password 32)
EOF

cat > ./secrets/login.env << EOF
AUTOPY_ADMIN_USERNAME=${ADMIN_USERNAME}
AUTOPY_ADMIN_PASSWORD=${ADMIN_PASSWORD}
ACTIVE_DIRECTORY_APP_ID=${AD_APP_ID}
ACTIVE_DIRECTORY_APP_KEY=${AD_APP_KEY}
ACTIVE_DIRECTORY_TENANT_ID=${AD_TENANT_ID}
EOF

cat > ./secrets/serviceprincipal.env << EOF
SP_APP_ID=${SP_APP_ID}
SP_APP_KEY=${SP_APP_KEY}
SP_TENANT_ID=${SP_TENANT_ID}
SP_SUBSCRIPTION_ID=${SP_SUBSCRIPTION_ID}
RESOURCE_GROUP_LOCATION=${RESOURCE_GROUP_LOCATION}
RESOURCE_GROUP_NAME=${RESOURCE_GROUP_NAME}
EOF

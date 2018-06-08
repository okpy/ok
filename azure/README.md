# Integrating OK.py with Azure services

## PaaS Deployment

To jump straight to deploying [Ok.py](http://www.okpy.org) to Azure without reading the integration guide click
[here](./paas/README.md).

## Azure Active Directory

The [Azure Active Directory](https://azure.microsoft.com/en-gb/services/active-directory/) login can be enabled by
setting the following environment variables:

```
MICROSOFT_TENANT_ID={TenantName}.onmicrosoft.com
MICROSOFT_APP_SECRET={ActiveDirectoryAppSecret}
MICROSOFT_APP_ID={ActiveDirectoryAppId}
```

To create and App registration follow this guide: [https://docs.microsoft.com/en-gb/azure/active-directory/develop/active-directory-integrating-applications](https://docs.microsoft.com/en-gb/azure/active-directory/develop/active-directory-integrating-applications)

The App registration reply URL needs to be set to: ```http(s)://<FQDN>/login/authorized/```

Your Azure AD administrator may have to grant consent to the application as per: [https://docs.microsoft.com/en-us/azure/active-directory/develop/active-directory-devhowto-multi-tenant-overview#understanding-user-and-admin-consent](https://docs.microsoft.com/en-us/azure/active-directory/develop/active-directory-devhowto-multi-tenant-overview#understanding-user-and-admin-consent)

## Azure Database for MySQL

The [Azure MySQL database](https://azure.microsoft.com/en-us/services/mysql/) can be enabled by setting the following
environment variables:

```
DATABASE_URL=mysql://{UserName}@{ServerName}:{Password}@{ServerName}.mysql.database.azure.com:3306/{DatabaseName}?
DB_ROW_FORMAT=DEFAULT
```

## Azure Storage

The [Azure Storage](https://azure.microsoft.com/en-gb/services/storage/blobs/) backend can be enabled by setting the
following environment variables:

```
STORAGE_PROVIDER=AZURE_BLOBS
STORAGE_KEY={AzureStorageAccountName}
STORAGE_SECRET={AzureStorageSecretKey}
STORAGE_CONTAINER=okpyfiles
```

## Azure Redis Cache

The [Azure Redis Cache](https://azure.microsoft.com/en-gb/services/cache/) can be enabled by setting the following
environment variables:

```
REDIS_URL=rediss://:{Password}@{CacheName}.redis.cache.windows.net:6380/0
```

Please node this issue which may require manual regeneration of the Redis key: [https://github.com/Cal-CS-61A-Staff/ok/issues/1279](https://github.com/Cal-CS-61A-Staff/ok/issues/1279)

## Azure Application Insights

The [Azure Application Insights](https://azure.microsoft.com/en-gb/services/application-insights/) logging and telemetry
monitoring can be enabled by setting the following environment variables:

```
APPLICATION_INSIGHTS_KEY={InstrumentationKey}
```

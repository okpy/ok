# Ok Staging Info

# Deploy
```
git remote add dokku dokku@app.cs61a.org:okstaging
git push <current branch>:master
```

# Setup
```
dokku mysql:create okstaging
dokku mysql:link okstaging okstaging
dokku config:set okstaging OK_ENV=staging # and other secrets if needed

# Other commands (optional)
dokku domains:add okstaging okstaging.cs61a.org
dokku domains:remove okstaging okstaging.apps.cs61a.org
dokku letsencrypt okstaging
dokku config:set okstaging DOKKU_NGINX_PORT=80  NGINX_SSL_PORT=443
```

# Development Environment

## Database setup

Ensure that SQLite 3 is installed. To set up the database:

    $ ./manage.py createdb

To "seed" the database with example data:

    $ ./manage.py seed

To both recreate the database and reseed it with the example data:

    $ ./manage.py resetdb

## Running the server

To run the server (point your browser to http://localhost:5000):

    $ ./manage.py server

## Testing

Run tests via

    $ ./manage.py test

In order to run the tests in `tests/test_web.py`, `phantom.js` needs to be installed.
On OSX: First make sure [Homebrew](http://brew.sh/) is installed. To install `phantom.js`:

    $ brew install phantomjs

# Test Environment Setup (Docker)

This section is optional. It shows how to get the Docker test environment
(which Travis uses) running locally.

## Mac OS X

Make sure [Homebrew](http://brew.sh/) is installed.

Local development uses [Docker](https://www.docker.com/). Install Docker:

    $ brew install docker

Then create a docker machine. The following command will create a machine named
`ok-server` with 512MB of memory.

    $ docker-machine create --driver virtualbox --virtualbox-memory 512 ok-server

Start the machine and tell Docker where your machine is.

    $ docker-machine start ok-server
    $ eval $(docker-machine env ok-server)

You will need to run these commands before running `docker` commands.

To make it easy to install Docker and sync files to the Docker containers, we'll
use [docker-osx-dev](https://github.com/brikis98/docker-osx-dev).
Install `docker-osx-dev`:

    $ curl -o /usr/local/bin/docker-osx-dev https://raw.githubusercontent.com/brikis98/docker-osx-dev/master/src/docker-osx-dev
    $ chmod +x /usr/local/bin/docker-osx-dev
    $ docker-osx-dev install

This will add an entry in `/etc/hosts` so you don't have to type in the Docker
machine IP every time.

### Development

To start the Docker machine, run

    $ docker-machine start ok-server
    $ eval $(docker-machine env ok-server)

To start the application, run

    $ docker-compose up

You can point your browser to http://ok-server/ to see the running app, thanks
to `/etc/hosts`.

To sync any changes you make into the running Docker containers, in another
terminal run

    $ docker-osx-dev

### Testing

The command that Travis uses is

    $ make docker-test

## Setting up Redis

There are two ways to configure Redis:

1. Connect to Redis using a URL
2. Connect to Redis using socket connection details

### Option 1: Connect to Redis using a URL

By setting the `REDIS_URL` environment variable the server will attempt to connect to a Redis service using a URL in one of the following formats:

```
redis://[username:password]@[server]:[port]/[db]
rediss://[username:password]@[server]:[port]/[db]
```

The `redis://` scheme connects to redis over a non-SSL connection, where as the `rediss://` scheme will use SSL.

An example connection URL might look like this:

`rediss://:reallystrongpassword@myazureredisinstance.redis.cache.example.net:6380/0`

Notes on this example:

- This example omits a username. If you omit the username make sure still include the `:` which would normally separate username and password
- The password for this Redis server is `reallystrongpassword`
- This fictional Redis instance is at `myazureredisinstance.redis.cache.example.net`
- Port `6380` is being used. For a non-secure endpoint, port `6379` would be appropriate
- the `/O` at the end signifies database 0.

For more information on the format of these URLs see the following:

- `redis://` <http://www.iana.org/assignments/uri-schemes/prov/redis>
- `rediss://` <http://www.iana.org/assignments/uri-schemes/prov/rediss>

### Option 2: Connect using Host/Port details

If the absense of the `REDIS_URL` environment variable, the server will look for the following environent variables and will use certain defaults if they're not found:

Env Variable | Default Value | Purpose
---|---|---
`REDIS_HOST`|`localhost` for all non-prod environments<br> `redis-master` for prod|Redis host name
`REDIS_PORT`|6379|Redis port

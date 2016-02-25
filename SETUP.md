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

    $ make test

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

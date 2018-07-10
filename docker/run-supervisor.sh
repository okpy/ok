#!/bin/sh

# supervisor doesn't have an easy way of passing all the environment variables
# to the child process so as a work-around we first dump the environment into
# files and then reload them in the child process from the files via the envdir
# utility
mkdir -p /env
python /code/docker/env_to_envdir.py --envdir /env

/usr/bin/supervisord -c /etc/supervisor.conf

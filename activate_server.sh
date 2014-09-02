#!/bin/bash
# You must 'source activate_server' to activate the server virtualenv.

if env | grep -q ^VIRTUAL_ENV=
then
    deactivate
fi
source env/server/bin/activate

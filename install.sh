#!/bin/sh
if env | grep -q ^VIRTUAL_ENV=
then
    echo '$VIRTUAL_ENV is defined'
else
    echo 'You need to set $VIRTUAL_ENV before continuing'
    exit  11
fi

server/app/generate_keys.py

pip install -r requirements.txt

ln -s ../../hooks/pre-commit.py .git/hooks/pre-commit

echo 'Linking environments'
linkenv $VIRTUAL_ENV/lib/python2.7/site-packages gaenv  1>/dev/null

#!/bin/sh
if env | grep -q ^VIRTUAL_ENV=
then
    echo '$VIRTUAL_ENV is defined'
else
    echo 'You need to set $VIRTUAL_ENV before continuing'
    exit  11
fi
if env | grep -q ^GAE_SDK=
then
    echo '$GAE_SDK is defined'
else
    echo 'You need to set $GAE_SDK before continuing'
    exit  11
fi

server/app/generate_keys.py

pip install -r requirements.txt

ln -s ../../hooks/pre-commit.py .git/hooks/pre-commit

echo 'Linking environments'
linkenv $VIRTUAL_ENV/lib/python2.7/site-packages server/gaenv  1>/dev/null

cd server;
mysql -u root -p < sql/setup_dev.sql
python alembic/create_all.py

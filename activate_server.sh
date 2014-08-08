# You must 'source activate_server' to activate the server virtualenv.

if env | grep -q ^VIRTUAL_ENV=
then
    deactivate
fi
source envs/server/bin/activate

# You must 'source activate_client' to activate the client virtualenv.

if env | grep -q ^VIRTUAL_ENV=
then
    deactivate
fi
source env/client/bin/activate

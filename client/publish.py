#! /usr/bin/env python3

STAGING_DIR = "./staging"

from config import protocols
import subprocess
import zipfile
import os

cmd = "mkdir " + STAGING_DIR

required_files = ["ok", "auth", "config", "utils"]
required_folders = ["models"]

def run_cmd(cmd):
    """
    Runs a shell command in the current bash environment
    """
    print(cmd)
    return subprocess.Popen(cmd.split())

# Make the staging_dir
run_cmd(cmd)

# Move all required files/folders in client/

for filename in required_files:
    cp_cmd = "cp {0}.py {1}".format(filename, STAGING_DIR)
    run_cmd(cp_cmd)

for folder in required_folders:
    cp_cmd = "cp -r {0} {1}".format(folder, STAGING_DIR)
    run_cmd(cp_cmd)

# Move all required protocols in client/protocols

run_cmd("mkdir {0}/protocols".format(STAGING_DIR))
run_cmd("cp protocols/__init__.py {0}/protocols/".format(STAGING_DIR))

for protocol in protocols:
    cp_cmd = "cp protocols/{0}.py {1}/protocols/".format(protocol, STAGING_DIR)
    run_cmd(cp_cmd)

# Zip up the files

# zipdir function taken from:
# https://stackoverflow.com/questions/1855095/how-to-create-a-zip-archive-of-a-directory-in-python
def zipdir(path, zipf):
    for root, dirs, files in os.walk(path):
        for file in files:
            zipf.write(os.path.join(root, file))

zipf = zipfile.ZipFile('ok', 'w')
zipdir(STAGING_DIR, zipf)
zipf.close()

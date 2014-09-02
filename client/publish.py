#! /usr/bin/env python3

"""
This module is responsible for publishing ok. This will put all of the
required files (as determined by config.py) into a separate directory
and then make a zipfile called "ok" that can be distributed to students.
"""

STAGING_DIR = "./staging"

from config import protocols
import zipfile
import os
import shutil

REQUIRED_FILES = ["auth", "config", "utils"]
REQUIRED_FOLDERS = ["models"]

# Make the staging_dir
os.mkdir(STAGING_DIR)

# Move ok.py and call it __main__.py
shutil.copyfile("ok.py", STAGING_DIR + "/__main__.py")

# Move all required files/folders in client/

for filename in REQUIRED_FILES:
    fullname = filename + ".py"
    shutil.copyfile(fullname, STAGING_DIR + "/" + fullname)

for folder in REQUIRED_FOLDERS:
    shutil.copytree(folder, STAGING_DIR + "/" + folder)

# Move all required protocols in client/protocols

os.mkdir(STAGING_DIR + "/protocols")
shutil.copyfile("protocols/__init__.py", STAGING_DIR + "/protocols/__init__.py")

for protocol in protocols:
    src = "protocols/{0}.py".format(protocol)
    dst = "{0}/protocols/{1}.py".format(STAGING_DIR, protocol)
    shutil.copyfile(src, dst)

# Zip up the files

zipf = zipfile.ZipFile('ok', 'w')

for root, dirs, files in os.walk(STAGING_DIR):
    os.chdir(STAGING_DIR)
    for filename in files:
        fullname = os.path.join(root, filename)
        fullname = fullname.replace(STAGING_DIR[1:], "")
        zipf.write(fullname)
    os.chdir("..")

zipf.close()

# Clean up staging dir
shutil.rmtree(STAGING_DIR)

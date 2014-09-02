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

REQUIRED_FILES = ["__main__", "ok", "auth", "config", "utils", "exceptions"]
REQUIRED_FOLDERS = ["models", "sanction"]

# Make the staging_dir
os.mkdir(STAGING_DIR)

shutil.copyfile("ok.py", os.path.join(STAGING_DIR ,"ok.py"))

# Move all required files/folders in client/

for filename in REQUIRED_FILES:
    fullname = filename + ".py"
    shutil.copyfile(fullname, os.path.join(STAGING_DIR, fullname))

for folder in REQUIRED_FOLDERS:
    shutil.copytree(folder, os.path.join(STAGING_DIR, folder))

# Move all required protocols in client/protocols

os.mkdir(os.path.join(STAGING_DIR, "protocols"))
shutil.copyfile(os.path.join("protocols", "__init__.py"), os.path.join(STAGING_DIR, "protocols", "__init__.py"))

for protocol in protocols:
    filename = "{0}.py".format(protocol)
    src = os.path.join("protocols", filename)
    dst = os.path.join(STAGING_DIR, "protocols", filename)
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

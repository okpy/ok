#!/bin/sh

server/app/generate_keys.py

pip install -r requirements.txt

ln -s ../../hooks/pre-commit.py .git/hooks/pre-commit

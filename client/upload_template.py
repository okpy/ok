"""
Uploads the current version of ok.py to the server.
"""

import requests
import base64
from os import path
import json

SERVER_URL = 'https://ok-server.appspot.com/api/v1/assignment'
SERVER_URL = 'http://localhost:8080/api/v1/assignment'

def get_current_templates(assign_name):
    resp = requests.get(SERVER_URL + "?name=" + assign_name)
    results = resp.json()['data']['results'][0]
    return results['id'], results['templates']

def main():
    assign_name = raw_input("Please input the assignment name: ")

    params = {
        'access_token': raw_input("Please enter your access token:")
    }

    assign_id, current_templates = get_current_templates(assign_name)

    try:
        current_templates = json.loads(current_templates)
    except ValueError:
        current_templates = {}

    in_str = True

    while in_str:
        in_str = raw_input("Enter filename to upload, or \"done\" to upload: ")
        if in_str == "done":
            break
        else:
            with open(in_str) as f:
                current_templates[path.basename(in_str)] = f.read()

    data = {
        'templates': current_templates
    }
    headers = {'content-type': 'application/json'}

    data = json.dumps(data)
    resp = requests.put(SERVER_URL + '/%s' % assign_id, params=params, data=data, headers=headers)
    print resp

if __name__ == "__main__":
    main()

"""
Uploads the current version of ok.py to the server.
"""

import requests
import base64

SERVER_URL = 'https://ok-server.appspot.com/api/v1/version'

def get_current_id():
    resp = requests.get(SERVER_URL + "?name=okpy")
    return resp.json()['data']['results'][0]['id']

def main():
    with open('ok', 'rb') as okzip:
        file_data = base64.b64encode(okzip.read()).decode('utf-8')

    params = {
        'access_token': raw_input("Please enter your access token:")
    }

    data = {
        'version': '1.1.1',
        'file_data': file_data
    }

    resp = requests.put(SERVER_URL + '/%s' % get_current_id(), params=params, data=data)
    print resp

if __name__ == "__main__":
    main()

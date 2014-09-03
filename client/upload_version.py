"""
Uploads the current version of ok.py to the server.
"""

import requests
import base64

def main():
    with open('ok', 'rb') as okzip:
        file_data = base64.b64encode(okzip.read()).decode('utf-8')

    params = {
        'access_token': raw_input("Please enter your access token:")
    }

    data = {
        'name': 'okpy',
        'version': '1.1.0',
        'file_data': file_data
    }

    resp = requests.post('https://ok-server.appspot.com/api/v1/version',
            params=params, data=data)
    print resp

if __name__ == "__main__":
    main()

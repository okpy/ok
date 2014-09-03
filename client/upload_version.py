import requests
import base64

with open('ok', 'rb') as okzip:
    file_data = base64.b64encode(okenc.read()).decode('utf-8')

params = {
    'access_token': "ya29.dQCiSYYqeLchvyEAAACgsU7OUS9sPftIYTJzJ5MsR6XZm2QH8HO4YjDBqaGGT1gojmbG6PGMEkSa7jx3yG8"
}

data = {
    'name': 'okpy',
    'version': '1.1.0',
    'file_data': file_data
}

r = requests.post('https://ok-server.appspot.com/api/v1/version', params=params, data=data)
print r

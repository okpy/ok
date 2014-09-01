"""
Utility functions used by API and other services
"""
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
import zipfile as zf
from flask import jsonify, request, Response, json


#TODO(martinis) somehow having data be an empty list doesn't make it
# return an empty list, but an empty object.
def create_api_response(status, message, data=None):
    """Creates a JSON response that contains status code (HTTP),
    an arbitrary message string, and a dictionary or list of data"""
    if request.args.get('format', 'default') == 'raw':
        response = Response(json.dumps(data))
    else:
        response = jsonify(**{
            'status': status,
            'message': message,
            'data': data
        })
    response.status_code = status
    return response

def create_zip(obj):
    zipfile_str = StringIO()
    with zf.ZipFile(zipfile_str, 'w') as zipfile:
        for filename, contents in obj.items():
            zipfile.writestr(filename, contents)
    zip_string = zipfile_str.getvalue()
    return zip_string

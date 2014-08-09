"""
Utility functions used by API and other services
"""
from flask import jsonify, request, Response, json


#TODO(martinis) somehow having data be an empty list doesn't make it
# return an empty list, but an empty object.
def create_api_response(status, message, data=None):
    """Creates a JSON response that contains status code (HTTP),
    an arbitrary message string, and a dictionary or list of data"""
    print data
    if request.args.get('format', 'default') == 'raw':
        response = Response(json.dumps(data))
        print response.data
    else:
        response = jsonify(**{
            'status': status,
            'message': message,
            'data': data
        })
    response.status_code = status
    return response

"""
Utility functions used by API and other services
"""
from flask import jsonify


def create_api_response(status, message, data=None):
    """Creates a JSON response that contains status code (HTTP),
    an arbitrary message string, and a dictionary or list of data"""
    response = jsonify(**{
        'status': status,
        'message': message,
        'data': data
    })
    response.status_code = status
    return response

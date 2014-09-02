"""
Utility functions used by API and other services
"""
from flask import jsonify

from google.appengine.datastore.datastore_query import Cursor

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


def paginate(entries, cursor, num_per_page):
    """
    Support pagination for an NDB query.
    Arguments:
      |entries| - a query which returns the items to paginate over.
      |cursor|  - a cursor of where in the pagination the user is.
      |num_per_page| - the number of results to display per page.

    The return value will be different from a regular query:
    There will be 3 things returned:
    - results: a list of results
    - forward_curs: a urlsafe hash for the cursor. Use this to get
    the next page. To retrieve the cursor object, do Cursor(urlsafe=s)
    - more: a boolean for whether or not there is more content.

    For more documentation, look at:
    https://developers.google.com/appengine/docs/python/ndb/queryclass#Query_fetch_page
    """
    if num_per_page is None:
        result = entries.fetch(), None, False
    else:
        if cursor is not None:
            cursor = Cursor(urlsafe=cursor)
            results, forward_curs, more = entries.fetch_page(
                int(num_per_page), start_cursor=cursor)
        else:
            results, forward_curs, more = entries.fetch_page(int(num_per_page))
        if forward_curs is not None:
            result = results, forward_curs.urlsafe(), more
        else:
            result = results, None, more
    results, urlsafe, more = result
    return {
        'results': results,
        'cursor': urlsafe,
        'more': more
    }

def _apply_filter(query, model, arg, value):
    field = getattr(model, arg, None)
    if not field:
        # Silently swallow for now
        # TODO(martinis) cause an error
        return query

    # Only equals for now
    return query.filter(field == value)

def filter_query(query, args, model):
    """
    Applies the filters in |args| to |query|.
    |args| is a dictionary of key to value, to be used to filter the query.
    |allowed| is an optional list of the allowed filters.

    Returns a modified query with the appropriate filters.
    """
    for arg, value in args.iteritems():
        query = _apply_filter(query, model, arg, value)

    return query

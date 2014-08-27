from google.appengine.datastore.datastore_query import Cursor
from app.decorators import wraps

class Paginator():
    """
    Paginator creates a decorator object that supports pagination
    for a decorated query maker. When creating the class, specify
    the max number of results per page.

    The return value will be different from a regular query:
    There will be 3 things returned:
    - results: a list of results
    - next_curs: a urlsafe hash for the cursor. Use this to get
    the next page. To retrieve the cursor object, do Cursor(urlsafe=s)
    - more: a boolean for whether or not there is more content. Useful
    to determine when to show the ("next page" link)

    For more information about the return value:
    https://developers.google.com/appengine/docs/python/ndb/queryclass#Query_fetch_page
    """
    def __init__(self, num_pages):
        self.num_pages = num_pages

    def __call__(self, query_maker):
        @wraps(query_maker)
        def wrapped(api, cursor):
            if cursor:
                cursor = Cursor(urlsafe=cursor) # Get a cursor object from URL parameter
                results, new_curs, more = query_maker(api, cursor).fetch_page(self.num_pages, start_cursor=cursor)
            else:
                results, new_curs, more = query_maker(api, cursor).fetch_page(self.num_pages)
            if not results:
                return results, new_curs, more
            if new_curs:
                new_curs = new_curs.urlsafe()
            return results, new_curs, more
        return wrapped


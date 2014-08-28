from google.appengine.datastore.datastore_query import Cursor
from app.decorators import wraps

def paginate(entries, cursor, num_per_page):
    """
    Support pagination for an NDB query.
    
    The arguments for the parameters cursor and num_per_page 
    should come from the URL.

    The return value will be different from a regular query:
    There will be 4 things returned:
    - results: a list of results
    - forward_curs: a urlsafe hash for the cursor. Use this to get
    the next page. To retrieve the cursor object, do Cursor(urlsafe=s)
    - back_curs: a urlsafe hash for the cursor to get the *previous* page.
    - more: a boolean for whether or not there is more content. Useful
    to determine when to show the ("next page" link)

    For more information about the return value:
    https://developers.google.com/appengine/docs/python/ndb/queryclass#Query_fetch_page
    """
    def helper():
        if num_per_page is None:
            return entries.fetch(), None, False
        if cursor is not None:
            cursor = Cursor(urlsafe=cursor)
            results, forward_curs, more = entries.fetch_page(
                    int(num_per_page), start_cursor=cursor)
        else:
            results, forward_curs, more = entries.fetch_page(int(num_per_page))
        if forward_curs is not None:
            return (results, forward_curs.urlsafe(), more)
        return results, None, more
    results, urlsafe, more = helper()
    return {
        'results': results,
        'cursor': urlsafe,
        'more': more
    }

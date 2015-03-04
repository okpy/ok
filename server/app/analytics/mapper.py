"""
NDB Mapper, taken from http://blog.altlimit.com/2013/05/simple-mapper-class-for-ndb-on-app.html,
inspired by http://cloud.google.com/appengine/articles/remote_api
"""

import logging
from google.appengine.ext import deferred, ndb
from google.appengine.runtime import DeadlineExceededError

from app.needs import Need


class Mapper(object):

    def __init__(self, kind, user, use_cache=False):

        ndb.get_context().set_cache_policy(use_cache)
        if not use_cache:
            ndb.get_context().clear_cache()

        self.kind = kind
        self.user = user
        self.to_put = []
        self.to_delete = []
        self.terminate = False
        # Data you wanna carry on in case of error
        self.data = None
        # Temporary Data that won't carry on in case of error
        self.tmp_data = None
        self.filters = []
        self.orders = []
        self.keys_only = False
        self.initial_query = None
        # implement init for different initializations
        self.init()

    def delete(self, entity):
        self.to_delete.append(entity if isinstance(entity, ndb.Key) else entity.key)

    def update(self, entity):
        self.to_put.append(entity)

    def map(self, entity):
        """Updates a single entity.

        Implementers should return a tuple containing two iterables (to_update, to_delete).
        """
        raise NotImplementedError

    def init(self):
        # initialize variables
        pass

    def deadline_error(self):
        # on deadline error execute
        pass

    def finish(self):
        """Called when the mapper has finished, to allow for any final work to be done."""
        pass

    def get_query(self):
        """Returns a query over the specified kind, with any appropriate filters applied."""
        q = self.kind.can(self.user, Need('index'), query=self.kind.query())
        for filter in self.filters:
            q = q.filter(ndb.query.FilterNode(*filter))
        for order in self.orders:
            q = q.order(order)
        return q

    def set_filters(self, filters):
        self.filters = filters

    def run(self, batch_size=100, initial_data=None):
        if initial_data is None:
            initial_data = self.data
        """Starts the mapper running."""
        if hasattr(self, '_pre_run_hook'):
            getattr(self, '_pre_run_hook')()

        self._continue(None, batch_size, initial_data)

    def _batch_write(self):
        """Writes updates and deletes entities in a batch."""
        if self.to_put:
            ndb.put_multi(self.to_put)
            del self.to_put[:]
        if self.to_delete:
            ndb.delete_multi(self.to_delete)
            del self.to_delete[:]

    def _continue(self, cursor, batch_size, data):
        self.data = data
        q = self.get_query()
        if q is None:
            self.finish()
            return
        # If we're resuming, pick up where we left off last time.
        iter = q.iter(produce_cursors=True, start_cursor=cursor, keys_only=self.keys_only)
        try:
            # Steps over the results, returning each entity and its index.
            i = 0
            while iter.has_next():
                entity = iter.next()
                self.map(entity)
                # Do updates and deletes in batches.
                if (i + 1) % batch_size == 0:
                    # Record the last entity we processed.
                    self._batch_write()
                i += 1
                if self.terminate:
                    break

            self._batch_write()
        except DeadlineExceededError:
            # Write any unfinished updates to the datastore.
            self._batch_write()
            self.deadline_error()
            # Queue a new task to pick up where we left off.
            deferred.defer(self._continue, iter.cursor_after(), batch_size, self.data)
            logging.error(self.__class__.__name__ + ' DeadlineExceedError')
            return
        self.finish()

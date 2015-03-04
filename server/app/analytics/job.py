import time

from google.appengine.ext import ndb, deferred
from app.analytics.mapper import Mapper
from app.models import Base, User


class JobException(Exception):
    """
    Represents an Exception that happens in a Mapper or Reducer.
    """
    def __init__(self, message, job_type):
        self.message = message
        self.job_type = job_type


class JobMapper(Mapper):
    """
    A wrapper class for the NDB Mapper that stores
    map results in an NDB AnalyticsDump in addition to just mapping.
    """
    def __init__(self, kind, user, job_dump, job_mapper, filters):
        super(JobMapper, self).__init__(kind, user)
        self.job_dump = job_dump
        self.job_mapper = job_mapper
        self.set_filters(filters)

    def map(self, entity):
        try:
            map_result = self.job_mapper(entity)
        except Exception as e:
            raise JobException(e.message, "map")
        self.job_dump.map_result.append(map_result)
        self.job_dump.map_count += 1
        self.job_dump.put()


class JobReducer(object):
    """
    A class that performs a reduce job on a map result
    and stores the result in an NDB AnalyticsDump.
    """
    def __init__(self, job_dump, job_reducer):
        self.job_dump = job_dump
        self.job_reducer = job_reducer

    def run(self, map_result):
        try:
            reduce_result = self.job_reducer(map_result)
        except Exception as e:
            raise JobException(e.message, "reduce")
        self.job_dump.result = {
            'result': reduce_result
        }
        self.job_dump.put()


class Job(object):
    """
    A class that represents a map-reduce job over some sort of
    entity in NDB. Each Job corresponds to an AnalyticsDump
    entity in NDB that stores the intermediary and final results.
    The user of this object needs to specify a mapper and
    a reducer over entities.
    """
    FAILURE = "failure"
    SUCCESS = "success"

    MAPPING = "mapping"
    REDUCING = "reducing"

    def __init__(self, kind, user, mapper, reducer, filters, save_output=False):
        self.kind = kind
        self.user = user
        self.job_dump = AnalyticsDump(owner=user.key)
        self.job_mapper = JobMapper(kind, user, self.job_dump, mapper, filters)
        self.job_reducer = JobReducer(self.job_dump, reducer)
        self.save_output = save_output

    def start(self):
        self.job_dump.initialize()
        self.job_dump.update_status('starting')
        result = deferred.defer(self._run)
        return result

    def wait(self, poll_time=1):
        # Hacky polling implementation, but not sure of a better way
        status = self.get_status()
        while status != self.FAILURE and status != self.SUCCESS:
            time.sleep(poll_time)
            status = self.get_status()

    def get_status(self):
        return self.get_dump().status

    def get_dump(self):
        return self.job_dump.key.get()

    def _run(self):
        self.job_dump.update_status(self.MAPPING)
        try:
            self.job_mapper.run()
            self.job_dump.update_status(self.REDUCING)
            self.job_reducer.run(self.job_dump.map_result)
            if not self.save_output:
                self.clean_up()
            self.job_dump.update_status(self.SUCCESS)
        except JobException as e:
            self.clean_up()
            self.job_dump.error = '%s: %s' % (e.job_type, e.message)
            self.job_dump.update_status(self.FAILURE)
            raise deferred.PermanentTaskFailure()

    def clean_up(self):
        self.job_dump.map_result = None


class AnalyticsDump(Base):
    """Represents the intermediary and final results of an analytics job"""
    map_result = ndb.JsonProperty()
    map_count = ndb.IntegerProperty()
    result = ndb.JsonProperty()
    status = ndb.StringProperty()
    error = ndb.StringProperty()
    owner = ndb.KeyProperty(User)

    def initialize(self):
        self.map_result = []
        self.map_count = 0

    def update_status(self, status):
        self.status = status
        self.put()

    @classmethod
    def _can(cls, user, need, obj, query):
        if need.action == "index":
            if user.is_admin:
                return query
            return query.filter(AnalyticsDump.owner == user.key)
        if need.action == "create":
            return True
        if need.action == "get":
            if user.is_admin:
                return True
            return obj.owner == user.key
        return False

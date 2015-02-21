from google.appengine.ext import ndb, deferred
from app.analytics.mapper import Mapper
from app.models import Base


class JobMapper(Mapper):
    """
    A wrapper class for the NDB Mapper that stores
    map results in an NDB AnalyticsDump in addition to just mapping.
    """
    def __init__(self, kind, job_dump, job_mapper, filters):
        super(JobMapper, self).__init__()
        self.kind = kind
        self.job_dump = job_dump
        self.job_mapper = job_mapper
        self.set_filters(filters)

    def map(self, entity):
        try:
            map_result = self.job_mapper(entity)
        except:
            raise deferred.PermanentTaskFailure()
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
        except:
            raise deferred.PermanentTaskFailure()
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
    def __init__(self, kind, mapper, reducer, filters):
        self.job_dump = AnalyticsDump()
        self.job_mapper = JobMapper(kind, self.job_dump, mapper, filters)
        self.job_reducer = JobReducer(self.job_dump, reducer)

    def start(self):
        self.job_dump.initialize()
        self.job_dump.update_status('starting')
        deferred.defer(self._run)
        return self.job_dump

    def _run(self):
        self.job_dump.update_status('mapping')
        self.job_mapper.run()
        self.job_dump.update_status('reducing')
        self.job_reducer.run(self.job_dump.map_result)
        self.job_dump.update_status('done')


class AnalyticsDump(Base):
    """Represents the intermediary and final results of an analytics job"""
    map_result = ndb.JsonProperty()
    map_count = ndb.IntegerProperty()
    result = ndb.JsonProperty()
    status = ndb.StringProperty()

    def initialize(self):
        self.map_result = []
        self.map_count = 0

    def update_status(self, status):
        self.status = status
        self.put()

    @classmethod
    def _can(cls, user, need, obj, query):
        if user.is_admin:
            return True
        return False

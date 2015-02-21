from google.appengine.ext import ndb, deferred
from mapper import Mapper

class JobMapper(Mapper):

    def __init__(self, kind, job_dump, job_mapper, filters):
        super(JobMapper, self).__init__()
        self.kind = kind
        self.job_dump = job_dump
        self.job_mapper = job_mapper
        self.job_mapper.filters = filters

    def map(self, entity):
        map_result = self.job_mapper(entity)
        self.job_dump.map_result.append(map_result)
        self.job_dump.put()

class JobReducer(object):

    def __init__(self, job_dump, job_reducer):
        self.job_dump = job_dump
        self.job_reducer = job_reducer

    def run(self, map_result):
        reduce_result = self.job_reducer(map_result)
        self.job_dump.result = {
            'result': reduce_result
        }
        self.job_dump.put()

class Job(object):

    def __init__(self, kind, mapper, reducer, filters=[]):
        self.job_dump = AnalyticsDump()
        self.job_mapper = JobMapper(kind, self.job_dump, mapper, filters)
        self.job_reducer = JobReducer(self.job_dump, reducer)

    def start(self):
        deferred.defer(self.run)

    def run(self):
        self.job_dump.initialize()
        self.job_dump.put()
        self.job_mapper.run(1)
        self.job_reducer.run(self.job_dump.map_result)


class AnalyticsDump(ndb.Model):
    """Represents the result of a job"""

    created = ndb.DateTimeProperty(auto_now_add=True)
    map_result = ndb.JsonProperty()
    result = ndb.JsonProperty()
    status = ndb.StringProperty()

    def initialize(self):
        self.map_result = []
        self.set_status("starting")

    def set_status(self, status):
        self.status = status

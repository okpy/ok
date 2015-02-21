from job import Job, AnalyticsDump

"""SAMPLE USE CASE
from analytics import Job

def mapper(entity):
    return entity.email

def reducer(map_result):
    return len(map_result)

filters = [("email", "=", "test@example.com")]

j = Job(models.User, mapper, reducer, filters=filters)
j.start()
"""

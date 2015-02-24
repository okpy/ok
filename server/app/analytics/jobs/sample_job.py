from app import models
from app.analytics import Job

def mapper(entity):
    return entity.email

def reducer(map_result):
    return len(map_result)

def get_job(user, filters=[]):
    return Job(models.User, user, mapper, reducer, filters=filters)

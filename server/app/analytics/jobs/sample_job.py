from app import models

KIND = models.User

def mapper(entity):
    return entity.email

def reducer(map_result):
    return len(map_result)


from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import ndb
from app import models
import getpass
import sys
import pickle

def main():
    assignment = int(sys.argv[1])
    assign_key = ndb.Key('Assignmentv2', assignment)
    def auth_func():
      return (raw_input('Username:'), getpass.getpass('Password:'))

    remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', auth_func,
                                   'ok-server.appspot.com')

    queues = models.Queue.query(models.Queue.assignment == assign_key).fetch()
    subms = models.FinalSubmission.query(models.FinalSubmission.assignemnt == assign_key).fetch()

    for i, subm in enumerate(subms):
        print i
        q = queues.pop(0)
        subm.queue = q.key
        queues.append(q)

    ndb.put_multi(subms)

if __name__ == "__main__":
    main()


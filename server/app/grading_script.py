import os
import subprocess
import json, urllib
import httplib2
import base64
import ast
import requests
from oauth2client.tools import run
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from oauth2client import gce

http = httplib2.Http()
email = '887076364996-opeevtug54963jn33liq618c1kjma8d5@developer.gserviceaccount.com'
with open("ok-grader-for-CS169-project-9dd4b3bdce6e.p12") as f:
        key = f.read()
credentials = SignedJwtAssertionCredentials(email,
                                            key,
                                            'https://www.googleapis.com/auth/taskqueue')
http = credentials.authorize(http)
task_api = build('taskqueue', 'v1beta2', http=http)
lease_req = task_api.tasks().lease(project='s~seventh-abacus-87719',
                                    taskqueue='pull-queue',
                                    leaseSecs=30,
                                    numTasks=1)
result = lease_req.execute()
try:
        task= result['items'][0]
        print(task['id'])
        payload = task['payloadBase64']
        decodedResult = base64.urlsafe_b64decode(str(payload))
        dictDecResult = ast.literal_eval(decodedResult)

        subprocess.call(["chmod", "-R", "775", "grading"])
        for key, value in dictDecResult.iteritems():
                if key != "submit":
                        f = open('grading/' + key, 'w')
                        f.write(value.encode('utf-8'))
                        f.close()
        output = subprocess.check_output("./grading/grade.sh")
        score_array = [int(p) for p in output.split() if p.isdigit()]

        subm_id= task['tag']
        req_url='https://seventh-abacus-87719.appspot.com/api/v1/grade/%s/add_grade'%subm_id
        #access_token="ya29.longOkGoogleAuthToken&client_version=v1.3.30"
        data= {'score':str(score_array[0])}
        headers= {'Content-type': 'application/json'}
        r = requests.post(req_url, data=json.dumps(data), headers=headers)
        print(r.json())
        delete_req = task_api.tasks().delete(project='s~seventh-abacus-87719', taskqueue='pull-queue', task=task['id'])
        delete_req.execute()

except KeyError:
        print(result)
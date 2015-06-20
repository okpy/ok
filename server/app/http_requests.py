import httplib
import urllib
import json
from dockermap.api import DockerClientWrapper, DockerFile

def get_images():
    conn = httplib.HTTPConnection("104.154.38.163:4243")
    conn.request("GET", '/images/json')
    resp = conn.getresponse()
    responses = resp.read()
    print responses
    conn.close()

def make_docker_file():
    df =  DockerFile('ubuntu:latest')
    df.run('yes | apt-get install python')
    df.run('yes | sudo apt-get install wget')
    df.run('yes | wget http://bootstrap.pypa.io/get-pip.py')
    df.run('yes | python get-pip.py')
    df.run('yes | sudo pip install httplib2')
    df.run('yes | sudo pip install requests')
    df.run('yes | sudo pip install --upgrade oauth2client')
    df.run('yes | sudo pip install --upgrade google-api-python-client')
    df.run('yes | sudo apt-get install python-openssl')
    
    #replace with adding grading files
    df.add_file('grading_script.py')
    df.add_file('grading')
    df.add_file('ok-grader-for-CS169-project-9dd4b3bdce6e.p12')

    #change to grading file directory
    df.command = 'python grading_script.py'
    #run grading script
    return df

    
def build_file():
    client = DockerClientWrapper('104.154.38.163:4243')
    df = make_docker_file()
    # dockerfile = DockerFile('ubuntu', maintainer='ME, me@example.com')

    client.build_from_file(df, 'grader')


def create_container():
    conn = httplib.HTTPConnection("104.154.38.163:4243")
    headers = {'Content-type': 'application/json'}
    args = {
         "Hostname":"",
         "User":"",
         "Memory":0,
         "MemorySwap":0,
         "AttachStdin":False,
         "AttachStdout":True,
         "AttachStderr":True,
         "PortSpecs":None,

         "Privileged": False,
         "Tty":False,
         "OpenStdin":False,
         "StdinOnce":False,
         "Env":None,
         "Dns":None,
         "Image":"grader",
         "Volumes":{},
         "VolumesFrom":"",
         "WorkingDir":""
    }
    params = json.dumps(args)
    conn.request("POST","/containers/create", params, headers)
    response = conn.getresponse()
    print response.status, response.reason
    r = response.read()
    r = r.split(",")[0]
    r = r.split(':')

    cont_id = r[1].strip("\"")
    conn.close()
    return cont_id

def delete_container(cont_id):
    conn = httplib.HTTPConnection("104.154.38.163:4243")
    conn.request("DELETE", '/containers/' + cont_id)
    response = conn.getresponse()
    print response.status, response.reason
    conn.close()

def list_containers():
    conn = httplib.HTTPConnection("104.154.38.163:4243")
    conn.request('GET', '/containers/json')
    response = conn.getresponse()
    print response.status, response.reason
    print response.read()
    conn.close()

def start_container(cont_id):
    conn = httplib.HTTPConnection("104.154.38.163:4243")
    conn.request('POST', '/containers/' + cont_id + '/start')
    response = conn.getresponse()
    print response.status, response.reason
    conn.close()

def stop_container(cont_id):
    conn = httplib.HTTPConnection("104.154.38.163:4243")
    conn.request('POST', '/containers/' + cont_id + '/stop')
    response = conn.getresponse()
    print response.status, response.reason
    conn.close()


def send():
    # get_images()
    build_file()
    cont_id = create_container()
    start_container(cont_id)
    stop_container(cont_id)
    delete_container(cont_id)
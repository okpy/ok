"""This module contains utilities for sending data to servers."""

from client.network import update
from urllib import request, error
import json
import time

def send_to_server(access_token, messages, name, server, version, insecure=False):
    """Send messages to server, along with user authentication."""
    data = {
        'assignment': name,
        'messages': messages,
    }
    try:
        prefix = "http" if insecure else "https"
        address = prefix + '://' + server + '/api/v1/submission'
        serialized = json.dumps(data).encode(encoding='utf-8')
        # TODO(denero) Wrap in timeout (maybe use PR #51 timed execution).
        # TODO(denero) Send access token with the request
        address += "?access_token={0}&client_version={1}".format(
            access_token, version)
        req = request.Request(address)
        req.add_header("Content-Type", "application/json")
        response = request.urlopen(req, serialized)
        return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as ex:
        # print("Error while sending to server: {}".format(ex))
        try:
            if ex.code == 403:
                response = ex.read().decode('utf-8')
                response_json = json.loads(response)
                update.software_update(response_json['data']['download_link'])
            #message = response_json['message']
            #indented = '\n'.join('\t' + line for line in message.split('\n'))
            #print(indented)
            return {}
        except Exception as e:
            # print(e)
            # print("Couldn't connect to server")
            pass

def dump_to_server(access_token, msg_queue, name, server, insecure, staging_queue, version):
    while not msg_queue.empty():
        message = msg_queue.get()
        staging_queue.put(message)
        try:
            if send_to_server(access_token, message, name, server, version, insecure) == None:
                staging_queue.get() #throw away successful message
        except error.URLError as ex:
            pass
    return

def server_timer():
    """Timeout for the server."""
    time.sleep(0.8)


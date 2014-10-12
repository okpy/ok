"""This module contains utilities for communicating with the ok server."""

from urllib import request, error
import json
import time

def send_to_server(access_token, messages, name, server, version, log,
        insecure=False):
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

        log.info('Sending data to %s', address)
        req = request.Request(address)
        req.add_header("Content-Type", "application/json")
        response = request.urlopen(req, serialized)
        return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as ex:
        log.warning('Error while sending to server: %s', str(ex))
        response = ex.read().decode('utf-8')
        response_json = json.loads(response)
        log.warning('Server error message: %s', response_json['message'])
        try:
            if ex.code == 403:
                software_update(response_json['data']['download_link'], log)
            return {}
        except Exception as e:
            log.warn('Could not connect to %s', server)

def dump_to_server(access_token, msg_queue, name, server, insecure, staging_queue,
        version, log):
    while not msg_queue.empty():
        message = msg_queue.get()
        staging_queue.put(message)
        try:
            if send_to_server(access_token, message, name, server, version, log, insecure) != None:
                staging_queue.get() #throw away successful message
        except error.URLError as ex:
            log.warning('URLError: %s', str(ex))
    return

def server_timer():
    """Timeout for the server."""
    time.sleep(0.8)

#####################
# Software Updating #
#####################

def software_update(download_link, log):
    """Check for the latest version of ok and update this file accordingly."""
    log.info('Retrieving latest version from %s', download_link)

    file_destination = 'ok'
    try:
        req = request.Request(download_link)
        log.info('Sending request to %s', download_link)
        response = request.urlopen(req)

        zip_binary = response.read()
        log.info('Writing new version to %s', file_destination)
        with open(file_destination, 'wb') as f:
            f.write(zip_binary)
        log.info('Successfully wrote to %s', file_destination)
    except error.HTTPError as e:
        log.warn('Error when downloading new version of ok: %s', str(e))
    except IOError as e:
        log.warn('Error writing to %s: %s', file_destination, str(e))


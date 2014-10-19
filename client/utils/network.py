"""This module contains utilities for communicating with the ok server."""

from urllib import request, error
import json
import time
import datetime
import socket

TIMEOUT = 500

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
        response = request.urlopen(req, serialized, TIMEOUT)
        return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as ex:
        log.warning('Error while sending to server: %s', str(ex))
        response = ex.read().decode('utf-8')
        response_json = json.loads(response)
        log.warning('Server error message: %s', response_json['message'])
        try:
            if ex.code == 403:
                if software_update(response_json['data']['download_link'], log):
                    raise SoftwareUpdated
            return {}
        except Exception as e:
            log.warning('Could not connect to %s', server)

def dump_to_server(access_token, msg_list, name, server, insecure, version, log, send_all=False):
    #TODO(soumya) Change after we get data on ok_messages
    # This request is temporary- it'll be removed in the next day or two.
    send_all = False
    try:
        prefix = "http" if insecure else "https"
        address = prefix + "://" + server + "/api/v1/nothing"
        address += "?access_token={0}&ok_messages={1}".format(access_token,
                len(msg_list))
        req = request.Request(address)
        response = request.urlopen(req, b"", 0.4)
    except Exception as e:
        pass

    stop_time = datetime.datetime.now() + datetime.timedelta(milliseconds=TIMEOUT)
    initial_length = len(msg_list)
    while msg_list:
        if not send_all and datetime.datetime.now() > stop_time:
            break
        message = msg_list[-1]
        try:
            response = send_to_server(access_token, message, name, server, version, log, insecure)
            if response:
                msg_list.pop()
            if send_all:
                print("Submitting project... {0}% complete".format(len(msg_list)*100/initial_length))
        except SoftwareUpdated:
            print("ok was updated. We will now terminate this run of ok.")
            log.info('ok was updated. Abort now; messages will be sent '
                     'to server on next invocation')
            return
        except error.URLError as ex:
            log.warning('URLError: %s', str(ex))
        except socket.timeout as ex:
            log.warning("socket.timeout: %s", str(ex))
    return

def server_timer():
    """Timeout for the server."""
    time.sleep(0.8)

#####################
# Software Updating #
#####################

class SoftwareUpdated(BaseException):
    pass

def software_update(download_link, log):
    """Check for the latest version of ok and update this file accordingly.

    RETURN:
    bool; True if the newest version of ok was written to the filesystem, False
    otherwise.
    """
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
            os.fsync(f)
        log.info('Successfully wrote to %s', file_destination)
        return True
    except error.HTTPError as e:
        log.warning('Error when downloading new version of ok: %s', str(e))
    except IOError as e:
        log.warning('Error writing to %s: %s', file_destination, str(e))
    return False

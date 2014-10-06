"""This module handles all updating mechanisms."""

from urllib import request, error

#####################
# Software Updating #
#####################

def software_update(download_link):
    """Check for the latest version of ok and update this file accordingly."""
    #print("We detected that you are running an old version of ok.py: {0}".format(VERSION))

    # Get server version

    try:
        req = request.Request(download_link)
        response = request.urlopen(req)

        zip_binary = response.read()
        with open('ok', 'wb') as f:
            f.write(zip_binary)
        #print("Done updating!")
    except error.HTTPError:
        # print("Error when downloading new version")
        pass


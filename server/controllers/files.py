import logging
import os
from urllib.parse import urlencode
import libcloud

from flask import Blueprint, redirect, request, Response, abort
from flask_login import login_required, current_user

from server.extensions import storage
from server.models import ExternalFile

files = Blueprint('files', __name__)

logger = logging.getLogger(__name__)

@files.route("/files/<hashid:file_id>")
@login_required
def file_url(file_id):
    ext_file = ExternalFile.query.filter_by(id=file_id, deleted=False).first()
    if not ext_file or not ExternalFile.can(ext_file, current_user, 'download'):
        logger.info("Access file without permission by {0}".format(current_user.email))
        abort(404)

    try:
        storage_obj = ext_file.object()
    except libcloud.common.types.InvalidCredsError:
        logger.warning("Could not get file {0} - {1}".format(file_id, ext_file.filename),
                       exc_info=True)
        storage_obj = None

    if storage_obj is None:
        abort(404, "File does not exist")
    basename = os.path.basename(ext_file.filename)
    # Do not use .download_url for local storage.
    if storage.provider == libcloud.storage.types.Provider.LOCAL:
        response = Response(storage.get_object_stream(storage_obj),
                            mimetype=ext_file.mimetype)
        response.headers["Content-Security-Policy"] = "default-src 'none';"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Disposition"] = ("attachment; filename={0!s}"
                                                   .format(basename))
        return response
    else:
        postpend = '&'
        if request.args.get('raw'):
            postpend += urlencode({'response-content-type': ext_file.mimetype})
        elif request.args.get('download'):
            postpend += urlencode({'response-content-disposition': 'attachment',
                                  'filename': basename})
        url = storage.get_blob_url(storage_obj.name)
        return redirect(url + postpend)

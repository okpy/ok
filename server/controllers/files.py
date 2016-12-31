import tempfile
import logging

import libcloud
from flask import Blueprint, url_for, redirect, send_from_directory, abort
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
        return abort(404)
    try:
        storage_obj = ext_file.object
    except libcloud.common.types.InvalidCredsError as e:
        logger.warning("Could not get file {0} - {1}".format(file_id, ext_file.filename),
                       exc_info=True)
        storage_obj = None
        raise e

    if storage_obj is None:
        return abort(404, "File does not exist")

    # Do not use .download_url for local storage.
    if "local" in storage.driver.name.lower():
        return redirect(url_for('.send_file', file_id=ext_file.id))
    else:
        return redirect(storage_obj.download_url())

@files.route("/files/<hashid:file_id>/download")
@login_required
def send_file(file_id):
    """ Serve file by downloading it into a local directory.
    Generally only used by local file system
    """
    ext_file = ExternalFile.query.get(file_id)
    if not ext_file or not ExternalFile.can(ext_file, current_user, 'download'):
        return abort(404)
    storage_obj = ext_file.object
    with tempfile.TemporaryDirectory() as tmp_dir:
        dst_path = '/{}/{}'.format(tmp_dir, storage_obj.name)
        storage_obj.download(destination_path=dst_path)
        response = send_from_directory(tmp_dir, storage_obj.name)
        response.headers["Content-Security-Policy"] = "default-src 'none';"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Disposition"] = ("attachment; filename={0!s}"
                                                   .format(ext_file.filename))

        return response
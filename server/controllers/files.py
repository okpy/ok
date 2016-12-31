import tempfile

from flask import Blueprint, url_for, redirect, send_from_directory, abort
from flask_login import login_required, current_user

from server.extensions import storage
from server.models import ExternalFile

files = Blueprint('files', __name__)

@files.route("/files/<hashid:file_id>")
@login_required
def file_url(file_id):
    ext_file = ExternalFile.query.filter_by(id=file_id, deleted=False).first()
    if not ext_file or not ExternalFile.can(ext_file, current_user, 'download'):
        return abort(404)
    storage_obj = ext_file.object
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
        return response

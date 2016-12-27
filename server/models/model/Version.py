from server.models.db import db, Model
from server.extensions import cache

class Version(Model):
    id = db.Column(db.Integer(), primary_key=True)
    # software name e.g. 'ok'
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    current_version = db.Column(db.String(255))
    download_link = db.Column(db.Text())

    @staticmethod
    @cache.memoize(1800)
    def get_current_version(name):
        version = Version.query.filter_by(name=name).one_or_none()
        if version:
            return version.current_version, version.download_link
        return None, None

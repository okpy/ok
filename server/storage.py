import os
import hmac
import hashlib
import base64
import datetime as dt
from urllib.parse import urlencode, urljoin

from werkzeug.utils import secure_filename
from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

def get_provider(name):
    if hasattr(Provider, name.upper()):
        return getattr(Provider, name.upper())
    else:
        raise AttributeError('Provider {} is unknown'.format(name))

class Storage:
    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        key = app.config.get('STORAGE_KEY')
        secret = app.config.get('STORAGE_SECRET')
        self.container_name = app.config.get('STORAGE_CONTAINER')
        self.provider_name = app.config.get('STORAGE_PROVIDER', 'LOCAL')

        self.provider = get_provider(self.provider_name)

        if self.provider == Provider.LOCAL:
            if not os.path.exists(self.container_name):
                os.makedirs(self.container_name)
            key = self.container_name
            self.container_name = ''  # Container name represents a child folder.

        driver_cls = get_driver(self.provider)
        self.driver = driver_cls(key, secret)
        # Also test credentials by getting the container
        self.container = self.driver.get_container(container_name=self.container_name)

    def upload(self, iterator, name=None, container=None, prefix=""):
        """ Upload (and overwrite) files on storage provider.
        To avoid overwriting files see `_safe_object_name` in Flask-Cloudy.
        File Names will always be sanitized to prevent directory traversal.
        """
        if container is None:
            container = self.container
        else:
            container = self.driver.get_container(container_name=container)

        obj_name = secure_filename(name)
        if self.provider == Provider.LOCAL:
            prefixed_name = prefix.lstrip("/") + obj_name
            # No folders locally to prevent directory traversal.
            obj_name = secure_filename(prefixed_name)
        elif prefix:
            obj_name = prefix.lstrip("/") + name

        obj = self.driver.upload_object_via_stream(iterator=iterator,
                                                   container=container,
                                                   object_name=obj_name)
        return obj

    def get_blob(self, obj_name, container_name=None):
        if container_name is None:
            container_name = self.container_name
        if self.provider == Provider.LOCAL:
            # Prevent malicious calls to get_blob locally
            obj_name = secure_filename(obj_name)

        return self.driver.get_object(container_name=container_name,
                                      object_name=obj_name)

    def get_url(self, object_path):
        """
        Return the unsigned URL of the object
        :param secure: bool - To use https
        :return: str
        """
        driver_name = self.driver.name.lower()
        if 's3' in driver_name:
            base_url = 'https://%s'.format(self.driver.connection.host)
            url = urljoin(base_url, object_path)
        elif 'google' in driver_name:
            url = urljoin('https://storage.googleapis.com', object_path)
        elif 'azure' in driver_name:
            base_url = 'https://%s.blob.core.windows.net'.format(self.driver.key)
            url = urljoin(base_url, object_path)
        else:
            raise Exception('Unsupported Storage Driver for URL')

        return url

    def get_blob_url(self, obj_name, container_name=None, timeout=60):
        """ Mostly from https://github.com/mardix/flask-cloudy/blob/master/flask_cloudy.py
        """
        if container_name is None:
            container_name = self.container_name
        driver_name = self.driver.name.lower()
        expires = (dt.datetime.now() + dt.timedelta(seconds=timeout)).strftime("%s")

        if 's3' in driver_name or 'google' in driver_name:
            keyIdName = "AWSAccessKeyId" if "s3" in driver_name else "GoogleAccessId"
        else:
            raise Exception('{0} does not support signed urls'.format(driver_name))

        obj_path = "{0}/{1}".format(self.container.name, obj_name)
        s2s = ("GET\n\n\n{expires}\n/{object_name}"
               .format(expires=expires, object_name=obj_path).encode('utf-8'))
        hmac_obj = hmac.new(self.driver.secret.encode('utf-8'), s2s, hashlib.sha1)
        encoded_sig = base64.encodestring(hmac_obj.digest()).strip()
        params = {
            keyIdName: self.driver.key,
            "Expires": expires,
            "Signature": encoded_sig
        }
        url_kv = urlencode(params)
        secure_url = self.get_url(obj_path)
        return "{0}?{1}".format(secure_url, url_kv)

    def get_object_stream(self, object):
        """ Data stream of the libcloud object.
        """
        return self.driver.download_object_as_stream(object)

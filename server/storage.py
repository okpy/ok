import os
import hmac
import hashlib
import base64
import datetime as dt
import logging
import random
import string
from urllib.parse import urlencode, urljoin

from werkzeug.utils import secure_filename
from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver
from azure.storage.blob import BlockBlobService, BlobPermissions

logger = logging.getLogger(__name__)

def get_provider(name):
    if hasattr(Provider, name.upper()):
        return getattr(Provider, name.upper())
    else:
        raise AttributeError('Provider {} is unknown'.format(name))

def sanitize_filename(fname, prefix=False):
    """ Sanitize filename and add random prefix to file to
    handle duplicate names and potentially empty sequences from secure_filename
    """
    random_prefix = ''.join([random.choice(string.ascii_letters + string.digits)
                             for n in range(5)])
    secured_name = secure_filename(fname)
    if not secured_name:
        return random_prefix
    elif prefix:
        return "{0}-{1}".format(random_prefix, secured_name)
    else:
        return secured_name


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
        driver_cls = get_driver(self.provider)

        if self.provider == Provider.LOCAL:
            if not os.path.exists(self.container_name):
                os.makedirs(self.container_name)
            key = self.container_name
            self.container_name = ''  # Container name represents a child folder.
        elif self.provider == Provider.GOOGLE_STORAGE:
            # Enable chunked uploads for performance improvement
            # Filed Issue: https://issues.apache.org/jira/browse/LIBCLOUD-895
            driver_cls.supports_chunked_encoding = True

        self.driver = driver_cls(key, secret)
        # Also test credentials by getting the container
        self.container = self.driver.get_container(container_name=self.container_name)

    def upload(self, iterable, name=None, container=None, prefix=""):
        """ Upload (and overwrite) files on storage provider.
        To avoid overwriting files see `_safe_object_name` in Flask-Cloudy.
        or use sanitize_filename(name, prefix=True).
        File Names will always be sanitized to prevent directory traversal.
        """
        if container is None:
            container = self.container
        else:
            container = self.driver.get_container(container_name=container)

        obj_name = sanitize_filename(name)
        if self.provider == Provider.LOCAL:
            prefixed_name = prefix.lstrip("/") + obj_name
            # No folders locally to prevent directory traversal.
            obj_name = sanitize_filename(prefixed_name)
        elif prefix:
            obj_name = prefix.lstrip("/") + obj_name
            obj_name = "/".join(part if part not in (".", "..") else "_"
                                for part in obj_name.split("/"))
        logger.info("Beginning upload of {}".format(name))
        obj = self.driver.upload_object_via_stream(iterator=iter(iterable),
                                                   container=container,
                                                   object_name=obj_name)
        logger.info("Completed upload of {}".format(name))
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
            base_url = 'https://{}'.format(self.driver.connection.host)
            url = urljoin(base_url, object_path)
        elif 'google' in driver_name:
            url = urljoin('https://storage.googleapis.com', object_path)
        elif 'azure' in driver_name:
            base_url = 'https://{}.blob.core.windows.net'.format(self.driver.key)
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
        expiry_timestamp = (dt.datetime.now() + dt.timedelta(seconds=timeout)).timestamp()

        if 's3' in driver_name or 'google' in driver_name:
            keyIdName = "AWSAccessKeyId" if "s3" in driver_name else "GoogleAccessId"
            return self._generate_google_aws_signed_url(keyIdName, obj_name, expiry_timestamp)
        elif 'azure' in driver_name:
            return self._generate_azure_signed_url(obj_name, expiry_timestamp)
        else:
            raise Exception('{0} does not support signed urls'.format(driver_name))

    def get_object_stream(self, object):
        """ Data stream of the libcloud object.
        """
        return self.driver.download_object_as_stream(object)

    def _generate_google_aws_signed_url(self, keyIdName, obj_name, expiry_timestamp):
        """ Generates a signed URL compatible with Google Cloud and AWS S3
        """
        expires = int(expiry_timestamp)
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

    def _generate_azure_signed_url(self, obj_name, expiry_timestamp):
        """ Generates a signed URL compatible with Azure Blob Storage
        """
        # libcloud encodes the access key, so it needs decoding
        secret_as_string = base64.b64encode(self.driver.secret).decode()

        # azure expiry times need to be ISO8601 (no milliseconds, and with the timezone character)
        expires = dt.datetime.utcfromtimestamp(expiry_timestamp).replace(microsecond=0).isoformat() + 'Z'

        blob_service = BlockBlobService(self.driver.key, secret_as_string)

        signed_url = blob_service.make_blob_url(
            self.container.name,
            obj_name,
            sas_token=blob_service.generate_blob_shared_access_signature(
                self.container.name,
                obj_name,
                permission=BlobPermissions(read=True),
                expiry=expires))

        return signed_url

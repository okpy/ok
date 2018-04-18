"""
This module contains integration tests which verify the behavior of the storage
module against supported cloud storage providers. The tests for the local
(directory-based) storage backend are re-used and run for each supported cloud
storage provider. To add tests for a new provider, create a new subclass of
CloudTestFile.

To run tests for Google Cloud Platform, set the following environment variables:
- GCP_STORAGE_KEY
- GCP_STORAGE_SECRET

"""
# TODO(@colinschoen) Configure CI to run the full integration test suite only on protected branches like master.

import os
import random
import unittest

import requests

from server.extensions import storage
from tests.test_files import TestFile


class CloudTestFile(TestFile):
    storage_provider = ""
    key_env_name = ""
    secret_env_name = ""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.storage_key = os.environ.get(cls.key_env_name)
        cls.storage_secret = os.environ.get(cls.secret_env_name)
        if not cls.storage_key or not cls.storage_secret:
            raise unittest.SkipTest("Cloud storage credentials for {} not configured".format(cls.storage_provider))

    def create_app(self):
        os.environ["STORAGE_PROVIDER"] = self.storage_provider
        os.environ["STORAGE_KEY"] = self.storage_key
        os.environ["STORAGE_SECRET"] = self.storage_secret
        os.environ.setdefault("STORAGE_CONTAINER", "okpycloudfilestest{}".format(random.randint(0, 100000)))

        return super().create_app()

    def tearDown(self):
        super().tearDown()

        del os.environ["STORAGE_PROVIDER"]
        del os.environ["STORAGE_KEY"]
        del os.environ["STORAGE_SECRET"]
        del os.environ["STORAGE_CONTAINER"]

        for obj in storage.container.list_objects():
            obj.delete()

        storage.container.delete()

    def fetch_file(self, url):
        client_response = self.client.get(url)
        self.assertStatus(client_response, 302)
        redirect_response = requests.get(client_response.location)
        redirect_response.raise_for_status()
        return redirect_response.headers, redirect_response.content

    def verify_download_headers(self, headers, filename, content_type):
        pass


class GoogleCloudTestFile(CloudTestFile):
    storage_provider = "GOOGLE_STORAGE"
    key_env_name = "GCP_STORAGE_KEY"
    secret_env_name = "GCP_STORAGE_SECRET"

    test_prefix_expected_obj_name = 'test/fizz.txt'
    test_malicious_directory_traversal_expected_obj_name = 'test/_/_/fizz.txt'


del CloudTestFile, TestFile

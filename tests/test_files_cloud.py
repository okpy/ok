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

    __env_backup = {}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        storage_key = os.environ.get(cls.key_env_name)
        storage_secret = os.environ.get(cls.secret_env_name)
        storage_container = "okpycloudfilestest{}".format(random.randint(0, 100000))

        if not storage_key or not storage_secret:
            raise unittest.SkipTest("Cloud storage credentials for {} not configured".format(cls.storage_provider))

        cls.set_environment_variable("STORAGE_PROVIDER", cls.storage_provider)
        cls.set_environment_variable("STORAGE_KEY", storage_key)
        cls.set_environment_variable("STORAGE_SECRET", storage_secret)
        cls.set_environment_variable("STORAGE_CONTAINER", storage_container)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        cls.restore_environment_variable("STORAGE_PROVIDER")
        cls.restore_environment_variable("STORAGE_KEY")
        cls.restore_environment_variable("STORAGE_SECRET")
        cls.restore_environment_variable("STORAGE_CONTAINER")

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

    @classmethod
    def set_environment_variable(cls, key, value):
        cls.__env_backup[key] = os.environ.get(key)
        os.environ[key] = value

    @classmethod
    def restore_environment_variable(cls, key):
        original_value = cls.__env_backup.get(key)

        if original_value is None:
            del os.environ[key]
        else:
            os.environ[key] = original_value


class GoogleCloudTestFile(CloudTestFile):
    storage_provider = "GOOGLE_STORAGE"
    key_env_name = "GCP_STORAGE_KEY"
    secret_env_name = "GCP_STORAGE_SECRET"

    test_prefix_expected_obj_name = 'test/fizz.txt'
    test_malicious_directory_traversal_expected_obj_name = 'test/_/_/fizz.txt'


del CloudTestFile, TestFile

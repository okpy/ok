"""
This module contains integration tests which verify the behavior of the storage
module against supported cloud storage providers. The tests for the local
(directory-based) storage backend are re-used and run for each supported cloud
storage provider. To add tests for a new provider, create a new subclass of
CloudTestFile.

To run tests for Google Cloud Platform, set the following environment variables:
- GCP_STORAGE_KEY
- GCP_STORAGE_SECRET
- GCP_STORAGE_CONTAINER

"""
# TODO(@colinschoen) Configure CI to run the full integration test suite only on protected branches like master.

import os
import unittest

import requests

from tests.test_files import TestFile


class EnvironmentMutationMixin(object):
    __env_backup = {}

    @classmethod
    def set_environment_variable(cls, key, value):
        cls.__env_backup.setdefault(key, os.environ.get(key))
        os.environ[key] = value

    @classmethod
    def restore_environment_variable(cls, key):
        original_value = cls.__env_backup.get(key)

        if original_value is None:
            del os.environ[key]
        else:
            os.environ[key] = original_value


class CloudTestFile(TestFile, EnvironmentMutationMixin):
    storage_provider = ""
    key_env_name = ""
    secret_env_name = ""
    container_env_name = ""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        storage_key = os.environ.get(cls.key_env_name)
        storage_secret = os.environ.get(cls.secret_env_name)
        storage_container = os.environ.get(cls.container_env_name)

        if not storage_key or not storage_secret or not storage_container:
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

    def fetch_file(self, url):
        client_response = self.client.get(url)
        self.assertStatus(client_response, 302)
        redirect_response = requests.get(client_response.location)
        redirect_response.raise_for_status()
        return redirect_response.headers, redirect_response.content

    def verify_download_headers(self, headers, filename, content_type):
        pass

    test_prefix_expected_obj_name = 'test/fizz.txt'
    test_malicious_directory_traversal_expected_obj_name = 'test/_/_/fizz.txt'


class GoogleCloudTestFile(CloudTestFile):
    storage_provider = "GOOGLE_STORAGE"
    key_env_name = "GCP_STORAGE_KEY"
    secret_env_name = "GCP_STORAGE_SECRET"
    container_env_name = "GCP_STORAGE_CONTAINER"


del CloudTestFile, TestFile

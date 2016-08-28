import datetime as dt
import json
import os

import requests
from flask_oauthlib.client import OAuth

from server.models import (db, Assignment, Backup, Course, User,
                           Client, Grant, Token)
from server.utils import encode_id

from tests import OkTestCase

class TestOAuth(OkTestCase):
    def _setup_clients(self, scope='email'):
        self.setup_course()

        self.oauth_client = Client(
            name='Testing Client', client_id='normal', client_secret='normal',
            redirect_uris=['http://127.0.0.1:8000/authorized'],
            is_confidential=False,
            description='Sample App for testing OAuth',
            default_scopes=scope
        )
        db.session.add(self.oauth_client)
        db.session.commit()

        self.temp_grant = Grant(
            user_id=self.user1.id, client_id='normal',
            code='12345', scopes=['email'],
            expires=dt.datetime.utcnow() + dt.timedelta(seconds=100)
        )
        db.session.add(self.temp_grant)

        self.expired_token = Token(
            user_id=self.user1.id, client_id='normal',
            scopes=[scope],
            access_token='expired', expires=dt.datetime.utcnow() - dt.timedelta(seconds=1)
        )
        db.session.add(self.expired_token)

        self.valid_token = Token(
            user_id=self.user1.id, client_id='normal',
            scopes=[scope],
            access_token='soo_valid', expires=dt.datetime.utcnow() + dt.timedelta(seconds=3600)
        )
        db.session.add(self.valid_token)

        self.valid_token_bad_scope = Token(
            user_id=self.user1.id, client_id='normal',
            scopes=['invalid'],
            access_token='soo_valid12', expires=dt.datetime.utcnow() + dt.timedelta(seconds=3600)
        )
        db.session.add(self.valid_token_bad_scope)

        self.valid_token_all_scope = Token(
            user_id=self.user1.id, client_id='normal',
            scopes=['all'],
            access_token='soo_valid322', expires=dt.datetime.utcnow() + dt.timedelta(seconds=3600)
        )
        db.session.add(self.valid_token_all_scope)
        db.session.commit()

    def test_api(self):
        self._setup_clients()
        response = self.client.get("/api/v3/user/?access_token={}".format(self.valid_token.access_token))
        self.assert_200(response)

        response = self.client.get("/api/v3/user/?access_token={}".format(self.valid_token_bad_scope.access_token))
        self.assert_403(response)

        response = self.client.get("/api/v3/user/?access_token={}".format(''))
        self.assert_401(response)

        response = self.client.get("/api/v3/user/")
        self.assert_401(response)

    def test_api_scopes(self):
        self._setup_clients()
        response = self.client.get(("/api/v3/assignment/{}/group/{}?access_token={}"
                                    .format(self.assignment.name, self.user1.email,
                                            self.valid_token.access_token)))
        self.assert_403(response)

        response = self.client.get(("/api/v3/assignment/{}/group/{}?access_token={}"
                                    .format(self.assignment.name, self.user1.email,
                                            self.valid_token_all_scope.access_token)))
        self.assert_200(response)

    def test_public_scopes(self):
        self._setup_clients()
        response = self.client.get(("/api/v3/assignment/{}"
                                    .format(self.assignment.name)))
        self.assert_401(response)

        response = self.client.get(("/api/v3/assignment/{}?access_token={}"
                                    .format(self.assignment.name, self.valid_token.access_token)))
        self.assert_200(response)

        response = self.client.get(("/api/v3/assignment/{}?access_token={}"
                                    .format(self.assignment.name, self.valid_token_bad_scope.access_token)))
        self.assert_200(response)

    def test_client_form(self):
        self._setup_clients()
        self.login(self.admin.email)

        redirect_uris = [
            'http://myapp.com/authorize',
            'https://myapp.com/authorize',
        ]
        default_scopes = ['email', 'all']
        data = {
            'name': 'My App',
            'description': 'A web app that does stuff',
            'client_id': 'my-app',
            'client_secret': 'my-secret-key',
            'is_confidential': 'true',
            'redirect_uris': ', '.join(redirect_uris),
            'default_scopes': ', '.join(default_scopes),
        }

        self.assert_200(self.client.post('/admin/clients/',
            data=data, follow_redirects=True))

        client = Client.query.filter_by(client_id="my-app").one()
        self.assertEqual(client.name, data['name'])
        self.assertEqual(client.description, data['description'])
        self.assertEqual(client.client_id, data['client_id'])
        self.assertEqual(client.client_secret, data['client_secret'])
        self.assertTrue(client.is_confidential)
        self.assertEqual(client.redirect_uris, redirect_uris)
        self.assertEqual(client.default_scopes, default_scopes)

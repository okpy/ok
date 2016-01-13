#! ../env/bin/python
# -*- coding: utf-8 -*-

import pytest

@pytest.mark.usefixtures("testapp")
class TestLogin:
    def test_login(self, testapp):
        """ Tests if the login and logout form functions """

        rv = testapp.post('/testing-login/authorized', data=dict(
            name='Marty McFly',
            email='martymcfly@aol.com'
        ), follow_redirects=True)
        assert rv.status_code == 200

        rv = testapp.get('/logout', follow_redirects=True)
        assert rv.status_code == 200

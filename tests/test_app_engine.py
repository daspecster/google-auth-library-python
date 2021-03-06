# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

import mock
import pytest

from google.auth import app_engine


@pytest.fixture
def app_identity_mock(monkeypatch):
    """Mocks the app_identity module for google.auth.app_engine."""
    app_identity_mock = mock.Mock()
    monkeypatch.setattr(
        app_engine, 'app_identity', app_identity_mock)
    yield app_identity_mock


def test_get_project_id(app_identity_mock):
    app_identity_mock.get_application_id.return_value = mock.sentinel.project
    assert app_engine.get_project_id() == mock.sentinel.project


def test_get_project_id_missing_apis():
    with pytest.raises(EnvironmentError) as excinfo:
        assert app_engine.get_project_id()

    assert excinfo.match(r'App Engine APIs are not available')


class TestCredentials(object):
    def test_missing_apis(self):
        with pytest.raises(EnvironmentError) as excinfo:
            app_engine.Credentials()

        assert excinfo.match(r'App Engine APIs are not available')

    def test_default_state(self, app_identity_mock):
        credentials = app_engine.Credentials()

        # Not token acquired yet
        assert not credentials.valid
        # Expiration hasn't been set yet
        assert not credentials.expired
        # Scopes are required
        assert not credentials.scopes
        assert credentials.requires_scopes

    def test_with_scopes(self, app_identity_mock):
        credentials = app_engine.Credentials()

        assert not credentials.scopes
        assert credentials.requires_scopes

        scoped_credentials = credentials.with_scopes(['email'])

        assert scoped_credentials.has_scopes(['email'])
        assert not scoped_credentials.requires_scopes

    def test_service_account_email_implicit(self, app_identity_mock):
        app_identity_mock.get_service_account_name.return_value = (
            mock.sentinel.service_account_email)
        credentials = app_engine.Credentials()

        assert (credentials.service_account_email ==
                mock.sentinel.service_account_email)
        assert app_identity_mock.get_service_account_name.called

    def test_service_account_email_explicit(self, app_identity_mock):
        credentials = app_engine.Credentials(
            service_account_id=mock.sentinel.service_account_email)

        assert (credentials.service_account_email ==
                mock.sentinel.service_account_email)
        assert not app_identity_mock.get_service_account_name.called

    @mock.patch(
        'google.auth._helpers.utcnow',
        return_value=datetime.datetime.min)
    def test_refresh(self, now_mock, app_identity_mock):
        token = 'token'
        ttl = 100
        app_identity_mock.get_access_token.return_value = token, ttl
        credentials = app_engine.Credentials(scopes=['email'])

        credentials.refresh(None)

        app_identity_mock.get_access_token.assert_called_with(
            credentials.scopes, credentials._service_account_id)
        assert credentials.token == token
        assert credentials.expiry == (
            datetime.datetime.min + datetime.timedelta(seconds=ttl))
        assert credentials.valid
        assert not credentials.expired

    def test_sign_bytes(self, app_identity_mock):
        app_identity_mock.sign_blob.return_value = mock.sentinel.signature
        credentials = app_engine.Credentials()
        to_sign = b'123'

        signature = credentials.sign_bytes(to_sign)

        assert signature == mock.sentinel.signature
        app_identity_mock.sign_blob.assert_called_with(to_sign)

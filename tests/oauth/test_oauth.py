from unittest.mock import patch, MagicMock

import pytest
from authlib.jose import JWTClaims
from authlib.jose.errors import BadSignatureError
from django.core.exceptions import ImproperlyConfigured
from oauthlib.oauth2 import TokenExpiredError
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from vitrina.api.oauth import (
    OAuth2AuthenticationWithLocalJWK,
    IsOAuthTokenValid,
    OAuthTokenHasScopes,
    OAuthTokenHasValidOrganizationClaim, OAuthClientAuthenticator
)


@pytest.fixture
def factory():
    return APIRequestFactory()


class DummyView:
    def __init__(self, required_scopes=None, kwargs=None):
        self.required_scopes = required_scopes or []
        self.kwargs = kwargs or {}


def test_authenticate_success(factory):
    request = factory.get("/")

    mock_claims = MagicMock()

    with patch("vitrina.api.oauth.OAuthClientAuthenticator.retrieve_and_verify_token", return_value=mock_claims):
        auth = OAuth2AuthenticationWithLocalJWK()
        user, claims = auth.authenticate(request)

        assert user.is_anonymous
        assert claims == mock_claims


def test_authenticate_token_missing(factory):
    request = factory.get("/")

    with patch.object(OAuthClientAuthenticator, "retrieve_and_verify_token", return_value=None):
        auth = OAuth2AuthenticationWithLocalJWK()
        with pytest.raises(AuthenticationFailed, match="Token not supplied"):
            auth.authenticate(request)


@pytest.mark.parametrize("error", ["bad", "expired"])
def test_authenticate_token_invalid(factory, error):
    request = factory.get("/")

    error_cls = {
        "bad": BadSignatureError,
        "expired": TokenExpiredError
    }[error]

    mock_error = error_cls("Invalid")

    with patch.object(OAuthClientAuthenticator, "retrieve_and_verify_token", side_effect=mock_error):
        auth = OAuth2AuthenticationWithLocalJWK()
        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request)


def test_is_oauth_token_valid_true():
    request = MagicMock()
    request.auth = MagicMock(spec=JWTClaims)
    permission = IsOAuthTokenValid()

    assert permission.has_permission(request, None) is True
    request.auth.validate.assert_called_once()


def test_is_oauth_token_valid_invalid_auth():
    request = MagicMock()
    request.auth = None
    permission = IsOAuthTokenValid()

    with pytest.raises(AttributeError):  # Because validate() is called unconditionally
        permission.has_permission(request, None)


def test_oauth_token_has_scopes_valid():
    request = MagicMock()
    request.auth = {"scope": "read write"}
    view = DummyView(required_scopes=["read"])

    permission = OAuthTokenHasScopes()
    assert permission.has_permission(request, view) is True


def test_oauth_token_has_scopes_missing():
    request = MagicMock()
    request.auth = {"scope": "read"}
    view = DummyView(required_scopes=["write"])

    permission = OAuthTokenHasScopes()
    assert permission.has_permission(request, view) is False


def test_oauth_token_has_scopes_unspecified():
    request = MagicMock()
    request.auth = {"scope": "read"}
    view = DummyView(required_scopes=[])

    permission = OAuthTokenHasScopes()
    assert permission.has_permission(request, view) is True


def test_oauth_token_get_scopes_missing_attribute():
    request = MagicMock()
    view = object()

    with pytest.raises(ImproperlyConfigured):
        OAuthTokenHasScopes.get_scopes(request, view)


def test_oauth_token_valid_org_success():
    request = MagicMock()
    claims = {"org_id": "123"}
    request.auth = claims

    mock_org = MagicMock()
    mock_org.pk = "123"

    view = DummyView(kwargs={"organization_id": "123"})

    with patch.object(OAuthClientAuthenticator, "resolve_organization_from_token", return_value=mock_org):
        permission = OAuthTokenHasValidOrganizationClaim()
        assert permission.has_permission(request, view) is True
        assert request.organization == mock_org


def test_oauth_token_valid_org_mismatch():
    request = MagicMock()
    request.auth = {"org_id": "123"}
    view = DummyView(kwargs={"organization_id": "456"})

    mock_org = MagicMock()
    mock_org.pk = "123"

    with patch.object(OAuthClientAuthenticator, "resolve_organization_from_token", return_value=mock_org):
        permission = OAuthTokenHasValidOrganizationClaim()
        assert permission.has_permission(request, view) is False


def test_oauth_token_valid_org_none():
    request = MagicMock()
    request.auth = {"org_id": "123"}
    view = DummyView(kwargs={"organization_id": "123"})

    with patch.object(OAuthClientAuthenticator, "resolve_organization_from_token", return_value=None):
        permission = OAuthTokenHasValidOrganizationClaim()
        assert permission.has_permission(request, view) is False

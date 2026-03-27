import time
from typing import Any, Optional, List
from unittest.mock import patch, MagicMock, Mock

import pytest
from authlib.jose import JWTClaims, JsonWebKey, jwt
from authlib.jose.errors import BadSignatureError
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from oauthlib.oauth2 import TokenExpiredError
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from vitrina.api.oauth import (
    OAuth2Authentication,
    IsOAuthTokenValid,
    OAuthTokenHasScopes,
    OAuthTokenHasValidOrganizationClaim,
    OAuthClientAuthenticator,
)
from vitrina.orgs.factories import OrganizationFactory
from vitrina.uapi.factories import AgentEnvironmentFactory


class TestView:
    def __init__(self, required_scopes: list | None = None, kwargs: Any = None):
        self.required_scopes = required_scopes or []
        self.kwargs = kwargs or {}


@pytest.fixture
def request_factory():
    return APIRequestFactory()


@pytest.fixture
def rsa_keypair():
    private = JsonWebKey.generate_key("RSA", 2048, is_private=True)
    public = JsonWebKey.import_key(private.as_dict(is_private=False))
    return private.as_dict(), public.as_dict()


@pytest.fixture
def download_only_oauth_settings(settings):
    settings.OAUTH_SERVER_PUBLIC_JWK_JSON = None
    settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_PATH = "/tmp/jwks"
    settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_URL = "https://example.com/jwks"
    settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_CACHE_TIMEOUT = 300
    return settings


@pytest.fixture
def mock_endpoints(requests_mock, rsa_keypair, download_only_oauth_settings):
    _, public = rsa_keypair
    requests_mock.get(
        download_only_oauth_settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_URL,
        json={"keys": [public]},
        status_code=200,
    )
    return requests_mock


@pytest.fixture
def decoded_jwt() -> JWTClaims:
    key = JsonWebKey.generate_key(kty="oct", crv_or_size=256, is_private=True)
    claims = {
        "iss": "issuer",
        "sub": "client",
        "scope": "test_scope",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    encoded = jwt.encode({"alg": "HS256"}, claims, key).decode()
    decoded = jwt.decode(encoded, key)

    return decoded


def test_authentication_with_local_jwk_authenticate_success(request_factory: APIRequestFactory, decoded_jwt: JWTClaims):
    request = request_factory.get("/", HTTP_AUTHORIZATION="Bearer <token>")

    with patch.object(OAuthClientAuthenticator, "retrieve_and_verify_token", return_value=decoded_jwt):
        user, token = OAuth2Authentication().authenticate(request)

    assert user.is_anonymous is True
    assert token == decoded_jwt


@pytest.mark.parametrize(
    "raised_exception, exception_message",
    [
        [BadSignatureError("Very bad signature"), "bad_signature"],
        [TokenExpiredError("Very expired token"), "token_expired"],
    ],
)
def test_authentication_with_local_jwk_authenticate_exception_raised(
    raised_exception: Exception, exception_message: str, request_factory: APIRequestFactory
):
    request = request_factory.get("/", HTTP_AUTHORIZATION="Bearer <token>")

    with (
        patch.object(OAuthClientAuthenticator, "retrieve_and_verify_token", side_effect=raised_exception),
        pytest.raises(AuthenticationFailed) as exc_info,
    ):
        OAuth2Authentication().authenticate(request)

    assert str(exc_info.value) == exception_message


@pytest.mark.parametrize(
    "auth_header",
    [
        None,  # No Authorization header
        "InvalidHeaderWithoutSpace",  # Header causes ValueError when splitting
        "Basic <token>",  # Header not starting with `Bearer`
    ],
)
def test_authentication_with_local_jwk_authenticate_no_access_token_in_request(
    auth_header: Optional[str],
    request_factory: APIRequestFactory,
):
    headers = {}
    if auth_header:
        headers["HTTP_AUTHORIZATION"] = auth_header

    request = request_factory.get("/", **headers)
    token = OAuthClientAuthenticator.retrieve_access_token_from_request(request)

    assert token is None


def test_authentication_with_local_jwk_authenticate_token_not_verified(request_factory: APIRequestFactory):
    request = request_factory.get("/", HTTP_AUTHORIZATION="Bearer <token>")

    with (
        patch.object(
            OAuthClientAuthenticator,
            "retrieve_and_verify_token",
            return_value=None,
        ),
        pytest.raises(AuthenticationFailed) as exc_info,
    ):
        OAuth2Authentication().authenticate(request)

    assert str(exc_info.value) == "Token not supplied"


def test_token_validation_success(
    request_factory: APIRequestFactory,
    decoded_jwt: JWTClaims,
):
    request = request_factory.get("/")
    request.auth = decoded_jwt

    assert IsOAuthTokenValid().has_permission(request, view=MagicMock()) is True


def test_token_validation_failure(
    request_factory: APIRequestFactory,
    decoded_jwt: JWTClaims,
):
    claims = decoded_jwt
    claims.validate = MagicMock(side_effect=ValueError("Simulated validation error"))

    request = request_factory.get("/")
    request.auth = claims

    with pytest.raises(ValueError) as exc_info:
        IsOAuthTokenValid().has_permission(request, view=MagicMock())

    assert str(exc_info.value) == "Simulated validation error"


def test_token_validation_failure_due_to_invalid_auth_object(request_factory: APIRequestFactory):
    request = request_factory.get("/")
    request.auth = {}  # Passing a regular-empty dictionary.

    with pytest.raises(AttributeError) as exc_info:
        IsOAuthTokenValid().has_permission(request, view=MagicMock())

    assert str(exc_info.value) == "'dict' object has no attribute 'validate'"


def test_token_has_permissions_success(request_factory: APIRequestFactory):
    request = request_factory.get("/")
    request.auth = {"scope": "read write execute"}
    view = TestView(required_scopes=["read", "write", "execute"])

    assert OAuthTokenHasScopes().has_permission(request, view) is True


def test_token_has_permissions_success_specific_scopes_defined_for_endpoint(request_factory: APIRequestFactory):
    request = request_factory.get("/")
    request.auth = {"scope": "read write execute"}
    view = TestView(required_scopes=["read"])

    assert OAuthTokenHasScopes().has_permission(request, view) is True


def test_token_has_permissions_no_token(request_factory: APIRequestFactory):
    request = request_factory.get("/")
    request.auth = None
    view = TestView(required_scopes=["read"])

    assert OAuthTokenHasScopes().has_permission(request, view) is False


def test_token_has_permissions_view_has_no_scopes(
    request_factory: APIRequestFactory,
    decoded_jwt: JWTClaims,
):
    """Even though this test returns True, Views without defined scopes will throw `ImproperlyConfigured` exception."""
    request = request_factory.get("/")
    request.auth = decoded_jwt
    view = TestView(required_scopes=[])

    assert OAuthTokenHasScopes().has_permission(request, view) is True


@pytest.mark.parametrize(
    "required_scopes, token_scopes, expected_result",
    [
        ([], "read write", True),  # No required scopes
        (["admin"], "read write", False),  # Required scope not in token scopes
        (["read"], "read write", True),  # Required scope in token scopes
    ],
)
def test_token_has_permissions_invalid_scopes(
    required_scopes: List[str],
    token_scopes: str,
    expected_result: bool,
    request_factory: APIRequestFactory,
    decoded_jwt: JWTClaims,
):
    decoded_jwt["scope"] = token_scopes

    request = request_factory.get("/")
    request.auth = decoded_jwt
    view = TestView(required_scopes=required_scopes)

    assert OAuthTokenHasScopes().has_permission(request, view) is expected_result


def test_token_has_permissions_no_view_scopes_defined(
    request_factory: APIRequestFactory,
    decoded_jwt: JWTClaims,
):
    request = request_factory.get("/")
    request.auth = decoded_jwt

    view = Mock(spec=[])

    with pytest.raises(ImproperlyConfigured) as exc_info:
        OAuthTokenHasScopes().has_permission(request, view)

    assert str(exc_info.value) == "TokenHasScope requires the view to define the required_scopes attribute"


@pytest.mark.django_db
def test_token_has_valid_organization_claim_has_permission_success(
    request_factory: APIRequestFactory,
    decoded_jwt: JWTClaims,
):
    organization = OrganizationFactory(kind="org", name="vssa")
    AgentEnvironmentFactory(agent__organization=organization, oauth_client_id=decoded_jwt["sub"])

    request = request_factory.get("/")
    request.auth = decoded_jwt

    view = TestView(kwargs={"form": "org", "org": "vssa"})

    result = OAuthTokenHasValidOrganizationClaim().has_permission(request, view)
    assert result is True
    assert request.organization == organization


def test_download_jwk_success(mock_endpoints, download_only_oauth_settings):
    keys = OAuthClientAuthenticator.get_jwk_verification_keys(check_cache=False)
    assert len(keys) == 1
    assert keys[0].kty == "RSA"


def test_download_failure_uses_backup(requests_mock, download_only_oauth_settings, rsa_keypair):
    _, public = rsa_keypair
    cache.set(
        OAuthClientAuthenticator.BACKUP_JWK_VERIFICATION_KEYS_CACHE_KEY,
        [JsonWebKey.import_key(public)],
    )
    requests_mock.get(
        download_only_oauth_settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_URL,
        status_code=500,
    )
    keys = OAuthClientAuthenticator.get_jwk_verification_keys(check_cache=True)
    assert len(keys) == 1


def test_download_failure_no_backup(requests_mock, download_only_oauth_settings):
    cache.delete(OAuthClientAuthenticator.BACKUP_JWK_VERIFICATION_KEYS_CACHE_KEY)
    requests_mock.get(
        download_only_oauth_settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_URL,
        status_code=500,
    )
    keys = OAuthClientAuthenticator.get_jwk_verification_keys(check_cache=True)
    assert keys == []


def test_cache_hit(requests_mock, download_only_oauth_settings, rsa_keypair):
    _, public = rsa_keypair
    cached = [JsonWebKey.import_key(public)]
    cache.set(OAuthClientAuthenticator.JWK_VERIFICATION_KEYS_CACHE_KEY, cached)
    keys = OAuthClientAuthenticator.get_jwk_verification_keys(check_cache=True)
    assert keys[0].kid == cached[0].kid
    assert requests_mock.call_count == 0


def test_missing_download_url(settings):
    settings.OAUTH_SERVER_PUBLIC_JWK_JSON = None
    settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_PATH = "/tmp/jwks"
    settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_URL = None
    keys = OAuthClientAuthenticator.get_jwk_verification_keys(check_cache=True)
    assert keys == []

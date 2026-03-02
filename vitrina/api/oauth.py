import base64
import json
import logging
import math
import os
from typing import Iterable, Any, Literal

import requests
from authlib.jose import jwt, JsonWebKey, JWTClaims, Key
from authlib.jose.errors import BadSignatureError, DecodeError, JoseError
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.views import View
from oauthlib.oauth2 import OAuth2Error
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from vitrina.orgs.models import Organization
from vitrina.uapi.models import AgentEnv

Secret = str
ClientId = str
AccessToken = str

logger = logging.getLogger(__name__)

# TODO migrate to Gravitee once its ready.


class OAuthClientManagement:
    @staticmethod
    def _to_urlsafe_base64(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode().rstrip("=")

    @staticmethod
    def generate_secret(size: int = 32):
        value = math.floor(math.log(64, 256) * size) + 1
        return OAuthClientManagement._to_urlsafe_base64(os.urandom(value))[:size]

    @staticmethod
    def create_oauth_client(
        client_name: str | None = None, scopes: list[str] | None = None, secret: Secret = None
    ) -> tuple[ClientId, Secret]:
        secret = secret or OAuthClientManagement.generate_secret()
        response = requests.post(
            settings.OAUTH_SERVER_CLIENTS_URL,
            headers={"Authorization": f"Bearer {OAuthClientManagement.get_management_access_token()}"},
            json={"client_name": client_name, "scopes": scopes or [], "secret": secret},
        )
        response.raise_for_status()
        client_id = response.json()["client_id"]
        return client_id, secret

    @staticmethod
    def update_oauth_client(client_id: ClientId, new_scopes: list[str] | None = None, new_name: str = None) -> None:
        update_data: dict = {}
        if new_scopes is not None:
            update_data["scopes"] = new_scopes
        if new_name is not None:
            update_data["name"] = new_name

        if not update_data:
            return
        response = requests.patch(
            f"{settings.OAUTH_SERVER_CLIENTS_URL}/{client_id}",
            headers={"Authorization": f"Bearer {OAuthClientManagement.get_management_access_token()}"},
            json=update_data,
        )
        response.raise_for_status()

    @staticmethod
    def get_management_access_token() -> AccessToken:
        response = requests.post(
            settings.OAUTH_SERVER_TOKEN_URL,
            headers={
                "Authorization": f"Basic {settings.OAUTH_CLIENT_SECRET_BASE64}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": settings.OAUTH_CLIENTS_MANAGEMENT_SCOPE,
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]


class OAuthClientAuthenticator:
    JWK_KEY = dict[str, str]
    JWK_VERIFICATION_KEYS_CACHE_KEY = ".well-known/jwks.json"
    BACKUP_JWK_VERIFICATION_KEYS_CACHE_KEY = "backup/.well-known/jwks.json"

    @staticmethod
    def retrieve_access_token_from_request(request: Request) -> str | None:
        auth_header = request.META.get("HTTP_AUTHORIZATION")

        if not auth_header:
            return None

        try:
            token_type, token_value = auth_header.split(" ", 1)
        except ValueError:
            return None

        if token_type.lower() != "bearer":
            return None

        return token_value

    @staticmethod
    def download_jwk_verification_keys() -> JWK_KEY | dict[str, JWK_KEY]:
        if not settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_PATH:
            logger.error(
                "Cannot download public JWK verification keys, OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_PATH is not set."
            )
            return {}
        try:
            response = requests.get(settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_URL)
            if not response.ok:
                logger.error(
                    f"Failed to download public JWK verification keys from {settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_URL=} - {response.status_code=} {response.text=}"
                )
                return {}
            return response.json()
        except Exception as e:
            logger.error(
                f"Failed to download public JWK verification keys from {settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_URL=} - {e}"
            )
            return {}

    @classmethod
    def get_jwk_verification_keys(cls, check_cache: bool = True) -> list[Key]:
        if settings.OAUTH_SERVER_PUBLIC_JWK_JSON:
            verification_keys = settings.OAUTH_SERVER_PUBLIC_JWK_JSON.get("keys") or [
                settings.OAUTH_SERVER_PUBLIC_JWK_JSON
            ]
            return [JsonWebKey.import_key(verification_key) for verification_key in verification_keys]
        elif settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_PATH:
            if check_cache and (cached_verification_keys := cache.get(cls.JWK_VERIFICATION_KEYS_CACHE_KEY)):
                return cached_verification_keys
            verification_keys = cls.download_jwk_verification_keys()
            if verification_keys:
                verification_keys = verification_keys.get("keys") or [verification_keys]
                verification_keys = [JsonWebKey.import_key(verification_key) for verification_key in verification_keys]
                cache.set(
                    cls.JWK_VERIFICATION_KEYS_CACHE_KEY,
                    verification_keys,
                    timeout=settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_CACHE_TIMEOUT,
                )
                cache.set(cls.BACKUP_JWK_VERIFICATION_KEYS_CACHE_KEY, verification_keys)
                return verification_keys
            else:
                logger.warning("Could not retrieve public JWK verification keys, using backup cached ones.")
                return cache.get(cls.BACKUP_JWK_VERIFICATION_KEYS_CACHE_KEY) or []
        raise ImproperlyConfigured(
            "No public JWK verification keys configured (OAUTH_SERVER_PUBLIC_JWK_JSON/OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_PATH)."
        )

    @staticmethod
    def decode_unverified_header(token: str | bytes) -> dict[str, Any]:
        try:
            if isinstance(token, bytes):
                token = token.decode("utf-8")

            header_b64 = token.split(".")[0]

            # Add padding if missing
            header_b64 += "=" * (-len(header_b64) % 4)
            header_bytes = base64.urlsafe_b64decode(header_b64)

            return json.loads(header_bytes)
        except (UnicodeDecodeError, DecodeError, json.JSONDecodeError, ValueError, IndexError) as e:
            raise AuthenticationFailed("Invalid token header.") from e

    @staticmethod
    def decode_kty_from_alg(alg: str) -> Literal["RSA", "EC", None]:
        """Get Key Type from Token Algorithm."""
        if alg.startswith("RS"):
            return "RSA"
        if alg.startswith("ES"):
            return "EC"
        return None

    @classmethod
    def verify_token(cls, token_string: str, check_cache: bool = True) -> JWTClaims:
        verification_keys = cls.get_jwk_verification_keys(check_cache=check_cache)
        token_header = cls.decode_unverified_header(token_string)
        if kid := token_header.get("kid"):
            for key in verification_keys:
                if key.kid and str(key.kid) == str(kid):
                    decoded_token = jwt.decode(token_string, key)
                    decoded_token.validate()
                    return decoded_token

        token_kty = cls.decode_kty_from_alg(token_header["alg"])
        for key in verification_keys:
            is_not_encryption_key = key.tokens.get("use") != "enc"
            key_algorithm = key.tokens.get("alg")
            is_same_algorithm = key_algorithm and token_header["alg"] == key_algorithm
            is_same_algorithm_type = key.kty and key.kty == token_kty
            if is_not_encryption_key and (is_same_algorithm or is_same_algorithm_type):
                try:
                    decoded_token = jwt.decode(token_string, key)
                    decoded_token.validate()
                    return decoded_token
                except BadSignatureError:
                    continue
        if check_cache:
            return cls.verify_token(token_string, check_cache=False)
        raise AuthenticationFailed(f"No public key found for token {token_header=}")

    @classmethod
    def retrieve_and_verify_token(cls, request: Request) -> JWTClaims | None:
        token_string = OAuthClientAuthenticator.retrieve_access_token_from_request(request)
        if not token_string:
            return None
        return cls.verify_token(token_string)

    @staticmethod
    def resolve_organization_from_token(decoded_token: JWTClaims) -> Organization | None:
        if not (client_id := OAuthClientAuthenticator.resolve_client_id_from_token(decoded_token)):
            return None
        agent_env = (
            AgentEnv.not_archived.filter(oauth_client_id=client_id).select_related("agent__organization").first()
        )
        return agent_env.agent.organization if agent_env else None

    @staticmethod
    def resolve_client_id_from_token(decoded_token: JWTClaims) -> str:
        return decoded_token["sub"]


class OAuth2Authentication(BaseAuthentication):
    def authenticate(self, request: Request) -> tuple[AnonymousUser, JWTClaims]:
        try:
            verified_token = OAuthClientAuthenticator.retrieve_and_verify_token(request)
        except (JoseError, OAuth2Error) as e:
            raise AuthenticationFailed(e.error)
        if not verified_token:
            raise AuthenticationFailed("Token not supplied")
        user = AnonymousUser()  # Workaround for django-cms middleware, as we authenticate on behalf of an organization.
        return user, verified_token


class IsOAuthTokenValid(BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        request.auth.validate()
        return isinstance(request.auth, JWTClaims)


class OAuthTokenHasScopes(BasePermission):
    def has_permission(self, request: Request, view: GenericViewSet) -> bool:
        if not (token := request.auth):
            return False

        if not (required_scopes := self.get_scopes(request, view)):
            return True

        if not (scopes := token.get("scope", "").split(" ")):
            return False

        missing_scopes = set(required_scopes) - set(scopes)
        return not bool(missing_scopes)

    @staticmethod
    def get_scopes(request: Request, view: GenericViewSet) -> Iterable[str]:
        try:
            scopes = getattr(view, "required_scopes")
        except AttributeError:
            raise ImproperlyConfigured("TokenHasScope requires the view to define the required_scopes attribute")

        if isinstance(scopes, dict):
            return scopes.get(view.action, [])

        return scopes


class OAuthTokenHasValidOrganizationClaim(BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        if not (organization := OAuthClientAuthenticator.resolve_organization_from_token(request.auth)):
            return False

        setattr(request, "organization", organization)
        return True

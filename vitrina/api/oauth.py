import base64
import math
import os
from typing import Iterable, Optional

import requests
from authlib.jose import jwt, JsonWebKey, JWTClaims
from authlib.jose.errors import BadSignatureError
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from django.views import View
from oauthlib.oauth2 import TokenExpiredError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from vitrina.orgs.models import Organization
from vitrina.uapi.models import Agent

Secret = str
ClientId = str
AccessToken = str


def get_oauth_client_management() -> "OAuthClientManagement":
    return import_string(settings.OAUTH_CLIENT_MANAGEMENT_CLASS)


class OAuthClientManagement:
    @staticmethod
    def _to_urlsafe_base64(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode().rstrip("=")

    @classmethod
    def generate_secret(cls, size: int = 32):
        value = math.floor(math.log(64, 256) * size) + 1
        return cls._to_urlsafe_base64(os.urandom(value))[:size]

    @classmethod
    def create_oauth_client(
        cls, client_name: Optional[str] = None, scopes: list[str] = None, secret: Secret = None
    ) -> tuple[ClientId, Secret]:
        secret = secret or cls.generate_secret()
        cls.declare_scopes(scopes)
        response = requests.post(
            settings.OAUTH_SERVER_CLIENTS_URL,
            headers={"Authorization": f"Bearer {cls.get_management_access_token()}"},
            json={"client_name": client_name, "scopes": scopes or [], "secret": secret},
        )
        response.raise_for_status()
        client_id = response.json()["client_id"]
        return client_id, secret

    @classmethod
    def update_oauth_client(cls, client_id: ClientId, new_scopes: list[str] = None, new_name: str = None) -> None:
        update_data: dict = {}
        if new_scopes is not None:
            update_data["scopes"] = new_scopes
        if new_name is not None:
            update_data["name"] = new_name

        if not update_data:
            return
        cls.declare_scopes(new_scopes)
        response = requests.patch(
            f"{settings.OAUTH_SERVER_CLIENTS_URL}/{client_id}",
            headers={"Authorization": f"Bearer {cls.get_management_access_token()}"},
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

    @classmethod
    def declare_scopes(cls, scopes: list[str]):
        """Override in case you need to declare new scopes before assigning them."""
        pass


class GraviteeOAuthClientManagement(OAuthClientManagement):
    @classmethod
    def declare_scopes(cls, scopes: list[str]) -> None:
        response = requests.post(
            settings.OAUTH_SERVER_CLIENTS_URL + settings.OAUTH_SERVER_SCOPES_PATH,
            headers={"Authorization": f"Bearer {cls.get_management_access_token()}"},
            json={"scopes": scopes},
        )
        response.raise_for_status()


class OAuthClientAuthenticator:
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

    @classmethod
    def retrieve_and_verify_token(cls, request: Request) -> JWTClaims | None:
        access_token = cls.retrieve_access_token_from_request(request)
        if not access_token:
            return None
        key_object = JsonWebKey.import_key(settings.OAUTH_SERVER_PUBLIC_JWK_JSON)
        decoded_token = jwt.decode(access_token, key_object)
        decoded_token.validate()
        return decoded_token

    @classmethod
    def resolve_organization_from_token(cls, decoded_token: JWTClaims) -> Organization | None:
        if not (client_id := cls.resolve_client_id_from_token(decoded_token)):
            return None
        agent = Agent.objects.filter(oauth_client_id=client_id).select_related("organization").first()
        return agent.organization if agent else None

    @staticmethod
    def resolve_client_id_from_token(decoded_token: JWTClaims) -> str:
        return decoded_token["sub"]


class OAuth2AuthenticationWithLocalJWK(BaseAuthentication):
    def authenticate(self, request: Request) -> tuple[AnonymousUser, JWTClaims]:
        try:
            verified_token = OAuthClientAuthenticator.retrieve_and_verify_token(request)
        except (BadSignatureError, TokenExpiredError) as e:
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

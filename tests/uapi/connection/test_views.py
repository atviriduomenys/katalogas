from http import HTTPStatus

from authlib.jose import RSAKey
from django.conf import settings
from django_webtest import DjangoTestApp
from rest_framework import status

from tests.uapi.conftest import _generate_test_token
from vitrina.orgs.models import Organization
from vitrina.uapi import HTTPMethods, PossibleResults
from vitrina.uapi.factories import AgentEnvFactory
from vitrina.uapi.models import RequestHistory


class TestConnectionCheck:
    def test_success(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_connection_check: str,
        test_jwk: RSAKey,
    ):
        spinta_version = "1.2.3"
        agent_env = AgentEnvFactory(
            agent__organization=organization,
            oauth_client_id="test-client-id",
            is_archived=False,
            is_enabled=True,
        )

        token = _generate_test_token(
            test_jwk,
            organization=organization,
            scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES,
            agent_env=agent_env,
        )

        payload = {"spinta_version": spinta_version}

        response = app.post_json(
            url_connection_check,
            payload,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        history = RequestHistory.objects.get()
        assert history.agent_environment == agent_env
        assert history.method == HTTPMethods.POST
        assert history.http_result == HTTPStatus.NO_CONTENT
        assert history.result == PossibleResults.STATUS_ALIVE
        assert spinta_version in history.details
        assert history.error is None

    def test_agent_archived_forbidden(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_connection_check: str,
        test_jwk: RSAKey,
    ):
        agent_env = AgentEnvFactory(
            agent__organization=organization,
            oauth_client_id="test-client-id",
            is_archived=True,
            is_enabled=True,
        )

        token = _generate_test_token(
            test_jwk,
            organization=organization,
            scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES,
            agent_env=agent_env,
        )

        response = app.post_json(
            url_connection_check,
            {"spinta_version": "1.13.0"},
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

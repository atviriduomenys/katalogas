from typing import Iterable
from unittest.mock import ANY

import pytest
from authlib.jose import RSAKey
from django.conf import settings
from django_webtest import DjangoTestApp
from rest_framework import status

from tests.uapi.conftest import _generate_test_token
from vitrina.orgs.models import Organization
from vitrina.uapi.factories import AgentEnvFactory
from vitrina.uapi.models import AgentEnv
from vitrina.datasets.models import Dataset


class TestList:
    def test_success(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_agent: str,
        test_jwk: RSAKey,
        agent_env: AgentEnv,
        dataset: Dataset,
    ):
        token = _generate_test_token(
            test_jwk, agent_env=agent_env, organization=organization, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES
        )

        response = app.get(
            url_agent,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "@context": "",
                    "_created": ANY,
                    "_updated": ANY,
                    "_txn": "",
                    "_revision": "",
                    "_id": str(agent_env.pk),
                    "_type": "datasets/gov/vssa/ror/dcat/Agent",
                    "synchronized_at": agent_env.synchronized_at,
                    "is_last_sync_successful": agent_env.is_last_sync_successful,
                    "title": agent_env.agent.title,
                    "codename": agent_env.agent.codename,
                    "object_type": agent_env.agent.object_type,
                    "is_open_data_published": agent_env.is_open_data_published,
                    "open_data_publish_url": agent_env.open_data_publish_url,
                    "is_enabled": agent_env.is_enabled,
                    "services": list(agent_env.agent.services.values_list("pk", flat=True)),
                    "organization": agent_env.agent.organization_id,
                    "oauth_client_id": agent_env.oauth_client_id,
                    "environment": agent_env.environment,
                    "auth_server_url": agent_env.auth_server_url,
                    "api_gate_server_url": agent_env.api_gate_server_url,
                    "agent_address": agent_env.agent_address,
                }
            ]
        }

    def test_success_specific_scope_given(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_agent: str,
        test_jwk: RSAKey,
        agent_env: AgentEnv,
    ):
        token = _generate_test_token(
            test_jwk,
            organization=organization,
            scopes=["uapi:/datasets/gov/vssa/dcat/Agent/:getall"],
            agent_env=agent_env,
        )

        response = app.get(
            url_agent,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json["_data"]) == 1

    def test_agent_is_archived(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_agent: str,
        test_jwk: RSAKey,
    ):
        agent_env = AgentEnvFactory(
            agent__organization=organization,
            oauth_client_id="test-client-id",
            is_archived=True,
            is_enabled=True,
        )
        token = _generate_test_token(
            test_jwk, organization=organization, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES, agent_env=agent_env
        )

        response = app.get(
            url_agent,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("invalid_scopes", [["invalid_scope"], [], [""]])
    def test_necessary_scope_missing_from_token(
        self,
        invalid_scopes: Iterable[str],
        app: DjangoTestApp,
        organization: Organization,
        url_agent: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        agent_env = AgentEnvFactory(
            agent__organization=organization,
            oauth_client_id="test-client-id",
            is_archived=False,
            is_enabled=True,
        )
        token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes, agent_env=agent_env)

        response = app.get(url_agent, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }

    def test_organization_id_missing_from_token(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_agent: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(
            test_jwk,
            scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES,
        )

        response = app.get(url_agent, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }

    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_agent: str,
        test_jwk: RSAKey,
    ):
        agent_env = AgentEnvFactory(
            agent__organization=organization,
            oauth_client_id="test-client-id",
            is_archived=False,
            is_enabled=False,
        )
        token = _generate_test_token(
            test_jwk, organization=organization, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES, agent_env=agent_env
        )

        response = app.get(
            url_agent,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "The agent is disabled. Enable the agent in the Data catalog to access this API.",
            "additionalProperties": None,
        }

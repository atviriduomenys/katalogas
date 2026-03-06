import pytest

from vitrina.uapi import Environment, AgentType
from vitrina.uapi.forms import AgentForm, AgentEnvironmentForm
from vitrina.uapi.models import Agent


class TestAgentForm:
    def test_success(self, organization):
        form_data = {
            "title": "Agent",
            "object_type": AgentType.SPINTA,
        }
        form = AgentForm(data=form_data, organization=organization)
        assert form.is_valid()

    @pytest.mark.django_db
    def test_duplicate_codename(self, organization):
        Agent.objects.create(title="Repeating", organization=organization)

        form = AgentForm(
            data={
                "title": "Repeating",
                "object_type": AgentType.SPINTA,
            },
            organization=organization,
        )
        assert not form.is_valid()
        assert "title" in form.errors
        assert form.errors["title"] == [
            "Agentas su tokiu pavadinimu jau registruotas organizacijoje, pasirinkite kitą pavadinimą."
        ]

    @pytest.mark.django_db
    def test_duplicate_codename_first_agent_is_archived(self, organization):
        """Only forbid creating an Agent with a repeating name if the initial Agent is not archived."""
        Agent.objects.create(title="Repeating", organization=organization, is_archived=True)

        form = AgentForm(
            data={
                "title": "Repeating",
                "object_type": AgentType.SPINTA,
            },
            organization=organization,
        )
        assert form.is_valid()

    @pytest.mark.django_db
    def test_agent_with_organization_service(self, organization):
        form = AgentForm(
            data={
                "title": "Agent with service",
                "object_type": AgentType.SPINTA,
            },
            organization=organization,
        )
        assert form.is_valid()


class TestAgentEnvironmentForm:
    def test_success(self, organization):
        form_data = {
            "environment": Environment.DEVELOPMENT,
            "agent_address": "http://agent-address.test",
            "auth_server_url": "http://auth-server.test",
            "api_gate_server_url": "http://api-gate-server.test",
            "is_open_data_published": True,
            "open_data_publish_url": "http://open-data.test",
            "is_enabled": True,
        }
        form = AgentEnvironmentForm(data=form_data, organization=organization)
        assert form.is_valid()

    def test_failure_open_data_is_published_but_no_url_is_provided(self, organization):
        form_data = {
            "environment": Environment.DEVELOPMENT,
            "agent_address": "http://agent-address.test",
            "auth_server_url": "http://auth-server.test",
            "api_gate_server_url": "http://api-gate-server.test",
            "is_open_data_published": True,
            "open_data_publish_url": "",
            "is_enabled": True,
        }

        form = AgentEnvironmentForm(data=form_data, organization=organization)

        assert not form.is_valid()
        assert form.errors == {
            "open_data_publish_url": [
                'Šis laukas yra privalomas, jei nustatytas požymis "Atviri duomenys publikuojami Saugykloje".'
            ]
        }

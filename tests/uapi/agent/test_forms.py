import pytest

from vitrina.datasets.factories import DatasetFactory
from vitrina.uapi import Environment, AgentType
from vitrina.uapi.forms import AgentForm
from vitrina.uapi.models import Agent


class TestAgentForm:
    def test_success(self, organization):
        dataset = DatasetFactory(service=True, organization=organization)
        form_data = {
            "title": "Agent",
            "is_enabled": True,
            "environment": Environment.DEVELOPMENT,
            "is_open_data_published": False,
            "object_type": AgentType.SPINTA,
            "open_data_publish_url": "",
            "service": dataset.pk,
            "agent_address": "http://agent-address.test",
        }
        form = AgentForm(data=form_data, organization=organization)
        assert form.is_valid()

    def test_success_open_data_publish_url_is_provided(self, organization):
        dataset = DatasetFactory(service=True, organization=organization)
        form_data = {
            "title": "Agent",
            "is_enabled": True,
            "environment": Environment.DEVELOPMENT,
            "is_open_data_published": True,
            "object_type": AgentType.SPINTA,
            "open_data_publish_url": "https://example.com",
            "service": dataset.pk,
            "agent_address": "http://agent-address.test",
        }
        form = AgentForm(data=form_data, organization=organization)
        assert form.is_valid()

    def test_failure_open_data_is_published_but_no_url_is_provided(self, organization):
        dataset = DatasetFactory(service=True, organization=organization)

        form_data = {
            "title": "Agent",
            "is_enabled": True,
            "environment": Environment.DEVELOPMENT,
            "is_open_data_published": True,
            "object_type": AgentType.SPINTA,
            "open_data_publish_url": "",
            "service": dataset.pk,
            "agent_address": "http://agent-address.test",
        }

        form = AgentForm(data=form_data, organization=organization)

        assert not form.is_valid()
        assert form.errors == {
            "open_data_publish_url": [
                'Šis laukas yra privalomas, jei nustatytas požymis "Atviri duomenys publikuojami Saugykloje".'
            ]
        }

    @pytest.mark.django_db
    def test_duplicate_codename(self, organization):
        dataset = DatasetFactory(service=True, organization=organization)
        Agent.objects.create(title="Repeating", organization=organization, service=dataset)

        form = AgentForm(
            data={
                "title": "Repeating",
                "is_enabled": True,
                "environment": Environment.DEVELOPMENT,
                "is_open_data_published": False,
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
        dataset = DatasetFactory(service=True, organization=organization)
        Agent.objects.create(title="Repeating", organization=organization, service=dataset, is_archived=True)

        form = AgentForm(
            data={
                "title": "Repeating",
                "is_enabled": True,
                "environment": Environment.DEVELOPMENT,
                "is_open_data_published": False,
                "object_type": AgentType.SPINTA,
                "service": dataset.pk,
                "agent_address": "http://agent-address.test",
            },
            organization=organization,
        )
        assert form.is_valid()

    @pytest.mark.django_db
    def test_agent_with_organization_service(self, organization):
        dataset = DatasetFactory(service=True, organization=organization)

        form = AgentForm(
            data={
                "title": "Agent with service",
                "is_enabled": True,
                "environment": Environment.DEVELOPMENT,
                "is_open_data_published": False,
                "object_type": AgentType.SPINTA,
                "service": dataset.pk,
                "agent_address": "http://agent-address.test",
            },
            organization=organization,
        )
        assert form.is_valid()

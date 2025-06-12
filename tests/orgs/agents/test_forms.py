import pytest

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs import AgentType
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.forms import AgentForm
from vitrina.orgs.models import Agent


def test_success_agent_create_form():
    form_data = {
        "title": "Agent",
        "is_enabled": True,
        "is_open_data_published": False,
        "object_type": AgentType.SPINTA,
        "open_data_publish_url": ""
    }
    form = AgentForm(data=form_data)
    assert form.is_valid()

def test_success_agent_create_form_open_data_publish_url_is_provided():
    form_data = {
        "title": "Agent",
        "is_enabled": True,
        "is_open_data_published": True,
        "object_type": AgentType.SPINTA,
        "open_data_publish_url": "https://example.com"
    }
    form = AgentForm(data=form_data)
    assert form.is_valid()

def test_failure_agent_create_form_open_data_is_published_but_no_url_is_provided():
    form_data = {
        "title": "Agent",
        "is_enabled": True,
        "is_open_data_published": True,
        "object_type": AgentType.SPINTA,
        "open_data_publish_url": ""
    }

    form = AgentForm(data=form_data)

    assert not form.is_valid()
    assert form.errors == {
        "open_data_publish_url": [
            "Šis laukas yra privalomas, jei nustatytas požymis \"Atviri duomenys publikuojami Saugykloje\"."
        ]
    }


@pytest.mark.django_db
def test_agent_form_duplicate_codename():
    organization = OrganizationFactory()
    dataset = DatasetFactory(service=True, organization=organization)
    Agent.objects.create(title="Repeating", organization=organization, service=dataset)

    form = AgentForm(
        data={
            "title": "Repeating",
            "is_enabled": True,
            "is_open_data_published": False,
            "object_type": AgentType.SPINTA,
        },
        organization=organization
    )
    assert not form.is_valid()
    assert "title" in form.errors
    assert form.errors["title"] == [
        "Agentas su tokiu pavadinimu jau registruotas organizacijoje, pasirinkite kitą pavadinimą."
    ]


@pytest.mark.django_db
def test_agent_form_duplicate_codename_first_agent_is_archived():
    """Only forbid creating an Agent with a repeating name if the initial Agent is not archived."""
    organization = OrganizationFactory()
    dataset = DatasetFactory(service=True, organization=organization)
    Agent.objects.create(title="Repeating", organization=organization, service=dataset, is_archived=True)

    form = AgentForm(
        data={
            "title": "Repeating",
            "is_enabled": True,
            "is_open_data_published": False,
            "object_type": AgentType.SPINTA,
        },
        organization=organization
    )
    assert form.is_valid()


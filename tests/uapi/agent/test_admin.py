from http import HTTPStatus

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.uapi.factories import AgentEnvironmentFactory
from vitrina.uapi.models import Agent, AgentEnvironment
from vitrina.users.models import User


pytestmark = pytest.mark.django_db


@pytest.fixture
def superuser() -> User:
    return User.objects.create_superuser(email="admin@gmail.com", password="test123")


def test_superuser_cannot_delete_agent_environment(app: DjangoTestApp, superuser: User):
    agent_environment = AgentEnvironmentFactory()
    app.set_user(superuser)

    response = app.get(
        reverse("admin:vitrina_uapi_agentenvironment_delete", args=[agent_environment.pk]), expect_errors=True
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert AgentEnvironment.objects.filter(pk=agent_environment.pk).exists()


def test_superuser_cannot_delete_agent(app: DjangoTestApp, superuser: User):
    agent_environment = AgentEnvironmentFactory()
    app.set_user(superuser)

    response = app.get(
        reverse("admin:vitrina_uapi_agent_delete", args=[agent_environment.agent.pk]), expect_errors=True
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert Agent.objects.filter(pk=agent_environment.agent.pk).exists()


def test_delete_action_not_offered_for_agent_environments(app: DjangoTestApp, superuser: User):
    AgentEnvironmentFactory()
    app.set_user(superuser)

    response = app.get(reverse("admin:vitrina_uapi_agentenvironment_changelist"))

    # With no other actions registered, admin renders no action form at all.
    action_form = response.context["action_form"]
    actions = [value for value, _ in action_form.fields["action"].choices] if action_form else []
    assert "delete_selected" not in actions


def test_organization_with_agents_cannot_be_deleted_in_admin(app: DjangoTestApp, superuser: User):
    agent_environment = AgentEnvironmentFactory()
    organization = agent_environment.agent.organization
    app.set_user(superuser)

    response = app.get(reverse("admin:vitrina_orgs_organization_delete", args=[organization.pk]))

    assert response.context["perms_lacking"]

import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Organization
from vitrina.orgs.services import Role
from vitrina.uapi.models import AgentEnv, RequestHistory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


@pytest.fixture
def representative_user(organization: Organization) -> User:
    user = UserFactory(is_staff=True)
    content_type = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        user=user, content_type=content_type, object_id=organization.pk, role=Role.OPEN_DATA_COORDINATOR
    )
    return user


@pytest.fixture
def request_history(agent_env: AgentEnv) -> RequestHistory:
    return RequestHistory.objects.create(
        agent_env=agent_env,
        endpoint="/api/v1/resource",
        method="GET",
        http_result=200,
        result="SUCCESS",
        error="Error\nerror",
    )

import uuid
from datetime import datetime, timedelta

import pytest
from typing import Any, Iterable

import reversion
from authlib.jose import RSAKey, jwt, JsonWebKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.urls import reverse

from vitrina.datasets.factories import DatasetFactory, DCATResourceSubclassFactory
from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization, Representative
from vitrina.projects.factories import ProjectFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.settings import OAUTH_AGENT_DEFAULT_SCOPES
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.smart_contracts.models import Agreement
from vitrina.structure.factories import MetadataFactory
from vitrina.uapi.factories import AgentFactory, AgentEnvFactory
from vitrina.uapi.models import Agent, AgentEnv
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


def _build_reverse_uapi_url(name: str, **kwargs: Any) -> str:
    return reverse(name, kwargs=kwargs)


def _generate_test_token(
    jwk: RSAKey,
    scopes: Iterable[str] = ("datasets:write",),
    organization: Organization | None = None,
    expires_in: int = 900,
    agent_env: AgentEnv | None = None,
    create_agent: bool = True,
    agent_is_enabled: bool = True,
):
    if organization and not agent_env and create_agent:
        agent_env = AgentEnvFactory(
            agent__organization=organization, oauth_client_id=str(uuid.uuid4()), is_enabled=agent_is_enabled
        )
    now = datetime.utcnow()
    claims = {
        "iss": "test-issuer",
        "sub": agent_env.oauth_client_id if agent_env else None,
        "scope": " ".join(scopes),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }

    header = {"alg": "RS256", "kid": "test-key"}

    return jwt.encode(header, claims, key=jwk).decode()


@pytest.fixture(autouse=True)
def override_oauth_jwk(settings, test_jwk):
    settings.OAUTH_SERVER_PUBLIC_JWK_JSON = test_jwk.as_dict(is_private=False)


# TODO: Remove after https://github.com/atviriduomenys/katalogas/issues/1840 is complete.
#   These classes should be created via migrations.
@pytest.fixture
def create_dcat_resource_subclasses() -> None:
    DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
    DCATResourceSubclassFactory(name=DCATResourceSubclass.SERIES)
    DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
    DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
    DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)


@pytest.fixture(scope="session")
def test_jwk() -> RSAKey:
    key = JsonWebKey.generate_key("RSA", crv_or_size=2048, is_private=True)
    return key


@pytest.fixture()
def agent(organization: Organization) -> Agent:
    return AgentFactory(organization=organization)


@pytest.fixture()
def agent_env(agent: Agent) -> AgentEnv:
    return AgentEnvFactory(agent=agent, oauth_client_id=str(uuid.uuid4()))


@pytest.fixture()
def valid_token(test_jwk: RSAKey, organization: Organization, agent_env: AgentEnv) -> str:
    return _generate_test_token(
        test_jwk, agent_env=agent_env, organization=organization, scopes=OAUTH_AGENT_DEFAULT_SCOPES
    )


@pytest.fixture()
def valid_token_disabled_agent(
    test_jwk: RSAKey,
    organization: Organization,
) -> str:
    return _generate_test_token(
        test_jwk,
        organization=organization,
        scopes=OAUTH_AGENT_DEFAULT_SCOPES,
        agent_is_enabled=False,
    )


@pytest.fixture
def organization() -> Organization:
    return OrganizationFactory(kind=Organization.ORG)


@pytest.fixture
def dataset(organization: Organization, agent: Agent) -> Dataset:
    dataset = DatasetFactory(
        organization=organization,
        title="Title of the Dataset",
        description="Description of the Dataset.",
        metadata="test/dataset",
        agent=agent,
    )
    return dataset


@pytest.fixture
def agreement() -> Agreement:
    return AgreementFactory()


@pytest.fixture
def user(organization: Organization) -> User:
    return UserFactory(organization=organization)


@pytest.fixture
def project(user: User, dataset: Dataset) -> Agreement:
    return ProjectFactory(user=user, datasets=[dataset])


@pytest.fixture
def domain() -> str:
    return Site.objects.get_current().domain


@pytest.fixture
def distribution(organization: Organization, dataset: Dataset) -> DatasetDistribution:
    with reversion.create_revision():
        distribution = DatasetDistributionFactory(
            dataset=dataset, title="Title of the Distribution", description="Description of the Distribution."
        )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(DatasetDistribution),
        object_id=distribution.pk,
        name="test/dataset/TestModel/TestDistribution",
    )
    return distribution


@pytest.fixture
def url_dataset() -> str:
    return _build_reverse_uapi_url("uapi-dataset")


@pytest.fixture
def url_distribution() -> str:
    return _build_reverse_uapi_url("uapi-distribution")


@pytest.fixture
def url_dataset_structure(dataset: Dataset) -> str:
    return _build_reverse_uapi_url("uapi-dataset-structure", pk=dataset.id)


@pytest.fixture
def url_version() -> str:
    return _build_reverse_uapi_url("uapi-version")


@pytest.fixture
def url_agent() -> str:
    return _build_reverse_uapi_url("uapi-agent")


@pytest.fixture
def url_connection_check() -> str:
    return _build_reverse_uapi_url("connection-check")


@pytest.fixture
def agreement_url() -> str:
    return _build_reverse_uapi_url("uapi-agreement")


@pytest.fixture
def dsa() -> str:
    return """id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description
,test/dataset,,,,,,,,,,,,,,,,,
,,users,,,,dask/json,,/path,,,,,,,,,,
,,,,,,,,,,,,,,,,,,
,,,,User,,,id,users,,,4,completed,package,open,,,Pavadinimas,
,,,,,id,integer,,id,,,,,,,,,,
,,,,,full_name,string,,name,,,,,,,,,,
,,,,,email_address,string,,email,,,,,,,,,,
,,,,,active,boolean,,isActive,,,,,,,,,,
"""


@pytest.fixture
def coordinator(organization: Organization) -> User:
    return RepresentativeFactory(content_object=organization, role=Representative.RESOURCE_COORDINATOR).user


@pytest.fixture
def manager(organization: Organization) -> User:
    return RepresentativeFactory(content_object=organization, role=Representative.RESOURCE_MANAGER).user


@pytest.fixture
def admin() -> User:
    return UserFactory(is_staff=True)

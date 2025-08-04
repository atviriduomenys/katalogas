from datetime import datetime, timedelta

import pytest
from typing import Any, Iterable

import reversion
from authlib.jose import RSAKey, jwt, JsonWebKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.urls import reverse

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.settings import OAUTH_AGENT_DEFAULT_SCOPES
from vitrina.structure.factories import MetadataFactory


def _build_reverse_uapi_url(name: str, **kwargs: Any) -> str:
    return reverse(name, kwargs=kwargs)


def _generate_test_token(
    jwk: RSAKey,
    client_id: str = "test-client",
    scopes: Iterable[str] = ("datasets:write",),
    organization_id: int = 1,
    expires_in: int = 900
):
    now = datetime.utcnow()
    claims = {
        "iss": "test-issuer",
        "sub": client_id,
        "scope": " ".join(scopes),
        "organization_id": organization_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }

    header = {"alg": "RS256", "kid": "test-key"}

    return jwt.encode(header, claims, key=jwk).decode()


@pytest.fixture(autouse=True)
def override_oauth_jwk(settings, test_jwk):
    settings.OAUTH_SERVER_PUBLIC_JWK_JSON = test_jwk.as_dict(is_private=False)


@pytest.fixture(scope="session")
def test_jwk() -> RSAKey:
    key = JsonWebKey.generate_key("RSA", crv_or_size=2048, is_private=True)
    return key


@pytest.fixture()
def valid_token(
    test_jwk: RSAKey,
    organization: Organization
) -> str:
    return _generate_test_token(test_jwk, organization_id=organization.id, scopes=OAUTH_AGENT_DEFAULT_SCOPES)


@pytest.fixture
def organization() -> Organization:
    return OrganizationFactory(kind=Organization.ORG)


@pytest.fixture
def dataset(organization: Organization) -> Dataset:
    dataset = DatasetFactory(
        organization=organization,
        title="Title of the Dataset",
        description="Description of the Dataset."
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )
    return dataset


@pytest.fixture
def domain() -> str:
    return Site.objects.get_current().domain


@pytest.fixture
def distribution(organization: Organization, dataset: Dataset) -> DatasetDistribution:
    with reversion.create_revision():
        distribution = DatasetDistributionFactory(
            dataset=dataset,
            title="Title of the Distribution",
            description="Description of the Distribution."
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
    return _build_reverse_uapi_url("uapi-dataset-structure", dataset_id=dataset.id)


@pytest.fixture
def dsa() -> str:
    return """
id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description
,example70,,,,,,,,,,,,,,,,,
,,users,,,,dask/json,,/path,,,,,,,,,,
,,,,,,,,,,,,,,,,,,
,,,,User,,,id,users,,,4,completed,package,open,,,Pavadinimas,
,,,,,id,integer,,id,,,,,,,,,,
,,,,,full_name,string,,name,,,,,,,,,,
,,,,,email_address,string,,email,,,,,,,,,,
,,,,,active,boolean,,isActive,,,,,,,,,,
"""

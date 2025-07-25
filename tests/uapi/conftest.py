import pytest
from typing import Any
from unittest.mock import patch

import reversion
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.urls import reverse

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.projects.factories import ProjectFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.smart_contracts.models import Agreement
from vitrina.structure.factories import MetadataFactory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


def build_reverse_uapi_url(name: str, organization: Organization, **kwargs: Any) -> str:
    return reverse(
        name,
        kwargs={
            "form": organization.kind,
            "org": organization.name,
            "catalog": "default",
            "catalog_sub": "v1",
            **kwargs,
        }
    )


@pytest.fixture(autouse=True)
def mock_auth_and_permissions():
    """A Fixture to avoid permission/auth checking for specific API's."""
    with patch("vitrina.api.oauth.OAuth2AuthenticationWithLocalJWK.authenticate") as mock_auth:
        mock_auth.return_value = (AnonymousUser(), {"scope": "read write", "organization_id": 1, "sub": "agentname"})
        with (
            patch("vitrina.api.oauth.IsOAuthTokenValid.has_permission", return_value=True),
            patch("vitrina.api.oauth.OAuthTokenHasScopes.has_permission", return_value=True),
            patch("vitrina.api.oauth.OAuthTokenHasValidOrganizationClaim.has_permission", return_value=True)
        ):
            yield


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
def url_dataset(organization: Organization) -> str:
    return build_reverse_uapi_url("dataset", organization)


@pytest.fixture
def url_distribution(organization: Organization) -> str:
    return build_reverse_uapi_url("distribution", organization)


@pytest.fixture
def url_dataset_structure(organization: Organization, dataset: Dataset) -> str:
    return build_reverse_uapi_url("dataset-structure", organization, dataset_id=dataset.id)


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

from typing import Any

import pytest
import reversion
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.urls import reverse

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.factories import MetadataFactory


def _build_reverse_uapi_url(name: str, organization: Organization, **kwargs: Any) -> str:
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
def url_dataset(organization: Organization) -> str:
    return _build_reverse_uapi_url("dataset", organization)


@pytest.fixture
def url_distribution(organization: Organization) -> str:
    return _build_reverse_uapi_url("distribution", organization)


@pytest.fixture
def url_dataset_structure(organization: Organization, dataset: Dataset) -> str:
    return _build_reverse_uapi_url("dataset-structure", organization, dataset_id=dataset.id)


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

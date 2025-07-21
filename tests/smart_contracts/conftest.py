import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.structure.factories import MetadataFactory


@pytest.fixture
def organization() -> Organization:
    return OrganizationFactory()


@pytest.fixture
def dataset(organization: Organization) -> Dataset:
    dataset = DatasetFactory(organization=organization)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset",
    )

    return dataset


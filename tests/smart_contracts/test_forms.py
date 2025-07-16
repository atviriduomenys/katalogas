import pytest
from django.contrib.contenttypes.models import ContentType
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.smart_contracts.forms import SmartContractForm
from vitrina.structure.factories import MetadataFactory

pytestmark = pytest.mark.django_db


class TestSmartContractForm:
    def test_generates_no_scope_choices_if_datasets_by_organization_not_given(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            dataset=dataset,
            name="test/dataset",
        )
        form = SmartContractForm(instance=organization)

        assert form.fields["scopes"].choices == []

    def test_generates_no_scope_choices_if_organization_has_no_datasets(self):
        organization = OrganizationFactory()
        form = SmartContractForm(
            instance=organization, datasets_by_organization={organization: []}
        )

        assert form.fields["scopes"].choices == []

    def test_generates_scope_choices_from_each_dataset(
        self, app: DjangoTestApp
    ) -> None:
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            dataset=dataset,
            name="test/dataset",
        )

        form = SmartContractForm(
            instance=organization, datasets_by_organization={organization: [dataset]}
        )

        assert set(form.fields["scopes"].choices) == {
            ("test_dataset_getall", "test_dataset_getall"),
            ("test_dataset_search", "test_dataset_search"),
            ("test_dataset_select", "test_dataset_select"),
        }

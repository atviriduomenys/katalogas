import pytest
from django_webtest import DjangoTestApp

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.smart_contracts.forms import SmartContractForm

pytestmark = pytest.mark.django_db


class TestSmartContractForm:
    def test_generates_no_scope_choices_if_datasets_by_organization_not_given(
        self, organization: Organization, dataset: Dataset
    ) -> None:
        form = SmartContractForm(instance=organization)

        assert form.fields["scopes"].choices == []

    def test_generates_no_scope_choices_if_organization_has_no_datasets(
        self, organization: Organization
    ) -> None:
        form = SmartContractForm(
            instance=organization, datasets_by_organization={organization: []}
        )

        assert form.fields["scopes"].choices == []

    def test_generates_scope_choices_from_each_dataset(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        form = SmartContractForm(
            instance=organization, datasets_by_organization={organization: [dataset]}
        )

        assert set(form.fields["scopes"].choices) == {
            ("test_dataset_getall", "test_dataset_getall"),
            ("test_dataset_search", "test_dataset_search"),
            ("test_dataset_select", "test_dataset_select"),
        }

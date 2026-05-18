from unittest.mock import Mock

from vitrina.datasets.factories import DatasetFactory, DatasetAttributionFactory, AttributionFactory
from vitrina.datasets.models import DatasetAttribution, Attribution
from vitrina.datasets.view_helpers import save_dataset_creator
from vitrina.orgs.factories import OrganizationFactory


def make_form(cleaned_data: dict, changed_data: list) -> Mock:
    form = Mock()
    form.cleaned_data = cleaned_data
    form.changed_data = changed_data
    form.fields = {field: Mock(label=field) for field in cleaned_data}
    return form


class TestSaveDatasetCreator:
    def test_skips_field_not_in_changed_data(self):
        dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"creator": OrganizationFactory()},
            changed_data=[],
        )

        save_dataset_creator(Mock(), dataset, form)

        assert DatasetAttribution.objects.filter(dataset=dataset).count() == 0

    def test_creates_attribution_for_selected_organization(self):
        dataset = DatasetFactory()
        attribution = Attribution.objects.get(name=Attribution.CREATOR)
        org = OrganizationFactory()
        form = make_form(
            cleaned_data={"creator": org},
            changed_data=["creator"],
        )

        save_dataset_creator(Mock(), dataset, form)

        assert DatasetAttribution.objects.filter(dataset=dataset, attribution=attribution, organization=org).exists()

    def test_deletes_old_creator_attributions(self):
        dataset = DatasetFactory()
        attribution = Attribution.objects.get(name=Attribution.CREATOR)
        old_da = DatasetAttributionFactory(dataset=dataset, attribution=attribution)
        form = make_form(
            cleaned_data={"creator": None},
            changed_data=["creator"],
        )

        save_dataset_creator(Mock(), dataset, form)

        assert not DatasetAttribution.objects.filter(pk=old_da.pk).exists()

    def test_replaces_old_creator_with_new_organization(self):
        dataset = DatasetFactory()
        attribution = Attribution.objects.get(name=Attribution.CREATOR)
        old_da = DatasetAttributionFactory(dataset=dataset, attribution=attribution)
        new_org = OrganizationFactory()
        form = make_form(
            cleaned_data={"creator": new_org},
            changed_data=["creator"],
        )

        save_dataset_creator(Mock(), dataset, form)

        assert not DatasetAttribution.objects.filter(pk=old_da.pk).exists()
        assert DatasetAttribution.objects.filter(
            dataset=dataset, attribution=attribution, organization=new_org
        ).exists()

    def test_does_not_delete_other_attribution_types(self):
        dataset = DatasetFactory()
        contributor_attribution = AttributionFactory(name=Attribution.CONTRIBUTOR)
        contributor_da = DatasetAttributionFactory(dataset=dataset, attribution=contributor_attribution)
        form = make_form(
            cleaned_data={"creator": None},
            changed_data=["creator"],
        )

        save_dataset_creator(Mock(), dataset, form)

        assert DatasetAttribution.objects.filter(pk=contributor_da.pk).exists()

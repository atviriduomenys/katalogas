from unittest.mock import Mock, patch

import pytest

from vitrina.datasets.factories import (
    AttributionFactory,
    DatasetAttributionFactory,
    DatasetFactory,
    DatasetQualifiedRelationFactory,
    DatasetRelationFactory,
    RelationFactory,
)
from vitrina.datasets.models import Attribution, DatasetAttribution, DatasetQualifiedRelation, DatasetRelation, Relation
from vitrina.dcat.view_helpers import (
    can_delete_distribution_in_wizard,
    save_dataset_attribution,
    save_dataset_qualified_relations,
    save_dataset_relations,
    save_produces_relations,
)
from vitrina.orgs.factories import OrganizationFactory
from vitrina.resources.factories import DatasetDistributionFactory

pytestmark = pytest.mark.django_db


def make_form(cleaned_data: dict, changed_data: list) -> Mock:
    form = Mock()
    form.cleaned_data = cleaned_data
    form.changed_data = changed_data
    form.fields = {field: Mock(label=field) for field in cleaned_data}
    return form


class TestSaveDatasetRelations:
    def test_skips_field_not_in_changed_data(self):
        dataset = DatasetFactory()
        other_dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"has_part": [other_dataset]},
            changed_data=[],
        )

        save_dataset_relations(Mock(), dataset, form)

        assert DatasetRelation.objects.filter(dataset=dataset).count() == 0

    def test_warns_when_relation_type_does_not_exist(self):
        dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"has_part": [DatasetFactory()]},
            changed_data=["has_part"],
        )
        request = Mock()

        with patch("vitrina.dcat.view_helpers.messages") as mock_messages:
            save_dataset_relations(request, dataset, form)

        mock_messages.warning.assert_called_once()
        assert DatasetRelation.objects.filter(dataset=dataset).count() == 0

    def test_non_inverse_creates_relation_and_m2m(self):
        dataset = DatasetFactory()
        relation = RelationFactory(name=Relation.CATALOG)
        other_dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"has_part": [other_dataset]},
            changed_data=["has_part"],
        )

        save_dataset_relations(Mock(), dataset, form)

        dr = DatasetRelation.objects.get(relation=relation, dataset=dataset, part_of=other_dataset)
        assert dataset.part_of.filter(pk=dr.pk).exists()

    def test_non_inverse_deletes_old_relations(self):
        dataset = DatasetFactory()
        relation = RelationFactory(name=Relation.CATALOG)
        old_dataset = DatasetFactory()
        old_dr = DatasetRelationFactory(relation=relation, dataset=dataset, part_of=old_dataset)
        dataset.part_of.add(old_dr)
        form = make_form(
            cleaned_data={"has_part": []},
            changed_data=["has_part"],
        )

        save_dataset_relations(Mock(), dataset, form)

        assert not DatasetRelation.objects.filter(pk=old_dr.pk).exists()

    def test_non_inverse_replaces_old_relations_with_new(self):
        dataset = DatasetFactory()
        relation = RelationFactory(name=Relation.CATALOG)
        old_dataset = DatasetFactory()
        old_dr = DatasetRelationFactory(relation=relation, dataset=dataset, part_of=old_dataset)
        dataset.part_of.add(old_dr)
        new_dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"has_part": [new_dataset]},
            changed_data=["has_part"],
        )

        save_dataset_relations(Mock(), dataset, form)

        assert not DatasetRelation.objects.filter(pk=old_dr.pk).exists()
        assert DatasetRelation.objects.filter(relation=relation, dataset=dataset, part_of=new_dataset).exists()

    def test_inverse_creates_relation_with_swapped_roles_and_m2m(self):
        dataset = DatasetFactory()
        relation = RelationFactory(name=Relation.RELATES_TO_INFORMATION_SYSTEM)
        other_dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"relates_to_information_system": [other_dataset]},
            changed_data=["relates_to_information_system"],
        )

        save_dataset_relations(Mock(), dataset, form)

        dr = DatasetRelation.objects.get(relation=relation, dataset=other_dataset, part_of=dataset)
        assert other_dataset.part_of.filter(pk=dr.pk).exists()

    def test_inverse_deletes_old_relations(self):
        dataset = DatasetFactory()
        relation = RelationFactory(name=Relation.RELATES_TO_INFORMATION_SYSTEM)
        old_dataset = DatasetFactory()
        old_dr = DatasetRelationFactory(relation=relation, dataset=old_dataset, part_of=dataset)
        old_dataset.part_of.add(old_dr)
        form = make_form(
            cleaned_data={"relates_to_information_system": []},
            changed_data=["relates_to_information_system"],
        )

        save_dataset_relations(Mock(), dataset, form)

        assert not DatasetRelation.objects.filter(pk=old_dr.pk).exists()


class TestSaveProducesRelations:
    def test_skips_when_no_produces_field_in_changed_data(self):
        dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"produces_datasets": [DatasetFactory()]},
            changed_data=[],
        )

        save_produces_relations(Mock(), dataset, form)

        assert DatasetRelation.objects.filter(dataset=dataset).count() == 0

    def test_triggers_when_any_produces_field_in_changed_data(self):
        dataset = DatasetFactory()
        other = DatasetFactory()
        form = make_form(
            cleaned_data={"produces_datasets": [], "produces_services": [other], "produces_catalogs": []},
            changed_data=["produces_services"],
        )

        save_produces_relations(Mock(), dataset, form)

        assert DatasetRelation.objects.filter(dataset=dataset).count() == 1

    def test_warns_when_produces_relation_type_does_not_exist(self):
        Relation.objects.filter(name=Relation.PRODUCES).delete()
        dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"produces_datasets": [DatasetFactory()], "produces_services": [], "produces_catalogs": []},
            changed_data=["produces_datasets"],
        )
        request = Mock()

        with patch("vitrina.dcat.view_helpers.messages") as mock_messages:
            save_produces_relations(request, dataset, form)

        mock_messages.warning.assert_called_once()
        assert DatasetRelation.objects.filter(dataset=dataset).count() == 0

    def test_creates_relation_for_produces_datasets(self):
        dataset = DatasetFactory()
        relation = Relation.objects.get(name=Relation.PRODUCES)
        produced = DatasetFactory()
        form = make_form(
            cleaned_data={"produces_datasets": [produced], "produces_services": [], "produces_catalogs": []},
            changed_data=["produces_datasets"],
        )

        save_produces_relations(Mock(), dataset, form)

        assert DatasetRelation.objects.filter(relation=relation, dataset=dataset, part_of=produced).exists()

    def test_creates_relation_for_produces_services(self):
        dataset = DatasetFactory()
        relation = Relation.objects.get(name=Relation.PRODUCES)
        produced = DatasetFactory()
        form = make_form(
            cleaned_data={"produces_datasets": [], "produces_services": [produced], "produces_catalogs": []},
            changed_data=["produces_services"],
        )

        save_produces_relations(Mock(), dataset, form)

        assert DatasetRelation.objects.filter(relation=relation, dataset=dataset, part_of=produced).exists()

    def test_creates_relation_for_produces_catalogs(self):
        dataset = DatasetFactory()
        relation = Relation.objects.get(name=Relation.PRODUCES)
        produced = DatasetFactory()
        form = make_form(
            cleaned_data={"produces_datasets": [], "produces_services": [], "produces_catalogs": [produced]},
            changed_data=["produces_catalogs"],
        )

        save_produces_relations(Mock(), dataset, form)

        assert DatasetRelation.objects.filter(relation=relation, dataset=dataset, part_of=produced).exists()

    def test_creates_relations_across_all_three_fields(self):
        dataset = DatasetFactory()
        relation = Relation.objects.get(name=Relation.PRODUCES)
        d1, d2, d3 = DatasetFactory(), DatasetFactory(), DatasetFactory()
        form = make_form(
            cleaned_data={"produces_datasets": [d1], "produces_services": [d2], "produces_catalogs": [d3]},
            changed_data=["produces_datasets", "produces_services", "produces_catalogs"],
        )

        save_produces_relations(Mock(), dataset, form)

        assert DatasetRelation.objects.filter(relation=relation, dataset=dataset).count() == 3

    def test_deletes_old_produces_relations(self):
        dataset = DatasetFactory()
        relation = Relation.objects.get(name=Relation.PRODUCES)
        old = DatasetFactory()
        old_dr = DatasetRelationFactory(relation=relation, dataset=dataset, part_of=old)
        dataset.part_of.add(old_dr)
        form = make_form(
            cleaned_data={"produces_datasets": [], "produces_services": [], "produces_catalogs": []},
            changed_data=["produces_datasets"],
        )

        save_produces_relations(Mock(), dataset, form)

        assert not DatasetRelation.objects.filter(pk=old_dr.pk).exists()

    def test_replaces_old_produces_relations_with_new(self):
        dataset = DatasetFactory()
        relation = Relation.objects.get(name=Relation.PRODUCES)
        old = DatasetFactory()
        old_dr = DatasetRelationFactory(relation=relation, dataset=dataset, part_of=old)
        dataset.part_of.add(old_dr)
        new = DatasetFactory()
        form = make_form(
            cleaned_data={"produces_datasets": [new], "produces_services": [], "produces_catalogs": []},
            changed_data=["produces_datasets"],
        )

        save_produces_relations(Mock(), dataset, form)

        assert not DatasetRelation.objects.filter(pk=old_dr.pk).exists()
        assert DatasetRelation.objects.filter(relation=relation, dataset=dataset, part_of=new).exists()


class TestSaveDatasetAttribution:
    def test_skips_field_not_in_changed_data(self):
        dataset = DatasetFactory()
        AttributionFactory(name=Attribution.CONTRIBUTOR)
        form = make_form(
            cleaned_data={"qualified_attribution": [OrganizationFactory()]},
            changed_data=[],
        )

        save_dataset_attribution(Mock(), dataset, form)

        assert DatasetAttribution.objects.filter(dataset=dataset).count() == 0

    def test_warns_when_contributor_attribution_does_not_exist(self):
        dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"qualified_attribution": [OrganizationFactory()]},
            changed_data=["qualified_attribution"],
        )
        request = Mock()

        with patch("vitrina.dcat.view_helpers.messages") as mock_messages:
            save_dataset_attribution(request, dataset, form)

        mock_messages.warning.assert_called_once()
        assert DatasetAttribution.objects.filter(dataset=dataset).count() == 0

    def test_creates_attribution_for_each_selected_organization(self):
        dataset = DatasetFactory()
        attribution = AttributionFactory(name=Attribution.CONTRIBUTOR)
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        form = make_form(
            cleaned_data={"qualified_attribution": [org1, org2]},
            changed_data=["qualified_attribution"],
        )

        save_dataset_attribution(Mock(), dataset, form)

        assert DatasetAttribution.objects.filter(dataset=dataset, attribution=attribution, organization=org1).exists()
        assert DatasetAttribution.objects.filter(dataset=dataset, attribution=attribution, organization=org2).exists()

    def test_deletes_old_contributor_attributions(self):
        dataset = DatasetFactory()
        attribution = AttributionFactory(name=Attribution.CONTRIBUTOR)
        old_da = DatasetAttributionFactory(dataset=dataset, attribution=attribution)
        form = make_form(
            cleaned_data={"qualified_attribution": []},
            changed_data=["qualified_attribution"],
        )

        save_dataset_attribution(Mock(), dataset, form)

        assert not DatasetAttribution.objects.filter(pk=old_da.pk).exists()

    def test_does_not_delete_other_attribution_types(self):
        dataset = DatasetFactory()
        AttributionFactory(name=Attribution.CONTRIBUTOR)
        creator_attribution = AttributionFactory(name=Attribution.CREATOR)
        creator_da = DatasetAttributionFactory(dataset=dataset, attribution=creator_attribution)
        form = make_form(
            cleaned_data={"qualified_attribution": []},
            changed_data=["qualified_attribution"],
        )

        save_dataset_attribution(Mock(), dataset, form)

        assert DatasetAttribution.objects.filter(pk=creator_da.pk).exists()


class TestSaveDatasetQualifiedRelations:
    def test_skips_field_not_in_changed_data(self):
        dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"qualified_relation": ["https://example.com/rel"]},
            changed_data=[],
        )

        save_dataset_qualified_relations(dataset, form)

        assert DatasetQualifiedRelation.objects.filter(dataset=dataset).count() == 0

    def test_creates_relation_for_each_url(self):
        dataset = DatasetFactory()
        form = make_form(
            cleaned_data={"qualified_relation": ["https://example.com/rel1", "https://example.com/rel2"]},
            changed_data=["qualified_relation"],
        )

        save_dataset_qualified_relations(dataset, form)

        assert DatasetQualifiedRelation.objects.filter(dataset=dataset, url="https://example.com/rel1").exists()
        assert DatasetQualifiedRelation.objects.filter(dataset=dataset, url="https://example.com/rel2").exists()

    def test_deletes_old_relations_before_creating_new(self):
        dataset = DatasetFactory()
        old = DatasetQualifiedRelationFactory(dataset=dataset, url="https://example.com/old")
        form = make_form(
            cleaned_data={"qualified_relation": ["https://example.com/new"]},
            changed_data=["qualified_relation"],
        )

        save_dataset_qualified_relations(dataset, form)

        assert not DatasetQualifiedRelation.objects.filter(pk=old.pk).exists()
        assert DatasetQualifiedRelation.objects.filter(dataset=dataset, url="https://example.com/new").exists()

    def test_empty_list_deletes_all_relations(self):
        dataset = DatasetFactory()
        DatasetQualifiedRelationFactory(dataset=dataset)
        DatasetQualifiedRelationFactory(dataset=dataset)
        form = make_form(
            cleaned_data={"qualified_relation": []},
            changed_data=["qualified_relation"],
        )

        save_dataset_qualified_relations(dataset, form)

        assert DatasetQualifiedRelation.objects.filter(dataset=dataset).count() == 0


class TestCanDeleteDistributionInWizard:
    def test_returns_true_when_dataset_is_not_public(self):
        distribution = DatasetDistributionFactory(dataset=DatasetFactory(is_public=False))
        assert can_delete_distribution_in_wizard(distribution) is True

    def test_returns_false_when_dataset_is_public(self):
        distribution = DatasetDistributionFactory(dataset=DatasetFactory(is_public=True))
        assert can_delete_distribution_in_wizard(distribution) is False

import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.classifiers.factories import ConceptFactory, LicenceFactory
from vitrina.classifiers.models import ConceptSchema
from vitrina.datasets.factories import DatasetFactory, DatasetServiceFactory
from vitrina.dcat.forms.distribution_forms import DistributionForm
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.factories import MetadataFactory

pytestmark = pytest.mark.django_db


class TestDistributionForm:
    def test_access_url_format_is_required(self):
        dataset = DatasetFactory()

        form = DistributionForm(dataset)

        assert form.fields["access_url"].required is True

    def test_data_service_and_format_not_required(self):
        dataset = DatasetFactory()

        form = DistributionForm(dataset)

        assert not form.fields["data_service"].required
        assert not form.fields["format"].required

    def test_default_licence_set_as_initial_when_creating(self):
        dataset = DatasetFactory()
        default_licence = LicenceFactory(is_default=True)

        form = DistributionForm(dataset)

        assert form.initial["licence"] == default_licence

    def test_default_licence_not_set_when_no_default_licence_exists(self):
        dataset = DatasetFactory()

        form = DistributionForm(dataset)

        assert "licence" not in form.initial

    def test_default_licence_not_set_when_editing_existing_resource(self):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory(dataset=dataset)
        LicenceFactory(is_default=True)

        form = DistributionForm(dataset, instance=distribution)

        assert not form.initial.get("licence")

    def test_name_initial_set_from_metadata_when_editing(self):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory(dataset=dataset)
        MetadataFactory.create(
            dataset=dataset,
            content_type=ContentType.objects.get_for_model(distribution),
            object_id=distribution.pk,
            name="my-resource-name",
        )

        form = DistributionForm(dataset, instance=distribution)

        assert form.initial["name"] == "my-resource-name"

    def test_name_initial_not_set_when_no_metadata(self):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory(dataset=dataset, name="")

        form = DistributionForm(dataset, instance=distribution)

        assert not form.initial.get("name")

    def test_data_service_queryset_includes_non_public_service_datasets(self):
        dataset = DatasetFactory()
        public_service_dataset = DatasetServiceFactory(is_public=True)
        non_public_service_dataset = DatasetServiceFactory(is_public=False)
        non_public_non_service_dataset = DatasetFactory(is_public=False)

        form = DistributionForm(dataset)

        assert non_public_service_dataset in form.fields["data_service"].queryset
        assert public_service_dataset not in form.fields["data_service"].queryset
        assert non_public_non_service_dataset not in form.fields["data_service"].queryset

    def test_status_queryset_filtered_to_distribution_status_concepts(self):
        dataset = DatasetFactory()
        status_schema, _ = ConceptSchema.objects.get_or_create(uri=DatasetDistribution.DISTRIBUTION_STATUS_URI)
        matching_concept = ConceptFactory(concept_schemas=[status_schema])
        other_concept = ConceptFactory()

        form = DistributionForm(dataset)

        assert matching_concept in form.fields["status"].queryset
        assert other_concept not in form.fields["status"].queryset

    def test_duplicate_download_url_in_same_dataset_raises_error(self):
        dataset = DatasetFactory()
        DatasetDistributionFactory(dataset=dataset, download_url="https://example.com/data.csv")

        form = DistributionForm(
            dataset,
            data={
                "access_url": "https://example.com",
                "download_url": "https://example.com/data.csv",
            },
        )

        assert not form.is_valid()
        assert "download_url" in form.errors
        assert "Duomenų šaltinis su šia atsisiuntimo nuoroda jau egzistuoja." in form.errors["download_url"]

    def test_duplicate_download_url_not_raised_when_updating_self(self):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory(dataset=dataset, download_url="https://example.com/data.csv")

        form = DistributionForm(
            dataset,
            instance=distribution,
            data={
                "access_url": "https://example.com",
                "download_url": "https://example.com/data.csv",
            },
        )

        assert "download_url" not in form.errors

    def test_both_rights_relation_and_conditions_raises_error(self):
        dataset = DatasetFactory()

        form = DistributionForm(
            dataset,
            data={
                "access_url": "https://example.com",
                "rights_relation": "https://example.com/rights",
                "conditions": "Some conditions text",
            },
        )

        assert not form.is_valid()
        assert "rights_relation" in form.errors
        assert "conditions" in form.errors
        assert "Užpildykite tik vieną teisių deklaracijų lauką." in form.errors["rights_relation"]
        assert "Užpildykite tik vieną teisių deklaracijų lauką." in form.errors["conditions"]

    def test_non_ascii_name_raises_error(self):
        dataset = DatasetFactory()

        form = DistributionForm(
            dataset,
            data={"access_url": "https://example.com", "name": "resursąs"},
        )

        assert not form.is_valid()
        assert "name" in form.errors
        assert "Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės." in form.errors["name"]

    def test_uppercase_name_raises_error(self):
        dataset = DatasetFactory()

        form = DistributionForm(
            dataset,
            data={"access_url": "https://example.com", "name": "MyResource"},
        )

        assert not form.is_valid()
        assert "name" in form.errors
        assert "Kodiniame pavadinime gali būti naudojamos tik mažosios raidės." in form.errors["name"]

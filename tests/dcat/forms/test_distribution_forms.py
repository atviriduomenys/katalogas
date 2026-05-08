import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.classifiers.factories import ConceptFactory, DocumentationFactory, LicenceFactory
from vitrina.classifiers.models import ConceptSchema
from vitrina.datasets.factories import DatasetFactory, DatasetServiceFactory
from vitrina.dcat.forms.distribution_forms import DatasetDistributionForm
from vitrina.orgs.factories import OrganizationFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution, DISTRIBUTION_STANDARD_URI
from vitrina.structure.factories import MetadataFactory

pytestmark = pytest.mark.django_db


class TestDatasetDistributionForm:
    def test_access_url_availability_title_description_are_required(self):
        dataset = DatasetFactory()

        form = DatasetDistributionForm(dataset)

        assert form.fields["access_url"].required is True
        assert form.fields["availability"].required is True
        assert form.fields["title"].required is True
        assert form.fields["description"].required is True

    def test_data_service_and_format_not_required(self):
        dataset = DatasetFactory()

        form = DatasetDistributionForm(dataset)

        assert not form.fields["data_service"].required
        assert not form.fields["format"].required

    def test_default_licence_set_as_initial_when_creating(self):
        dataset = DatasetFactory()
        default_licence = LicenceFactory(is_default=True)

        form = DatasetDistributionForm(dataset)

        assert form.initial["licence"] == default_licence

    def test_default_licence_not_set_when_no_default_licence_exists(self):
        dataset = DatasetFactory()

        form = DatasetDistributionForm(dataset)

        assert "licence" not in form.initial

    def test_default_licence_not_set_when_editing_existing_resource(self):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory(dataset=dataset)
        LicenceFactory(is_default=True)

        form = DatasetDistributionForm(dataset, instance=distribution)

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

        form = DatasetDistributionForm(dataset, instance=distribution)

        assert form.initial["name"] == "my-resource-name"

    def test_documentation_initial_set_from_resource_when_editing(self):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory(dataset=dataset)
        doc1 = DocumentationFactory(documentation_link="https://example.com/doc1")
        doc2 = DocumentationFactory(documentation_link="https://example.com/doc2")
        distribution.documentation.set([doc1, doc2])

        form = DatasetDistributionForm(dataset, instance=distribution)

        assert set(form.initial["documentation"]) == {"https://example.com/doc1", "https://example.com/doc2"}

    def test_documentation_initial_not_set_when_creating(self):
        dataset = DatasetFactory()

        form = DatasetDistributionForm(dataset)

        assert "documentation" not in form.initial

    def test_name_initial_not_set_when_no_metadata(self):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory(dataset=dataset, name="")

        form = DatasetDistributionForm(dataset, instance=distribution)

        assert not form.initial.get("name")

    def test_data_service_queryset_includes_non_public_service_datasets(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        public_service_dataset = DatasetServiceFactory(organization=organization, is_public=True)
        non_public_service_dataset = DatasetServiceFactory(organization=organization, is_public=False)
        non_public_non_service_dataset = DatasetFactory(organization=organization, is_public=False)

        form = DatasetDistributionForm(dataset)

        assert non_public_service_dataset in form.fields["data_service"].queryset
        assert public_service_dataset not in form.fields["data_service"].queryset
        assert non_public_non_service_dataset not in form.fields["data_service"].queryset

    def test_conforms_to_queryset_filtered_to_distribution_standard_concepts(self):
        dataset = DatasetFactory()
        standard_schema, _ = ConceptSchema.objects.get_or_create(uri=DISTRIBUTION_STANDARD_URI)
        matching_concept = ConceptFactory(concept_schemas=[standard_schema])
        other_concept = ConceptFactory()

        form = DatasetDistributionForm(dataset)

        assert matching_concept in form.fields["conforms_to"].queryset
        assert other_concept not in form.fields["conforms_to"].queryset

    def test_status_queryset_filtered_to_distribution_status_concepts(self):
        dataset = DatasetFactory()
        status_schema, _ = ConceptSchema.objects.get_or_create(uri=DatasetDistribution.DISTRIBUTION_STATUS_URI)
        matching_concept = ConceptFactory(concept_schemas=[status_schema])
        other_concept = ConceptFactory()

        form = DatasetDistributionForm(dataset)

        assert matching_concept in form.fields["status"].queryset
        assert other_concept not in form.fields["status"].queryset

    def test_duplicate_download_url_in_same_dataset_raises_error(self):
        dataset = DatasetFactory()
        DatasetDistributionFactory(dataset=dataset, download_url="https://example.com/data.csv")

        form = DatasetDistributionForm(
            dataset,
            data={
                "access_url": "https://example.com",
                "download_url": "https://example.com/data.csv",
            },
        )

        assert not form.is_valid()
        assert "download_url" in form.errors
        assert "Pateiktis su šia atsisiuntimo nuoroda jau egzistuoja." in form.errors["download_url"]

    def test_duplicate_download_url_not_raised_when_updating_self(self):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory(dataset=dataset, download_url="https://example.com/data.csv")

        form = DatasetDistributionForm(
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

        form = DatasetDistributionForm(
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

        form = DatasetDistributionForm(
            dataset,
            data={"access_url": "https://example.com", "name": "resursąs"},
        )

        assert not form.is_valid()
        assert "name" in form.errors
        assert "Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės." in form.errors["name"]

    def test_uppercase_name_raises_error(self):
        dataset = DatasetFactory()

        form = DatasetDistributionForm(
            dataset,
            data={"access_url": "https://example.com", "name": "MyResource"},
        )

        assert not form.is_valid()
        assert "name" in form.errors
        assert "Kodiniame pavadinime gali būti naudojamos tik mažosios raidės." in form.errors["name"]

    def test_uppercase_checksum_value_raises_error(self):
        dataset = DatasetFactory()

        form = DatasetDistributionForm(
            dataset,
            data={"access_url": "https://example.com", "checksum_value": "ABCDEF123"},
        )

        assert not form.is_valid()
        assert "checksum_value" in form.errors
        assert "Kontrolinės sumos reikšmei gali būti naudojamos tik mažosios raidės." in form.errors["checksum_value"]

    def test_lowercase_checksum_value_is_valid(self):
        dataset = DatasetFactory()

        form = DatasetDistributionForm(
            dataset,
            data={"access_url": "https://example.com", "checksum_value": "abcdef123"},
        )

        assert "checksum_value" not in form.errors

    def test_invalid_documentation_url_raises_error(self):
        dataset = DatasetFactory()

        form = DatasetDistributionForm(
            dataset,
            data={"access_url": "https://example.com", "documentation": ["not-a-url"]},
        )

        assert not form.is_valid()
        assert "documentation" in form.errors
        assert "Yra klaidų sąraše." in form.errors["documentation"]

    def test_valid_documentation_urls_are_accepted(self):
        dataset = DatasetFactory()

        form = DatasetDistributionForm(
            dataset,
            data={
                "access_url": "https://example.com",
                "documentation": ["https://example.com/doc1", "https://example.com/doc2"],
            },
        )

        assert "documentation" not in form.errors
        assert form.cleaned_data["documentation"] == ["https://example.com/doc1", "https://example.com/doc2"]

import pytest
from django.utils.translation import override as translation_override
from vitrina.classifiers.factories import (
    ConceptFactory,
    DocumentationFactory,
)
from vitrina.classifiers.models import (
    Concept,
    ConceptSchema,
    LANGUAGE_CONCEPT_SCHEMA_URI,
)
from vitrina.datasets.form_helpers import DATASET_STANDARD_URI
from vitrina.datasets.factories import ContactFactory, DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.dcat.forms.dataset_forms import (
    DatasetResourceForm,
    InformationSystemResourceForm,
    ServiceResourceForm,
)
from vitrina.orgs.factories import OrganizationFactory
from vitrina.uapi.factories import AgentFactory

pytestmark = pytest.mark.django_db


class TestBaseResourceForm:
    def test_parent_initial_value_set_when_parent_dataset_id_given(self):
        organization = OrganizationFactory()
        parent_dataset = DatasetFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=parent_dataset.pk,
        )

        assert form.fields["parent"].initial == parent_dataset.pk

    def test_parent_initial_not_set_when_no_parent_dataset_id(self):
        organization = OrganizationFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
        )

        assert form.fields["parent"].initial is None

    def test_parent_queryset_excludes_instance(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        other_dataset = DatasetFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert dataset not in form.fields["parent"].queryset
        assert other_dataset in form.fields["parent"].queryset

    def test_description_not_required_when_language_is_en(self):
        organization = OrganizationFactory()

        with translation_override("en"):
            form = InformationSystemResourceForm(
                organization=organization,
                parent_dataset_id=None,
            )

        assert form.fields["description"].required is False

    def test_description_required_when_language_is_lt(self):
        organization = OrganizationFactory()

        with translation_override("lt"):
            form = InformationSystemResourceForm(
                organization=organization,
                parent_dataset_id=None,
            )

        assert form.fields["description"].required is True

    def test_name_with_non_ascii_raises_error(self):
        organization = OrganizationFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={"name": f"{organization.name}ąčę"},
        )

        assert not form.is_valid()
        assert "name" in form.errors
        assert "Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės." in form.errors["name"]


class TestInformationSystemResourceForm:
    def test_both_rights_fields_raises_error(self):
        organization = OrganizationFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "rights_relation": "https://example.com",
                "conditions": "Some conditions",
            },
        )

        assert not form.is_valid()
        assert "rights_relation" in form.errors
        assert "conditions" in form.errors
        assert "Užpildykite tik vieną teisių deklaracijų lauką." in form.errors["rights_relation"]
        assert "Užpildykite tik vieną teisių deklaracijų lauką." in form.errors["conditions"]

    def test_invalid_identifier_raises_error(self):
        organization = OrganizationFactory()
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test IS",
                "description": "Test description",
                "name": "testis",
                "information_system_importance": importance.pk,
                "information_system_publisher": organization.pk,
                "information_system_creator": organization.pk,
                "identifier": "not-four-digits",
            },
        )

        assert not form.is_valid()
        assert "identifier" in form.errors
        assert "Žymėjimas turi atitikti šabloną: ^\\d{4}$" in form.errors["identifier"]

    def test_valid_identifier_passes(self):
        organization = OrganizationFactory()
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test IS",
                "description": "Test description",
                "name": "testis",
                "information_system_importance": importance.pk,
                "information_system_publisher": organization.pk,
                "information_system_creator": organization.pk,
                "identifier": "1234",
            },
        )

        assert not form.is_valid()
        assert "identifier" not in form.errors

    def test_invalid_applicable_legislation_url_raises_error(self):
        organization = OrganizationFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={"applicable_legislation": ["not-a-url"]},
        )

        assert not form.is_valid()
        assert "applicable_legislation" in form.errors

    def test_information_system_assessment_url_is_required(self):
        organization = OrganizationFactory()
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test IS",
                "description": "Test description",
                "name": "testis",
                "information_system_importance": importance.pk,
                "information_system_publisher": organization.pk,
                "information_system_creator": organization.pk,
            },
        )

        assert not form.is_valid()
        assert "information_system_assessment_url" in form.errors

    def test_languages_queryset_filtered_to_language_concepts(self):
        organization = OrganizationFactory()
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language_concept = ConceptFactory(concept_schemas=[language_schema])
        other_concept = ConceptFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
        )

        assert language_concept in form.fields["languages"].queryset
        assert other_concept not in form.fields["languages"].queryset

    def test_languages_not_required(self):
        organization = OrganizationFactory()
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])

        form = InformationSystemResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test IS",
                "description": "Test description",
                "name": "testis",
                "information_system_importance": importance.pk,
                "information_system_publisher": organization.pk,
                "information_system_creator": organization.pk,
                "information_system_assessment_url": "https://example.com/assessment",
            },
        )

        assert "languages" not in form.errors


class TestServiceResourceForm:
    def test_no_agent_no_endpoint_url_raises_error(self):
        organization = OrganizationFactory()
        contact = ContactFactory(organization=organization)

        form = ServiceResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test Service",
                "name": "testservice",
                "tags": "tag1",
                "contact": contact.pk,
            },
        )

        error_msg = "Pasirinkite agentą, arba nurodykite API adresą."
        assert not form.is_valid()
        assert "agent" in form.errors
        assert "endpoint_url" in form.errors
        assert error_msg in form.errors["agent"]
        assert error_msg in form.errors["endpoint_url"]

    def test_no_endpoint_description_without_agent_raises_error(self):
        organization = OrganizationFactory()
        contact = ContactFactory(organization=organization)

        form = ServiceResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test Service",
                "name": "testservice",
                "tags": "tag1",
                "contact": contact.pk,
                "endpoint_url": "http://example.com",
            },
        )

        assert not form.is_valid()
        assert "endpoint_description" in form.errors
        assert "Pasirinkite agentą, arba nurodykite API specifikaciją." in form.errors["endpoint_description"]

    def test_agent_with_endpoint_url_raises_error(self):
        organization = OrganizationFactory()
        contact = ContactFactory(organization=organization)
        agent = AgentFactory(organization=organization)

        form = ServiceResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test Service",
                "name": "testservice",
                "tags": "tag1",
                "contact": contact.pk,
                "agent": agent.pk,
                "endpoint_url": "http://example.com",
            },
        )

        error_msg = "Pasirinkus agentą, šis laukas negali būti užpildytas."
        assert not form.is_valid()
        assert "endpoint_url" in form.errors
        assert error_msg in form.errors["endpoint_url"]

    def test_agent_with_endpoint_description_raises_error(self):
        organization = OrganizationFactory()
        contact = ContactFactory(organization=organization)
        agent = AgentFactory(organization=organization)

        form = ServiceResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test Service",
                "name": "testservice",
                "tags": "tag1",
                "contact": contact.pk,
                "agent": agent.pk,
                "endpoint_description": "http://example.com/spec",
            },
        )

        error_msg = "Pasirinkus agentą, šis laukas negali būti užpildytas."
        assert not form.is_valid()
        assert "endpoint_description" in form.errors
        assert error_msg in form.errors["endpoint_description"]

    def test_follows_license_service_quality_not_required(self):
        organization = OrganizationFactory()
        contact = ContactFactory(organization=organization)

        form = ServiceResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test Service",
                "name": "testservice",
                "tags": "tag1",
                "contact": contact.pk,
                "endpoint_url": "http://example.com",
                "endpoint_description": "http://example.com/spec",
            },
        )

        assert "follows" not in form.errors
        assert "license" not in form.errors
        assert "service_quality" not in form.errors

    def test_conforms_to_uapi_without_agent_raises_error(self):
        organization = OrganizationFactory()
        contact = ContactFactory(organization=organization)
        uapi_concept = Concept.objects.get(code="UAPI")

        form = ServiceResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test Service",
                "name": "testservice",
                "tags": "tag1",
                "contact": contact.pk,
                "conforms_to": uapi_concept.pk,
                "endpoint_url": "http://example.com",
                "endpoint_description": "http://example.com/spec",
            },
        )

        assert not form.is_valid()
        assert "agent" in form.errors
        assert "UDTS standartą atitinkančios paslaugos privalo būti susietos su agentu." in form.errors["agent"][0]


class TestDatasetResourceForm:
    def test_temporal_start_after_end_raises_error(self):
        organization = OrganizationFactory()

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "temporal_start": "2025-08-20",
                "temporal_end": "2025-08-10",
            },
        )

        assert not form.is_valid()
        assert "temporal_start" in form.errors
        assert "Laikotarpio pradžios data negali būti vėlesnė nei pabaigos data." in form.errors["temporal_start"]

    def test_temporal_start_before_end_no_error(self):
        organization = OrganizationFactory()

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "temporal_start": "2025-01-01",
                "temporal_end": "2025-12-31",
            },
        )

        assert not form.is_valid()
        assert "temporal_start" not in form.errors

    def test_documentation_initial_populated_from_instance(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        doc1 = DocumentationFactory(documentation_link="https://example.com/doc1")
        doc2 = DocumentationFactory(documentation_link="https://example.com/doc2")
        dataset.documentation.set([doc1, doc2])

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert set(form.initial["documentation"]) == {
            "https://example.com/doc1",
            "https://example.com/doc2",
        }

    def test_documentation_initial_empty_when_no_instance(self):
        organization = OrganizationFactory()

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
        )

        assert "documentation" not in form.initial

    def test_conforms_to_queryset_filtered_to_dataset_standard(self):
        organization = OrganizationFactory()
        dataset_standard_schema, _ = ConceptSchema.objects.get_or_create(uri=DATASET_STANDARD_URI)
        matching_concept = ConceptFactory(concept_schemas=[dataset_standard_schema])
        other_concept = ConceptFactory()

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
        )

        assert matching_concept in form.fields["conforms_to"].queryset
        assert other_concept not in form.fields["conforms_to"].queryset

    def test_languages_queryset_filtered_to_language_concepts(self):
        organization = OrganizationFactory()
        language_schema, _ = ConceptSchema.objects.get_or_create(uri=LANGUAGE_CONCEPT_SCHEMA_URI)
        language_concept = ConceptFactory(concept_schemas=[language_schema])
        other_concept = ConceptFactory()

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
        )

        assert language_concept in form.fields["languages"].queryset
        assert other_concept not in form.fields["languages"].queryset

    def test_dataset_type_queryset_filtered_to_dataset_type_concepts(self):
        organization = OrganizationFactory()
        dataset_type_schema, _ = ConceptSchema.objects.get_or_create(uri=Dataset.DATASET_TYPE_SCHEME_URI)
        matching_concept = ConceptFactory(concept_schemas=[dataset_type_schema])
        other_concept = ConceptFactory()

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
        )

        assert matching_concept in form.fields["dataset_type"].queryset
        assert other_concept not in form.fields["dataset_type"].queryset

    def test_conforms_to_languages_provenance_dataset_type_was_generated_by_not_required(self):
        organization = OrganizationFactory()

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "temporal_start": "2025-01-01",
                "temporal_end": "2025-12-31",
            },
        )

        assert "conforms_to" not in form.errors
        assert "languages" not in form.errors
        assert "provenance" not in form.errors
        assert "dataset_type" not in form.errors
        assert "was_generated_by" not in form.errors

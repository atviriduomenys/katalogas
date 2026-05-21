import pytest
from django.utils.translation import override as translation_override
from vitrina.classifiers.factories import (
    ApplicableLegislationFactory,
    ConceptFactory,
    DocumentationFactory,
)
from vitrina.classifiers.models import (
    Concept,
    ConceptSchema,
    LANGUAGE_CONCEPT_SCHEMA_URI,
)
from vitrina.datasets.form_helpers import DATASET_STANDARD_URI
from vitrina.datasets.factories import (
    AttributionFactory,
    ContactFactory,
    DatasetAttributionFactory,
    DatasetFactory,
    DatasetQualifiedRelationFactory,
    DatasetRelationFactory,
    DCATResourceSubclassFactory,
    RelationFactory,
)
from vitrina.datasets.models import Attribution, Dataset, DCATResourceSubclass, Relation
from vitrina.dcat.forms.dataset_forms import (
    DatasetResourceForm,
    DatasetUpdateForm,
    InformationSystemResourceForm,
    InformationSystemUpdateForm,
    ServiceResourceForm,
    ServiceUpdateForm,
)
from vitrina.identifiers.models import Agency, Identifier
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
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=False)
        other_dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=False)

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
    def test_parent_queryset_includes_is_dataset_from_same_org(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        matching_dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=False)

        form = InformationSystemResourceForm(organization=organization, parent_dataset_id=None)

        assert matching_dataset in form.fields["parent"].queryset

    def test_parent_queryset_excludes_dataset_from_different_org(self):
        organization = OrganizationFactory()
        other_organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        other_org_dataset = DatasetFactory(organization=other_organization, subclass=subclass, is_public=False)

        form = InformationSystemResourceForm(organization=organization, parent_dataset_id=None)

        assert other_org_dataset not in form.fields["parent"].queryset

    def test_parent_queryset_excludes_dataset_with_service_subclass(self):
        organization = OrganizationFactory()
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        service_dataset = DatasetFactory(organization=organization, subclass=service_subclass, is_public=False)

        form = InformationSystemResourceForm(organization=organization, parent_dataset_id=None)

        assert service_dataset not in form.fields["parent"].queryset

    def test_parent_queryset_excludes_public_dataset(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        public_dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=True)

        form = InformationSystemResourceForm(organization=organization, parent_dataset_id=None)

        assert public_dataset not in form.fields["parent"].queryset

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
                "information_system_publishers": [organization.pk],
                "creator": organization.pk,
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
                "information_system_publishers": [organization.pk],
                "creator": organization.pk,
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
                "information_system_publishers": [organization.pk],
                "creator": organization.pk,
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
                "information_system_publishers": [organization.pk],
                "creator": organization.pk,
                "information_system_assessment_url": "https://example.com/assessment",
            },
        )

        assert "languages" not in form.errors


class TestServiceResourceForm:
    def test_parent_queryset_includes_is_dataset_from_same_org(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        matching_dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=False)

        form = ServiceResourceForm(organization=organization, parent_dataset_id=None)

        assert matching_dataset in form.fields["parent"].queryset

    def test_parent_queryset_excludes_dataset_from_different_org(self):
        organization = OrganizationFactory()
        other_organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        other_org_dataset = DatasetFactory(organization=other_organization, subclass=subclass, is_public=False)

        form = ServiceResourceForm(organization=organization, parent_dataset_id=None)

        assert other_org_dataset not in form.fields["parent"].queryset

    def test_parent_queryset_excludes_dataset_with_service_subclass(self):
        organization = OrganizationFactory()
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        service_dataset = DatasetFactory(organization=organization, subclass=service_subclass, is_public=False)

        form = ServiceResourceForm(organization=organization, parent_dataset_id=None)

        assert service_dataset not in form.fields["parent"].queryset

    def test_parent_queryset_excludes_public_dataset(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        public_dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=True)

        form = ServiceResourceForm(organization=organization, parent_dataset_id=None)

        assert public_dataset not in form.fields["parent"].queryset

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

    def test_organization_required(self):
        organization = OrganizationFactory()

        form = ServiceResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test Service",
                "name": "testservice",
                "tags": "tag1",
                "endpoint_url": "http://example.com",
                "endpoint_description": "http://example.com/spec",
            },
        )

        assert not form.is_valid()
        assert "organization" in form.errors


class TestDatasetResourceForm:
    def test_parent_queryset_includes_service_dataset_from_same_org(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        matching_dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=False)

        form = DatasetResourceForm(organization=organization, parent_dataset_id=None)

        assert matching_dataset in form.fields["parent"].queryset

    def test_parent_queryset_excludes_dataset_from_different_org(self):
        organization = OrganizationFactory()
        other_organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        other_org_dataset = DatasetFactory(organization=other_organization, subclass=subclass, is_public=False)

        form = DatasetResourceForm(organization=organization, parent_dataset_id=None)

        assert other_org_dataset not in form.fields["parent"].queryset

    def test_parent_queryset_excludes_dataset_with_is_subclass(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        is_dataset = DatasetFactory(organization=organization, subclass=is_subclass, is_public=False)

        form = DatasetResourceForm(organization=organization, parent_dataset_id=None)

        assert is_dataset not in form.fields["parent"].queryset

    def test_parent_queryset_excludes_public_dataset(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        public_dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=True)

        form = DatasetResourceForm(organization=organization, parent_dataset_id=None)

        assert public_dataset not in form.fields["parent"].queryset

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

    def test_invalid_qualified_relation_url_raises_error(self):
        organization = OrganizationFactory()

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={"qualified_relation": ["not-a-url"]},
        )

        assert not form.is_valid()
        assert "qualified_relation" in form.errors

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

    def test_organization_required(self):
        organization = OrganizationFactory()

        form = DatasetResourceForm(
            organization=organization,
            parent_dataset_id=None,
            data={
                "title": "Test Dataset",
                "description": "Test description",
                "name": "testdataset",
            },
        )

        assert not form.is_valid()
        assert "organization" in form.errors

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


class TestInformationSystemUpdateForm:
    def test_identifier_initial_set_from_instance(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=subclass)
        agency, _ = Agency.objects.get_or_create(
            code=Agency.RISR_CODE,
            defaults={
                "name": "RISR",
                "uri": "http://registrai.lt",
                "identifier_validation_type": "REGEXP",
                "identifier_validation_options": r"^\d{4}$",
            },
        )
        Identifier.objects.create(
            resource=dataset,
            scheme_agency=agency,
            notation="5678",
            identifier_type=Identifier.IdentifierType.OTHER,
        )

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert form.fields["identifier"].initial == "5678"

    def test_identifier_initial_empty_when_no_identifier(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=subclass)

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert form.fields["identifier"].initial == ""

    def test_applicable_legislation_initial_set_from_instance(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=subclass)
        leg1 = ApplicableLegislationFactory(url="https://example.com/law1")
        leg2 = ApplicableLegislationFactory(url="https://example.com/law2")
        dataset.applicable_legislation.set([leg1, leg2])

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert set(form.initial["applicable_legislation"]) == {
            "https://example.com/law1",
            "https://example.com/law2",
        }

    def test_applicable_legislation_initial_empty_when_no_legislation(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=subclass)

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert form.initial["applicable_legislation"] == []


class TestDatasetUpdateForm:
    def test_documentation_initial_set_from_instance(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        doc1 = DocumentationFactory(documentation_link="https://example.com/doc1")
        doc2 = DocumentationFactory(documentation_link="https://example.com/doc2")
        dataset.documentation.set([doc1, doc2])

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert set(form.initial["documentation"]) == {
            "https://example.com/doc1",
            "https://example.com/doc2",
        }

    def test_documentation_initial_empty_when_no_documentation(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert form.initial["documentation"] == []

    def test_applicable_legislation_initial_set_from_instance(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        leg1 = ApplicableLegislationFactory(url="https://example.com/law1")
        leg2 = ApplicableLegislationFactory(url="https://example.com/law2")
        dataset.applicable_legislation.set([leg1, leg2])

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert set(form.initial["applicable_legislation"]) == {
            "https://example.com/law1",
            "https://example.com/law2",
        }

    def test_applicable_legislation_initial_empty_when_no_legislation(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert form.initial["applicable_legislation"] == []

    def test_qualified_attribution_initial_set_from_contributor_attributions(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        contributor = AttributionFactory(name=Attribution.CONTRIBUTOR)
        org = OrganizationFactory()
        DatasetAttributionFactory(dataset=dataset, attribution=contributor, organization=org)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert org.pk in form.initial["qualified_attribution"]

    def test_qualified_attribution_initial_excludes_other_attribution_types(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        AttributionFactory(name=Attribution.CONTRIBUTOR)
        creator = AttributionFactory(name=Attribution.CREATOR)
        org = OrganizationFactory()
        DatasetAttributionFactory(dataset=dataset, attribution=creator, organization=org)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert org.pk not in form.initial["qualified_attribution"]

    def test_qualified_attribution_initial_empty_when_no_attributions(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert list(form.initial["qualified_attribution"]) == []

    def test_qualified_relation_initial_set_from_instance(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        DatasetQualifiedRelationFactory(dataset=dataset, url="https://example.com/rel1")
        DatasetQualifiedRelationFactory(dataset=dataset, url="https://example.com/rel2")

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert set(form.initial["qualified_relation"]) == {
            "https://example.com/rel1",
            "https://example.com/rel2",
        }

    def test_qualified_relation_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert list(form.initial["qualified_relation"]) == []

    def test_creator_initial_set_from_first_creator_attribution(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        creator = Attribution.objects.get(name=Attribution.CREATOR)
        org = OrganizationFactory()
        DatasetAttributionFactory(dataset=dataset, attribution=creator, organization=org)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert form.initial["creator"] == org.pk

    def test_creator_initial_uses_first_record_when_multiple_exist(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        creator = Attribution.objects.get(name=Attribution.CREATOR)
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        first_da = DatasetAttributionFactory(dataset=dataset, attribution=creator, organization=org1)
        DatasetAttributionFactory(dataset=dataset, attribution=creator, organization=org2)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert form.initial["creator"] == first_da.organization_id

    def test_creator_initial_not_set_when_no_creator_attribution(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert "creator" not in form.initial

    def test_creator_initial_excludes_other_attribution_types(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        contributor = AttributionFactory(name=Attribution.CONTRIBUTOR)
        org = OrganizationFactory()
        DatasetAttributionFactory(dataset=dataset, attribution=contributor, organization=org)

        form = DatasetUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert "creator" not in form.initial


class TestServiceUpdateForm:
    def test_serves_datasets_initial_set_from_existing_relations(self):
        organization = OrganizationFactory()
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        dataset_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        service = DatasetFactory(organization=organization, subclass=service_subclass)
        served_dataset = DatasetFactory(organization=organization, subclass=dataset_subclass)
        relation = RelationFactory(name=Relation.SERVICE)
        DatasetRelationFactory(relation=relation, dataset=service, part_of=served_dataset)

        form = ServiceUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=service,
        )

        assert served_dataset in form.initial["serves_datasets"]

    def test_serves_datasets_initial_excludes_unrelated_datasets(self):
        organization = OrganizationFactory()
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        dataset_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        service = DatasetFactory(organization=organization, subclass=service_subclass)
        unrelated_dataset = DatasetFactory(organization=organization, subclass=dataset_subclass)

        form = ServiceUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=service,
        )

        assert unrelated_dataset not in form.initial["serves_datasets"]

    def test_serves_datasets_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        service = DatasetFactory(organization=organization, subclass=service_subclass)

        form = ServiceUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=service,
        )

        assert not form.initial["serves_datasets"].exists()


class TestInformationSystemUpdate:
    def test_has_part_initial_set_from_existing_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        catalog_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)
        catalog_dataset = DatasetFactory(organization=organization, subclass=catalog_subclass)
        relation = RelationFactory(name=Relation.CATALOG)
        DatasetRelationFactory(relation=relation, dataset=dataset, part_of=catalog_dataset)

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert catalog_dataset in form.initial["has_part"]

    def test_has_part_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert not form.initial["has_part"].exists()

    def test_relates_to_information_system_initial_set_from_existing_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)
        other_is = DatasetFactory(organization=organization, subclass=is_subclass)
        relation = RelationFactory(name=Relation.RELATES_TO_INFORMATION_SYSTEM)
        DatasetRelationFactory(relation=relation, dataset=other_is, part_of=dataset)

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert other_is in form.initial["relates_to_information_system"]

    def test_relates_to_information_system_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert not form.initial["relates_to_information_system"].exists()

    def test_related_information_system_initial_set_from_existing_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)
        other_is = DatasetFactory(organization=organization, subclass=is_subclass)
        relation = RelationFactory(name=Relation.RELATES_TO_INFORMATION_SYSTEM)
        DatasetRelationFactory(relation=relation, dataset=dataset, part_of=other_is)

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert other_is in form.initial["related_information_system"]

    def test_related_information_system_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)

        form = InformationSystemUpdateForm(
            organization=organization,
            parent_dataset_id=None,
            instance=dataset,
        )

        assert not form.initial["related_information_system"].exists()

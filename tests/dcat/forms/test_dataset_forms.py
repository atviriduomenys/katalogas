import pytest
from django.utils.translation import override as translation_override
from vitrina.classifiers.factories import (
    ApplicableLegislationFactory,
    CategoryFactory,
    ConceptFactory,
    DocumentationFactory,
    FormFieldTextFactory,
)
from vitrina.classifiers.models import (
    ConceptSchema,
    FormFieldText,
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
    DatasetRelationshipForm,
    DatasetResourceForm,
    DatasetUpdateForm,
    InformationSystemRelationshipForm,
    InformationSystemResourceForm,
    InformationSystemUpdateForm,
    ISPublicServiceRelationshipForm,
    ISPublicServiceResourceForm,
    ISPublicServiceUpdateForm,
    ServiceRelationshipForm,
    ServiceResourceForm,
    ServiceUpdateForm,
)
from vitrina.identifiers.models import Agency, Identifier
from vitrina.orgs.factories import OrganizationFactory


pytestmark = pytest.mark.django_db


class TestBaseResourceForm:
    def test_description_not_required_when_language_is_en(self):
        organization = OrganizationFactory()

        with translation_override("en"):
            form = InformationSystemResourceForm(
                organization=organization,
                url_parent=None,
            )

        assert form.fields["description"].required is False

    def test_description_required_when_language_is_lt(self):
        organization = OrganizationFactory()

        with translation_override("lt"):
            form = InformationSystemResourceForm(
                organization=organization,
                url_parent=None,
            )

        assert form.fields["description"].required is True

    def test_category_initial_set_from_instance(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        cat1 = CategoryFactory()
        cat2 = CategoryFactory()
        dataset.category.set([cat1, cat2])

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=None,
            instance=dataset,
        )

        assert set(form.initial["category"]) == {cat1, cat2}

    def test_category_initial_empty_when_instance_has_no_categories(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=None,
            instance=dataset,
        )

        assert list(form.initial["category"]) == []


class TestDatasetNameMixin:
    def test_name_with_non_ascii_raises_error(self):
        organization = OrganizationFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=None,
            data={"name": f"{organization.name}ąčę"},
        )

        assert not form.is_valid()
        assert "name" in form.errors
        assert (
            "Kodinis pavadinimas turi būti sudarytas iš mažųjų lotyniškų raidžių ir (arba) apatinių brūkšnių, žodžius atskiriant apatiniais brūkšniais"
            in form.errors["name"]
        )

    def test_create_form_raise_error_when_url_parent_that_has_no_metadata_name(self):
        organization = OrganizationFactory(name="")
        url_parent = DatasetFactory(metadata=False)

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=url_parent,
            data={"name": "myservice"},
        )

        error_msg = (
            "Organizacija neturi nurodyto kodinio pavadinimo. "
            "Priskirkite kodinį pavadinimą organizacijai ir bandykite iš naujo"
        )
        assert not form.is_valid()
        assert error_msg in form.non_field_errors()

    def test_update_form_raise_error_when_parent_has_no_metadata_name(self):
        organization = OrganizationFactory(name="")
        dataset = DatasetFactory(organization=organization, metadata=False)

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=None,
            instance=dataset,
            data={"name": "myservice"},
        )

        error_msg = (
            "Organizacija neturi nurodyto kodinio pavadinimo. "
            "Priskirkite kodinį pavadinimą organizacijai ir bandykite iš naujo"
        )
        assert not form.is_valid()
        assert error_msg in form.non_field_errors()

    def test_do_not_show_initial_name_for_create_form(self):
        organization = OrganizationFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=None,
        )

        assert "name" not in form.initial

    def test_show_initial_name_without_prefix_for_update_form(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(
            organization=organization,
            metadata=f"{organization.name}/myservice",
        )

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=None,
            instance=dataset,
        )

        assert form.initial["name"] == "myservice"

    def test_show_initial_name_without_slashes_stripped_for_update_form(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(
            organization=organization,
            metadata=f"{organization.name}/myservice/",
        )

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=None,
            instance=dataset,
        )

        assert form.initial["name"] == "myservice"

    def test_get_dataset_name_joins_prefix_and_name(self):
        organization = OrganizationFactory()
        form = InformationSystemResourceForm(organization=organization, url_parent=None)
        form.codename_prefix = "gov"
        form.cleaned_data = {"name": "myservice"}

        assert form.get_dataset_name() == "gov/myservice"

    def test_get_dataset_name_separates_prefix_and_name_with_single_slash(self):
        organization = OrganizationFactory()
        form = InformationSystemResourceForm(organization=organization, url_parent=None)
        form.codename_prefix = "gov/"
        form.cleaned_data = {"name": "myservice"}

        assert form.get_dataset_name() == "gov/myservice"

    def test_codename_prefix_set_from_url_parent(self):
        organization = OrganizationFactory()
        url_parent = DatasetFactory(metadata=f"{organization.name}myparent")

        form = InformationSystemResourceForm(organization=organization, url_parent=url_parent)

        assert form.codename_prefix == url_parent.name

    def test_codename_prefix_set_from_instance_parent(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        parent_dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=False)
        child_dataset = DatasetFactory(organization=organization, subclass=subclass, is_public=False)
        child_dataset.move(parent_dataset, "sorted-child")
        child_dataset.refresh_from_db()

        form = InformationSystemResourceForm(organization=organization, url_parent=None, instance=child_dataset)

        assert form.codename_prefix == parent_dataset.name

    def test_codename_preview_initial_for_create_form(self):
        organization = OrganizationFactory()

        form = InformationSystemResourceForm(organization=organization, url_parent=None)

        assert form.initial["codename_preview"] == organization.name

    def test_codename_preview_initial_for_update_form(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization, metadata=f"{organization.name}myservice")

        form = InformationSystemResourceForm(organization=organization, url_parent=None, instance=dataset)

        assert form.initial["codename_preview"] == dataset.name


class TestInformationSystemResourceForm:
    def test_both_rights_fields_raises_error(self):
        organization = OrganizationFactory()

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
        )

        assert language_concept in form.fields["languages"].queryset
        assert other_concept not in form.fields["languages"].queryset

    def test_languages_not_required(self):
        organization = OrganizationFactory()
        importance_schema = ConceptSchema.objects.get(uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI)
        importance = ConceptFactory(concept_schemas=[importance_schema])

        form = InformationSystemResourceForm(
            organization=organization,
            url_parent=None,
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

    def test_dynamic_help_text_applied(self):
        organization = OrganizationFactory()
        FormFieldTextFactory(
            form_name=FormFieldText.DCAT_INFORMATION_SYSTEM,
            field_name="identifier",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = InformationSystemResourceForm(organization=organization, url_parent=None)

        assert form.fields["identifier"].help_text == "Dinaminis tekstas"


class TestServiceResourceForm:
    def test_follows_license_service_quality_not_required(self):
        organization = OrganizationFactory()
        contact = ContactFactory(organization=organization)

        form = ServiceResourceForm(
            organization=organization,
            url_parent=None,
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

    def test_organization_required(self):
        organization = OrganizationFactory()

        form = ServiceResourceForm(
            organization=organization,
            url_parent=None,
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

    def test_dynamic_help_text_applied(self):
        organization = OrganizationFactory()
        FormFieldTextFactory(
            form_name=FormFieldText.DCAT_SERVICE,
            field_name="endpoint_url",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = ServiceResourceForm(organization=organization, url_parent=None)

        assert form.fields["endpoint_url"].help_text == "Dinaminis tekstas"


class TestDatasetResourceForm:
    def test_temporal_start_after_end_raises_error(self):
        organization = OrganizationFactory()

        form = DatasetResourceForm(
            organization=organization,
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
            data={"qualified_relation": ["not-a-url"]},
        )

        assert not form.is_valid()
        assert "qualified_relation" in form.errors

    def test_documentation_initial_empty_when_no_instance(self):
        organization = OrganizationFactory()

        form = DatasetResourceForm(
            organization=organization,
            url_parent=None,
        )

        assert "documentation" not in form.initial

    def test_conforms_to_queryset_filtered_to_dataset_standard(self):
        organization = OrganizationFactory()
        dataset_standard_schema, _ = ConceptSchema.objects.get_or_create(uri=DATASET_STANDARD_URI)
        matching_concept = ConceptFactory(concept_schemas=[dataset_standard_schema])
        other_concept = ConceptFactory()

        form = DatasetResourceForm(
            organization=organization,
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
        )

        assert matching_concept in form.fields["dataset_type"].queryset
        assert other_concept not in form.fields["dataset_type"].queryset

    def test_organization_required(self):
        organization = OrganizationFactory()

        form = DatasetResourceForm(
            organization=organization,
            url_parent=None,
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
            url_parent=None,
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

    def test_dynamic_help_text_applied(self):
        organization = OrganizationFactory()
        FormFieldTextFactory(
            form_name=FormFieldText.DCAT_DATASET,
            field_name="documentation",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = DatasetResourceForm(organization=organization, url_parent=None)

        assert form.fields["documentation"].help_text == "Dinaminis tekstas"


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
            url_parent=None,
            instance=dataset,
        )

        assert form.fields["identifier"].initial == "5678"

    def test_identifier_initial_empty_when_no_identifier(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=subclass)

        form = InformationSystemUpdateForm(
            organization=organization,
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
            instance=dataset,
        )

        assert form.initial["applicable_legislation"] == []

    def test_dynamic_help_text_applied(self):
        organization = OrganizationFactory()
        FormFieldTextFactory(
            form_name=FormFieldText.DCAT_INFORMATION_SYSTEM,
            field_name="identifier",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = InformationSystemUpdateForm(organization=organization, url_parent=None)

        assert form.fields["identifier"].help_text == "Dinaminis tekstas"


class TestDatasetUpdateForm:
    def test_documentation_initial_set_from_instance(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        doc1 = DocumentationFactory(documentation_link="https://example.com/doc1")
        doc2 = DocumentationFactory(documentation_link="https://example.com/doc2")
        dataset.documentation.set([doc1, doc2])

        form = DatasetUpdateForm(
            organization=organization,
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
            instance=dataset,
        )

        assert form.initial["applicable_legislation"] == []

    def test_qualified_attribution_initial_set_from_contributor_attributions(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        contributor = AttributionFactory(name=Attribution.CONTRIBUTOR)
        org = OrganizationFactory()
        DatasetAttributionFactory(dataset=dataset, attribution=contributor, organization=org)

        form = DatasetRelationshipForm(dataset=dataset)

        assert org.pk in form.initial["qualified_attribution"]

    def test_qualified_attribution_initial_excludes_other_attribution_types(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        AttributionFactory(name=Attribution.CONTRIBUTOR)
        creator = AttributionFactory(name=Attribution.CREATOR)
        org = OrganizationFactory()
        DatasetAttributionFactory(dataset=dataset, attribution=creator, organization=org)

        form = DatasetRelationshipForm(dataset=dataset)

        assert org.pk not in form.initial["qualified_attribution"]

    def test_qualified_attribution_initial_empty_when_no_attributions(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        form = DatasetRelationshipForm(dataset=dataset)

        assert list(form.initial["qualified_attribution"]) == []

    def test_qualified_relation_initial_set_from_instance(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        DatasetQualifiedRelationFactory(dataset=dataset, url="https://example.com/rel1")
        DatasetQualifiedRelationFactory(dataset=dataset, url="https://example.com/rel2")

        form = DatasetUpdateForm(
            organization=organization,
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
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
            url_parent=None,
            instance=dataset,
        )

        assert form.initial["creator"] == first_da.organization_id

    def test_creator_initial_not_set_when_no_creator_attribution(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        form = DatasetUpdateForm(
            organization=organization,
            url_parent=None,
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
            url_parent=None,
            instance=dataset,
        )

        assert "creator" not in form.initial

    def test_dynamic_help_text_applied(self):
        organization = OrganizationFactory()
        FormFieldTextFactory(
            form_name=FormFieldText.DCAT_DATASET,
            field_name="documentation",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = DatasetUpdateForm(organization=organization, url_parent=None)

        assert form.fields["documentation"].help_text == "Dinaminis tekstas"


class TestServiceUpdateForm:
    def test_serves_datasets_initial_set_from_existing_relations(self):
        organization = OrganizationFactory()
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        dataset_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        service = DatasetFactory(organization=organization, subclass=service_subclass)
        served_dataset = DatasetFactory(organization=organization, subclass=dataset_subclass)
        relation = RelationFactory(name=Relation.SERVICE)
        DatasetRelationFactory(relation=relation, dataset=service, part_of=served_dataset)

        form = ServiceRelationshipForm(dataset=service)

        assert served_dataset in form.initial["serves_datasets"]

    def test_serves_datasets_initial_excludes_unrelated_datasets(self):
        organization = OrganizationFactory()
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        dataset_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        service = DatasetFactory(organization=organization, subclass=service_subclass)
        unrelated_dataset = DatasetFactory(organization=organization, subclass=dataset_subclass)

        form = ServiceRelationshipForm(dataset=service)

        assert unrelated_dataset not in form.initial["serves_datasets"]

    def test_serves_datasets_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        service = DatasetFactory(organization=organization, subclass=service_subclass)

        form = ServiceRelationshipForm(dataset=service)

        assert not form.initial["serves_datasets"].exists()

    def test_dynamic_help_text_applied(self):
        organization = OrganizationFactory()
        FormFieldTextFactory(
            form_name=FormFieldText.DCAT_SERVICE,
            field_name="endpoint_url",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = ServiceUpdateForm(organization=organization, url_parent=None)

        assert form.fields["endpoint_url"].help_text == "Dinaminis tekstas"


class TestInformationSystemUpdate:
    def test_has_part_initial_set_from_existing_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        catalog_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)
        catalog_dataset = DatasetFactory(organization=organization, subclass=catalog_subclass)
        relation = RelationFactory(name=Relation.CATALOG)
        DatasetRelationFactory(relation=relation, dataset=dataset, part_of=catalog_dataset)

        form = InformationSystemRelationshipForm(dataset=dataset)

        assert catalog_dataset in form.initial["has_part"]

    def test_has_part_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)

        form = InformationSystemRelationshipForm(dataset=dataset)

        assert not form.initial["has_part"].exists()

    def test_relates_to_information_system_initial_set_from_existing_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)
        other_is = DatasetFactory(organization=organization, subclass=is_subclass)
        relation = RelationFactory(name=Relation.RELATES_TO_INFORMATION_SYSTEM)
        DatasetRelationFactory(relation=relation, dataset=other_is, part_of=dataset)

        form = InformationSystemRelationshipForm(dataset=dataset)

        assert other_is in form.initial["relates_to_information_system"]

    def test_relates_to_information_system_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)

        form = InformationSystemRelationshipForm(dataset=dataset)

        assert not form.initial["relates_to_information_system"].exists()

    def test_related_information_system_initial_set_from_existing_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)
        other_is = DatasetFactory(organization=organization, subclass=is_subclass)
        relation = RelationFactory(name=Relation.RELATES_TO_INFORMATION_SYSTEM)
        DatasetRelationFactory(relation=relation, dataset=dataset, part_of=other_is)

        form = InformationSystemRelationshipForm(dataset=dataset)

        assert other_is in form.initial["related_information_system"]

    def test_related_information_system_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)

        form = InformationSystemRelationshipForm(dataset=dataset)

        assert not form.initial["related_information_system"].exists()

    def test_relates_to_data_service_initial_set_from_existing_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)
        service = DatasetFactory(organization=organization, subclass=service_subclass)
        relation = Relation.objects.get(name=Relation.RELATES_TO_DATA_SERVICE)
        DatasetRelationFactory(relation=relation, dataset=dataset, part_of=service)

        form = InformationSystemRelationshipForm(dataset=dataset)

        assert service in form.initial["relates_to_data_service"]

    def test_relates_to_data_service_initial_empty_when_no_relations(self):
        organization = OrganizationFactory()
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.INFORMATION_SYSTEM)
        dataset = DatasetFactory(organization=organization, subclass=is_subclass)

        form = InformationSystemRelationshipForm(dataset=dataset)

        assert not form.initial["relates_to_data_service"].exists()


class TestISPublicServiceResourceForm:
    def test_identifier_is_required(self):
        organization = OrganizationFactory()

        form = ISPublicServiceResourceForm(organization=organization, url_parent=None)

        assert form.fields["identifier"].required is True

    def test_information_system_publishers_is_required(self):
        organization = OrganizationFactory()

        form = ISPublicServiceResourceForm(organization=organization, url_parent=None)

        assert form.fields["information_system_publishers"].required is True

    def test_landing_page_is_required(self):
        organization = OrganizationFactory()

        form = ISPublicServiceResourceForm(organization=organization, url_parent=None)

        assert form.fields["landing_page"].required is True

    def test_is_public_service_status_queryset_filtered_to_adms_scheme(self):
        organization = OrganizationFactory()
        adms_schema = ConceptSchema.objects.get_or_create(uri=Dataset.IS_PUBLIC_SERVICE_STATUS_SCHEME_URI)[0]
        adms_concept = ConceptFactory(concept_schemas=[adms_schema])
        other_concept = ConceptFactory()

        form = ISPublicServiceResourceForm(organization=organization, url_parent=None)

        assert adms_concept in form.fields["is_public_service_status"].queryset
        assert other_concept not in form.fields["is_public_service_status"].queryset

    def test_service_type_queryset_filtered_to_service_type_scheme(self):
        organization = OrganizationFactory()
        service_type_schema = ConceptSchema.objects.get_or_create(uri=Dataset.SERVICE_TYPE_SCHEME_URI)[0]
        service_type_concept = ConceptFactory(concept_schemas=[service_type_schema])
        other_concept = ConceptFactory()

        form = ISPublicServiceResourceForm(organization=organization, url_parent=None)

        assert service_type_concept in form.fields["service_type"].queryset
        assert other_concept not in form.fields["service_type"].queryset

    def test_get_dataset_name_combines_parent_name_and_identifier(self):
        organization = OrganizationFactory()
        parent = DatasetFactory(metadata="gov/ivpk/is_name")

        form = ISPublicServiceResourceForm(organization=organization, url_parent=parent)
        form.cleaned_data = {"identifier": "paslauga"}

        assert form.get_dataset_name() == "gov/ivpk/is_name/paslauga"

    def test_get_dataset_name_strips_trailing_slash_from_parent_name(self):
        organization = OrganizationFactory()
        parent = DatasetFactory(metadata="gov/ivpk/is_name/")

        form = ISPublicServiceResourceForm(organization=organization, url_parent=parent)
        form.cleaned_data = {"identifier": "paslauga"}

        assert form.get_dataset_name() == "gov/ivpk/is_name/paslauga"


class TestISPublicServiceUpdateForm:
    def test_identifier_initial_set_from_pasis_identifier(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.IS_PUBLIC_SERVICE)
        dataset = DatasetFactory(organization=organization, subclass=subclass)
        agency, _ = Agency.objects.get_or_create(
            code=Agency.PASIS_CODE,
            defaults={
                "name": "Paslaugų ir gaminių informacinė sistema",
                "uri": "https://www.pasis.lt",
                "identifier_validation_type": None,
            },
        )
        Identifier.objects.create(
            resource=dataset,
            scheme_agency=agency,
            notation="paslauga_1",
            identifier_type=Identifier.IdentifierType.OTHER,
        )

        form = ISPublicServiceUpdateForm(
            organization=organization,
            url_parent=None,
            instance=dataset,
        )

        assert form.fields["identifier"].initial == "paslauga_1"

    def test_identifier_initial_empty_when_no_pasis_identifier(self):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.IS_PUBLIC_SERVICE)
        dataset = DatasetFactory(organization=organization, subclass=subclass)

        form = ISPublicServiceUpdateForm(
            organization=organization,
            url_parent=None,
            instance=dataset,
        )

        assert form.fields["identifier"].initial == ""


class TestISPublicServiceRelationshipForm:
    def test_produces_datasets_queryset_only_includes_dataset_subclass(self):
        dataset_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.IS_PUBLIC_SERVICE)
        matching = DatasetFactory(subclass=dataset_subclass)
        excluded_service = DatasetFactory(subclass=service_subclass)
        dataset = DatasetFactory(subclass=is_subclass)

        form = ISPublicServiceRelationshipForm(dataset=dataset)

        assert matching in form.fields["produces_datasets"].queryset
        assert excluded_service not in form.fields["produces_datasets"].queryset

    def test_produces_services_queryset_only_includes_service_subclass(self):
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        dataset_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.IS_PUBLIC_SERVICE)
        matching = DatasetFactory(subclass=service_subclass)
        excluded_dataset = DatasetFactory(subclass=dataset_subclass)
        dataset = DatasetFactory(subclass=is_subclass)

        form = ISPublicServiceRelationshipForm(dataset=dataset)

        assert matching in form.fields["produces_services"].queryset
        assert excluded_dataset not in form.fields["produces_services"].queryset

    def test_produces_catalogs_queryset_only_includes_catalog_subclass(self):
        catalog_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)
        dataset_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.IS_PUBLIC_SERVICE)
        matching = DatasetFactory(subclass=catalog_subclass)
        excluded_dataset = DatasetFactory(subclass=dataset_subclass)
        dataset = DatasetFactory(subclass=is_subclass)

        form = ISPublicServiceRelationshipForm(dataset=dataset)

        assert matching in form.fields["produces_catalogs"].queryset
        assert excluded_dataset not in form.fields["produces_catalogs"].queryset

    def test_initial_set_from_existing_produces_relations(self):
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.IS_PUBLIC_SERVICE)
        dataset_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)
        service_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.SERVICE)
        catalog_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)
        dataset = DatasetFactory(subclass=is_subclass)
        produced_dataset = DatasetFactory(subclass=dataset_subclass)
        produced_service = DatasetFactory(subclass=service_subclass)
        produced_catalog = DatasetFactory(subclass=catalog_subclass)
        relation = RelationFactory(name=Relation.PRODUCES)
        DatasetRelationFactory(relation=relation, dataset=dataset, part_of=produced_dataset)
        DatasetRelationFactory(relation=relation, dataset=dataset, part_of=produced_service)
        DatasetRelationFactory(relation=relation, dataset=dataset, part_of=produced_catalog)

        form = ISPublicServiceRelationshipForm(dataset=dataset)

        assert produced_dataset in form.initial["produces_datasets"]
        assert produced_service in form.initial["produces_services"]
        assert produced_catalog in form.initial["produces_catalogs"]

    def test_initial_empty_when_no_produces_relations(self):
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.IS_PUBLIC_SERVICE)
        dataset = DatasetFactory(subclass=is_subclass)

        form = ISPublicServiceRelationshipForm(dataset=dataset)

        assert not form.initial["produces_datasets"].exists()
        assert not form.initial["produces_services"].exists()
        assert not form.initial["produces_catalogs"].exists()

    def test_initial_not_set_when_dataset_has_no_pk(self):
        is_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.IS_PUBLIC_SERVICE)
        dataset = DatasetFactory.build(subclass=is_subclass)

        form = ISPublicServiceRelationshipForm(dataset=dataset)

        assert "produces_datasets" not in form.initial
        assert "produces_services" not in form.initial
        assert "produces_catalogs" not in form.initial

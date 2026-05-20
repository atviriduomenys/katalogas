import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, resolve
from django_webtest import DjangoTestApp
from django.test import RequestFactory

from vitrina.classifiers.factories import ConceptSchemaFactory, ConceptFactory
from vitrina.classifiers.models import ConceptSchema, Concept
from vitrina.datasets.factories import DCATResourceSubclassFactory, DatasetFactory
from vitrina.datasets.forms import (
    InformationSystemResourceForm,
    ServiceResourceForm,
    ResourceSubclassForm,
    CatalogResourceForm,
    DatasetResourceForm,
)
from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization, Representative
from vitrina.users.factories import UserFactory
from vitrina.uapi.factories import AgentFactory
from vitrina.users.models import User
from vitrina.resources.models import Format

pytestmark = pytest.mark.django_db


class TestInformationSystemResourceForm:
    @pytest.mark.parametrize(
        "field_name, schema_uri_attr",
        [
            ("information_system_type", "INFORMATION_SYSTEM_TYPE_SCHEMA_URI"),
            ("information_system_importance", "INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI"),
        ],
    )
    def test_information_system_fields_only_allow_choices_from_correct_schema(
        self, app: DjangoTestApp, field_name, schema_uri_attr
    ) -> None:
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        subclass = DCATResourceSubclassFactory(name="information_system")

        schema_uri = getattr(Dataset, schema_uri_attr)

        concept_schema = ConceptSchema.objects.filter(uri=schema_uri).first()
        concept_schema2 = ConceptSchemaFactory(uri="foo")
        concept = ConceptFactory(concept_schemas=[concept_schema])
        wrong_schema_concept = ConceptFactory(concept_schemas=[concept_schema2])
        no_schema_concept = ConceptFactory(concept_schemas=[])

        form = app.get(
            reverse(
                "dataset-add",
                kwargs={"pk": organization.id, "subclass_uuid": subclass.pk},
            )
        ).context["form"]

        assert isinstance(form, InformationSystemResourceForm)
        queryset = set(form.fields[field_name].queryset)
        assert concept in queryset
        assert wrong_schema_concept not in queryset
        assert no_schema_concept not in queryset


class TestDatasetResourceForm:
    def test_temporal_start_date_must_be_lower_then_temporal_end_date(self, app: DjangoTestApp) -> None:
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        subclass = DCATResourceSubclassFactory(name="dataset")

        url = reverse(
            "dataset-add",
            kwargs={"pk": organization.id, "subclass_uuid": subclass.pk},
        )
        response = app.post(
            url,
            {
                "title": "Test Dataset",
                "temporal_start": "2025-08-20",
                "temporal_end": "2025-08-10",
            },
        )

        assert response.status_code == 200

        form_in_context = response.context["form"]
        assert isinstance(form_in_context, DatasetResourceForm)
        assert (
            "Laikotarpio pradžios data negali būti vėlesnė nei pabaigos data."
            in form_in_context.errors["temporal_start"]
        )


class TestServiceResourceForm:
    def test_dataset_service_subclass_service_type_management(self, app: DjangoTestApp):
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        subclass = DCATResourceSubclassFactory(name="service")

        form = app.get(
            reverse(
                "dataset-add",
                kwargs={"pk": organization.id, "subclass_uuid": subclass.pk},
            )
        ).context["form"]
        concept1 = ConceptFactory()
        concept2 = ConceptFactory()
        concept3 = ConceptFactory()
        needed_concept_schema, _ = ConceptSchema.objects.get_or_create(
            uri="http://publications.europa.eu/resource/authority/data-service-type"
        )

        wrong_concept_schema, _ = ConceptSchema.objects.get_or_create(uri="dcataplt:Importance")

        concept1.concept_schemas.add(needed_concept_schema)
        concept2.concept_schemas.add(wrong_concept_schema)
        concept3.concept_schemas.add(needed_concept_schema)

        assert isinstance(form, ServiceResourceForm)
        form_queryset = set(form.fields["service_type"].queryset)
        assert concept1 in form_queryset
        assert concept3 in form_queryset
        assert concept2 not in form_queryset

    def test_correct_agents_appear_in_agent_selection(self, organization: Organization, user: User, rf: RequestFactory):
        request = rf.get("/")
        request.resolver_match = resolve("/")
        request.user = user
        form = ServiceResourceForm(request=request, organization=organization)

        valid_agent = AgentFactory(organization=organization)
        archived_agent = AgentFactory(organization=organization, is_archived=True)
        different_org_agent = AgentFactory()

        agents_queryset = form.fields["agent"].queryset

        assert len(agents_queryset) == 1
        assert valid_agent in agents_queryset
        assert archived_agent not in agents_queryset
        assert different_org_agent not in agents_queryset

    def test_endpoint_url_and_description_must_be_empty_when_agent_selected(
        self, organization: Organization, user: User, rf: RequestFactory
    ):
        request = rf.get("/")
        request.resolver_match = resolve("/")
        request.user = user
        agent = AgentFactory(organization=organization)

        data = {
            "agent": agent,
            "endpoint_url": "http://www.example.com",
            "endpoint_description": "http://www.example.com",
        }

        form = ServiceResourceForm(data=data, request=request, organization=organization)

        error_msg = "Pasirinkus agentą, šis laukas negali būti užpildytas."
        assert "endpoint_url" in form.errors
        assert "endpoint_description" in form.errors

        assert error_msg in form.errors["endpoint_url"]
        assert error_msg in form.errors["endpoint_description"]

    def test_conforms_to_must_be_uapi_when_agent_selected(
        self, organization: Organization, user: User, rf: RequestFactory
    ):
        request = rf.get("/")
        request.resolver_match = resolve("/")
        request.user = user
        agent = AgentFactory(organization=organization)
        concepts_schema = ConceptSchema.objects.get(uri="https://data.gov.lt/id/non-standard/DataServiceStandard")
        concept = Concept.objects.create(code="test", valid_since="2000-01-01")
        concept.concept_schemas.add(concepts_schema)

        data = {
            "agent": agent,
            "conforms_to": concept,
        }

        form = ServiceResourceForm(data=data, request=request, organization=organization)

        assert "conforms_to" in form.errors
        assert "Su agentu susietos paslaugos privalo atitikti UDTS standartą." in form.errors["conforms_to"]

    def test_wrong_endpoint_type_and_description_type_when_agent_selected(
        self, organization: Organization, user: User, rf: RequestFactory
    ):
        request = rf.get("/")
        request.resolver_match = resolve("/")
        request.user = user
        agent = AgentFactory(organization=organization)
        wrong_format = Format.objects.get(title="API")

        data = {
            "agent": agent,
            "endpoint_type": wrong_format,
            "endpoint_description_type": wrong_format,
        }

        form = ServiceResourceForm(data=data, request=request, organization=organization)

        assert "endpoint_type" in form.errors
        assert "endpoint_description_type" in form.errors
        assert "Pasirinkus agentą, API formatas privalo būti 'JSON'" in form.errors["endpoint_type"]
        assert (
            "Pasirinkus agentą, API specifikacijos formatas privalo būti 'OpenAPI'"
            in form.errors["endpoint_description_type"]
        )

    def test_agent_must_be_selected_if_conforms_to_is_uapi(
        self, organization: Organization, user: User, rf: RequestFactory
    ):
        request = rf.get("/")
        request.resolver_match = resolve("/")
        request.user = user

        data = {
            "conforms_to": Concept.objects.get(code="UAPI"),
        }

        form = ServiceResourceForm(data=data, request=request, organization=organization)

        assert "agent" in form.errors
        assert (
            "UDTS standartą atitinkančios paslaugos privalo būti susietos su agentu. Pasirinkite agentą arba pasirinkite kitą 'Atitinka' lauko reikšmę."
            in form.errors["agent"]
        )

    def test_related_fields_auto_filled_if_agent_selected(
        self, organization: Organization, user: User, rf: RequestFactory
    ):
        request = rf.get("/")
        request.resolver_match = resolve("/")
        request.user = user
        agent = AgentFactory(organization=organization)

        data = {
            "agent": agent,
        }

        form = ServiceResourceForm(data=data, request=request, organization=organization)

        assert not form.is_valid()
        form_cleaned_data = form.cleaned_data
        form_cleaned_data["endpoint_type"] == Format.objects.get(title="JSON")
        form_cleaned_data["endpoint_description_type"] == Format.objects.get(title="OpenAPI")
        form_cleaned_data["conforms_to"] == Concept.objects.get(code="UAPI")


class TestCatalogResourceForm:
    def test_create_catalog_with_conditions_error(self, app: DjangoTestApp) -> None:
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        subclass = DCATResourceSubclassFactory(name="catalog")

        url = reverse(
            "dataset-add",
            kwargs={"pk": organization.id, "subclass_uuid": subclass.pk},
        )
        response = app.post(
            url,
            {
                "title": "Test Catalog",
                "conditions": "Conditions",
                "rights_relation": "https://example.com",
            },
        )

        assert response.status_code == 200
        form_in_context = response.context["form"]
        assert isinstance(form_in_context, CatalogResourceForm)
        assert "Užpildykite tik vieną teisių deklaracijų lauką." in form_in_context.errors["conditions"]


class TestResourceSubclassForm:
    def test_information_system_excluded_if_user_open_data_representative(self, app: DjangoTestApp):
        organization = OrganizationFactory(kind=Organization.GOV)
        user = UserFactory()
        user.organization = organization
        user.save()

        RepresentativeFactory(
            organization=organization,
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )
        app.set_user(user)

        form = app.get(
            reverse(
                "resource-subclass-add",
                kwargs={"pk": organization.id},
            )
        ).context["form"]
        assert isinstance(form, ResourceSubclassForm)
        subclass_names = {s.name for s in form.fields["subclass"].queryset}
        assert DCATResourceSubclass.INFORMATION_SYSTEM not in subclass_names

    def test_resource_access_rights_non_public_confidential_excluded_if_user_open_data_representative(
        self, app: DjangoTestApp
    ):
        organization = OrganizationFactory()
        user = UserFactory()
        app.set_user(user)
        subclass = DCATResourceSubclassFactory(name="dataset")

        RepresentativeFactory(
            organization=organization,
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )
        app.set_user(user)

        form = app.get(
            reverse(
                "dataset-add",
                kwargs={"pk": organization.id, "subclass_uuid": subclass.pk},
            )
        ).context["form"]
        assert isinstance(form, DatasetResourceForm)

        choices = [value for value, label in form.fields["access_rights"].choices]

        assert Dataset.NON_PUBLIC not in choices
        assert Dataset.CONFIDENTIAL not in choices
        assert Dataset.PUBLIC in choices
        assert Dataset.RESTRICTED in choices

    def test_resource_access_rights_non_public_confidential_excluded_if_user_open_data_representative_for_parent_dataset(
        self, app: DjangoTestApp
    ):
        organization = OrganizationFactory()
        user = UserFactory()
        subclass = DCATResourceSubclassFactory(name="dataset")

        parent_dataset = DatasetFactory(organization=organization)

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(parent_dataset),
            object_id=parent_dataset.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )
        app.set_user(user)

        form = app.get(
            reverse(
                "child-dataset-add",
                kwargs={
                    "pk": organization.id,
                    "subclass_uuid": subclass.pk,
                    "parent_id": parent_dataset.pk,
                },
            )
        ).context["form"]
        assert isinstance(form, DatasetResourceForm)

        choices = [value for value, label in form.fields["access_rights"].choices]

        assert Dataset.NON_PUBLIC not in choices
        assert Dataset.CONFIDENTIAL not in choices
        assert Dataset.PUBLIC in choices
        assert Dataset.RESTRICTED in choices

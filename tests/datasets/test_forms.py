import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import ConceptSchemaFactory, ConceptFactory
from vitrina.classifiers.models import ConceptSchema
from vitrina.datasets.factories import DCATResourceSubclassFactory
from vitrina.datasets.forms import InformationSystemResourceForm, ServiceResourceForm
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.users.factories import UserFactory

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
        ConceptFactory(concept_schemas=[concept_schema2])
        ConceptFactory(concept_schemas=[])

        form = app.get(
            reverse(
                "dataset-add",
                kwargs={"pk": organization.id, "subclass_uuid": subclass.pk},
            )
        ).context["form"]

        assert isinstance(form, InformationSystemResourceForm)
        assert set(form.fields[field_name].queryset) == {concept}


class DatasetResourceForm:
    def test_temporal_start_date_must_be_lower_then_temporal_end_date(self, app: DjangoTestApp) -> None:
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        subclass = DCATResourceSubclassFactory(name="dataset")

        form = app.get(
            reverse(
                "dataset-add",
                kwargs={"pk": organization.id, "subclass_uuid": subclass.pk},
            )
        ).context["form"]

        form["temporal_start"] = "2025-08-20"
        form["temporal_end"] = "2025-08-10"

        response = form.submit()

        assert isinstance(form, DatasetResourceForm)
        assert response.status_code == 200
        form_in_context = response.context["form"]
        assert "Laikotarpio pradžios data negali būti vėlesnė nei pabaigos data." in form_in_context.errors


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

        wrong_concept_schema, _ = ConceptSchema.objects.get_or_create(
            uri="dcataplt:Importance"
        )

        concept1.concept_schemas.add(needed_concept_schema)
        concept2.concept_schemas.add(wrong_concept_schema)
        concept3.concept_schemas.add(needed_concept_schema)

        assert isinstance(form, ServiceResourceForm)
        assert len(form.fields['service_type'].queryset) == 2


class CatalogResourceForm:
    def test_create_catalog_with_conditions_error(self, app: DjangoTestApp) -> None:
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        subclass = DCATResourceSubclassFactory(name="catalog")

        form = app.get(
            reverse(
                "dataset-add",
                kwargs={"pk": organization.id, "subclass_uuid": subclass.pk},
            )
        ).context["form"]

        form["conditions"] = "Conditions"
        form["rights_relation"] = "https://example.com"

        response = form.submit()

        assert isinstance(form, CatalogResourceForm)
        assert response.status_code == 200
        form_in_context = response.context["form"]
        assert "Užpildykite tik vieną teisių deklaracijų lauką." in form_in_context.errors


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

        wrong_concept_schema, _ = ConceptSchema.objects.get_or_create(
            uri="dcataplt:Importance"
        )

        concept1.concept_schemas.add(needed_concept_schema)
        concept2.concept_schemas.add(wrong_concept_schema)
        concept3.concept_schemas.add(needed_concept_schema)

        form_fields = list(form.fields['service_type'].queryset)
        assert isinstance(form, ServiceResourceForm)
        assert concept1 in form_fields
        assert concept3 in form_fields
        assert concept2 not in form_fields


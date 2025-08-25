import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import ConceptSchemaFactory, ConceptFactory
from vitrina.datasets.factories import DCATResourceSubclassFactory
from vitrina.datasets.forms import InformationSystemResourceForm
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

        concept_schema = ConceptSchemaFactory(uri=schema_uri)
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
    def test_temporal_start_date_must_be_lower_then_temporal_end_date(
        self, app: DjangoTestApp
    ) -> None:
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


class CatalogResourceForm:
    def test_create_catalog_with_conditions(self, app: DjangoTestApp) -> None:
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
        assert form.cleaned_data["conditions"] == "Conditions"
        assert form.cleaned_data["rights_relation"] == "https://example.com"

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
            ("information_system_type", "information_system_type_schema_uri"),
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

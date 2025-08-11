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
    def test_information_system_type_only_allows_choices_from_information_system_type_schema_uri(
        self, app: DjangoTestApp
    ) -> None:
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        subclass = DCATResourceSubclassFactory(name="information_system")

        concept_schema = ConceptSchemaFactory(
            uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
        )
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
        assert set(form.fields["information_system_type"].queryset) == {concept}

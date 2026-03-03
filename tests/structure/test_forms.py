import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.structure.factories import (
    VersionFactory,
    ModelFactory,
    MetadataFactory,
    PropertyFactory,
    EnumFactory,
    EnumItemFactory,
)
from vitrina.structure.models import Property, Metadata, Model
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def model() -> Model:
    version = VersionFactory()
    model = ModelFactory(dataset=version.dataset, metadata_version=version)
    dataset = version.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset",
        metadata_version=version,
    )

    return model


@pytest.fixture
def string_property(model: Model) -> Property:
    prop = PropertyFactory(model=model, metadata_version=model.metadata_version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=model.dataset,
        name="prop",
        type="string",
        metadata_version=model.metadata_version,
    )

    return prop


@pytest.fixture
def integer_property(model: Model) -> Property:
    prop = PropertyFactory(model=model, metadata_version=model.metadata_version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=model.dataset,
        name="prop",
        type="integer",
        metadata_version=model.metadata_version,
    )

    return prop


class TestEnumForm:
    @pytest.mark.parametrize(
        "given_value, saved_value",
        [
            ("First", '"First"'),
            ("'First'", "'First'"),
            ('"First"', '"First"'),
        ],
    )
    def test_creating_string_enum_automatically_adds_quotes_if_not_quoted(
        self, app: DjangoTestApp, string_property: Property, given_value: str, saved_value: str
    ):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        version = string_property.metadata_version
        model = string_property.model
        dataset = model.dataset

        enum = EnumFactory(
            content_type=ContentType.objects.get_for_model(string_property),
            object_id=string_property.pk,
            metadata_version=version,
        )

        form = app.get(reverse("enum-create", args=[dataset.pk, version.pk, model.name, string_property.name])).forms[
            "enum-form"
        ]
        form["value"] = given_value
        form["source"] = "TEST"
        form["access"] = Metadata.OPEN
        form["title"] = "Test value"
        form["description"] = "For testing"
        resp = form.submit()

        assert resp.url == string_property.get_absolute_url()
        enum_item_metadata = enum.enumitem_set.all().first().metadata.first()
        assert enum_item_metadata.prepare == saved_value

    def test_cannot_create_enum_item_if_value_already_exists(self, app: DjangoTestApp, string_property: Property):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        version = string_property.metadata_version
        model = string_property.model
        dataset = model.dataset

        enum = EnumFactory(
            content_type=ContentType.objects.get_for_model(string_property),
            object_id=string_property.pk,
            metadata_version=version,
        )
        enum_item = EnumItemFactory(enum=enum, metadata_version=version)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(enum_item),
            object_id=enum_item.pk,
            dataset=dataset,
            title="Test value",
            description="For testing",
            prepare='"First"',
            access=Metadata.OPEN,
            source="TEST",
            metadata_version=version,
        )

        form = app.get(reverse("enum-create", args=[dataset.pk, version.pk, model.name, string_property.name])).forms[
            "enum-form"
        ]
        form["value"] = "First"
        form["source"] = "TEST"
        form["access"] = Metadata.OPEN
        form["title"] = "Test value"
        form["description"] = "For testing"
        resp = form.submit()

        form = resp.context["form"]
        assert not form.is_valid()
        assert form.errors == {"value": ['Galima reikšmė ""First"" jau egzistuoja.']}

    def test_cannot_update_enum_item_if_value_already_exists(self, app: DjangoTestApp, string_property: Property):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        version = string_property.metadata_version
        model = string_property.model
        dataset = model.dataset

        enum = EnumFactory(
            content_type=ContentType.objects.get_for_model(string_property),
            object_id=string_property.pk,
            metadata_version=version,
        )
        enum_item = EnumItemFactory(enum=enum, metadata_version=version)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(enum_item),
            object_id=enum_item.pk,
            dataset=dataset,
            title="Test value",
            description="For testing",
            prepare='"First"',
            access=Metadata.OPEN,
            source="TEST",
            metadata_version=version,
        )
        enum_item2 = EnumItemFactory(enum=enum, metadata_version=version)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(enum_item2),
            object_id=enum_item.pk,
            dataset=dataset,
            title="Test value",
            description="For testing",
            prepare='"Second"',
            access=Metadata.OPEN,
            source="TEST2",
            metadata_version=version,
        )

        form = app.get(
            reverse("enum-update", args=[dataset.pk, version.pk, model.name, string_property.name, enum_item2.pk])
        ).forms["enum-form"]
        form["value"] = "First"
        resp = form.submit()

        form = resp.context["form"]
        assert not form.is_valid()
        assert form.errors == {"value": ['Galima reikšmė ""First"" jau egzistuoja.']}

    def test_enum_item_value_unique_check_excludes_current_item(self, app: DjangoTestApp, string_property: Property):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        version = string_property.metadata_version
        model = string_property.model
        dataset = model.dataset

        enum = EnumFactory(
            content_type=ContentType.objects.get_for_model(string_property),
            object_id=string_property.pk,
            metadata_version=version,
        )
        enum_item = EnumItemFactory(enum=enum, metadata_version=version)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(enum_item),
            object_id=enum_item.pk,
            dataset=dataset,
            title="Test value",
            description="For testing",
            prepare='"First"',
            access=Metadata.OPEN,
            source="TEST",
            metadata_version=version,
        )

        form = app.get(
            reverse("enum-update", args=[dataset.pk, version.pk, model.name, string_property.name, enum_item.pk])
        ).forms["enum-form"]
        form["value"] = "First2"
        resp = form.submit()

        assert resp.url == string_property.get_absolute_url()

    @pytest.mark.parametrize("non_integer_value", ["abc", '"First"', "1.33", "1.0", 1.1])
    def test_cannot_save_non_integer_item_values_for_integer_enum(
        self, app: DjangoTestApp, integer_property: Property, non_integer_value: str | float
    ):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        version = integer_property.metadata_version
        model = integer_property.model
        dataset = model.dataset

        form = app.get(reverse("enum-create", args=[dataset.pk, version.pk, model.name, integer_property.name])).forms[
            "enum-form"
        ]
        form["value"] = non_integer_value
        form["source"] = "TEST"
        form["access"] = Metadata.OPEN
        form["title"] = "Test value"
        form["description"] = "For testing"

        resp = form.submit()

        form = resp.context["form"]
        assert not form.is_valid()
        assert form.errors == {"value": [f'Reikšmė "{non_integer_value}" turi būti integer tipo.']}

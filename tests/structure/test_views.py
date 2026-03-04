import datetime
import json
import uuid
from http import HTTPStatus

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from unittest.mock import Mock, patch

from factory.django import FileField
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer
from pygments.lexers.special import TextLexer
from pygments.styles import get_style_by_name
from reversion.models import Version

from vitrina.classifiers.models import Status
from vitrina.cms.factories import FilerFileFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetStructureFactory, DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import RepresentativeFactory, OrganizationFactory
from vitrina.orgs.models import Representative, Organization
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure import VersionStatus
from vitrina.structure.factories import (
    ModelFactory,
    MetadataFactory,
    PropertyFactory,
    EnumFactory,
    EnumItemFactory,
    PrefixFactory,
    ParamItemFactory,
    ParamFactory,
    BaseFactory,
    VersionFactory,
)
from vitrina.structure.models import Metadata, Enum, EnumItem, VersionType, Model, Property, Base
from vitrina.structure.services import create_structure_objects
from vitrina.users.factories import UserFactory
from vitrina.structure.models import Version as _Version
from vitrina.utils import RevisionComment, RevisionSource


class BaseTestCreateManifest:
    def _create_manifest(self, manifest: str, title: str = "", description: str = ""):
        dataset = DatasetFactory(
            title=title,
            description=description,
            metadata=False,
        )
        structure = DatasetStructureFactory(
            file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)), dataset=dataset
        )
        structure.dataset.current_structure = structure
        structure.dataset.save()
        create_structure_objects(structure)
        dataset.refresh_from_db()
        return dataset


@pytest.mark.django_db
def test_model_data(app: DjangoTestApp):
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
    prop_1 = PropertyFactory(model=model, metadata_version=version)
    prop_2 = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name="prop_1",
        type="string",
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name="prop_2",
        type="integer",
        metadata_version=version,
    )
    data = {
        "_data": [
            {"_id": "c7d66fa2-a880-443d-8ab5-2ab7f9c79886", "prop_1": "test 1", "prop_2": 1},
            {"_id": "5bfd5a54-0ded-4803-9363-349f6e1b4523", "prop_1": "test 2", "prop_2": 2},
        ]
    }
    resp = app.post(reverse("model-data-table", args=[dataset.pk, version.pk, model.name]), {"data": json.dumps(data)})
    assert resp.context["headers"] == ["_id", "prop_1", "prop_2"]
    assert resp.context["properties"] == {"prop_1": prop_1, "prop_2": prop_2}
    assert resp.context["tags"] == []
    assert resp.context["select"] == "select(*)"
    assert resp.context["selected_cols"] == ["_id", "prop_1", "prop_2"]


@pytest.mark.django_db
def test_model_data_select(app: DjangoTestApp):
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
    prop_1 = PropertyFactory(model=model, metadata_version=version)
    prop_2 = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name="prop_1",
        type="string",
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name="prop_2",
        type="integer",
        metadata_version=version,
    )

    data = {"_data": [{"prop_1": "test 1"}, {"prop_1": "test 2"}]}
    resp = app.post(
        reverse("model-data-table", args=[dataset.pk, version.pk, model.name]),
        {
            "data": json.dumps(data),
            "query": "?select(prop_1)",
        },
    )
    assert resp.context["headers"] == ["prop_1"]
    assert resp.context["tags"] == []
    assert resp.context["select"] == "select(prop_1)"
    assert resp.context["selected_cols"] == ["prop_1"]


@pytest.mark.django_db
def test_model_data_sort(app: DjangoTestApp):
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
    prop_1 = PropertyFactory(model=model, metadata_version=version)
    prop_2 = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name="prop_1",
        type="string",
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name="prop_2",
        type="integer",
        metadata_version=version,
    )

    data = {
        "_data": [
            {"prop_1": "test 2"},
            {"prop_1": "test 1"},
        ]
    }
    resp = app.post(
        reverse("model-data-table", args=[dataset.pk, version.pk, model.name]),
        {
            "data": json.dumps(data),
            "query": "?select(prop_1)&sort(-prop_1)",
        },
    )
    assert resp.context["headers"] == ["prop_1"]
    assert resp.context["tags"] == ["sort(-prop_1)"]
    assert resp.context["select"] == "select(prop_1)"
    assert resp.context["selected_cols"] == ["prop_1"]


@pytest.mark.django_db
@pytest.mark.parametrize("operator", ["=", "<><=", ">="])
def test_model_data_with_compare_operators(app: DjangoTestApp, operator: str):
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
    prop_1 = PropertyFactory(model=model, metadata_version=version)
    prop_2 = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name="prop_1",
        type="string",
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name="prop_2",
        type="integer",
        metadata_version=version,
    )

    data = {
        "_data": [
            {"prop_2": 2},
        ]
    }
    resp = app.post(
        reverse("model-data-table", args=[dataset.pk, version.pk, model.name]),
        {
            "data": json.dumps(data),
            "query": f"?select(prop_2)&prop_2{operator}2",
        },
    )
    assert resp.context["headers"] == ["prop_2"]
    assert resp.context["tags"] == [f"prop_2{operator}2"]
    assert resp.context["select"] == "select(prop_2)"
    assert resp.context["selected_cols"] == ["prop_2"]


@pytest.mark.django_db
@pytest.mark.parametrize("operator", ["contains", "startswith", "endswith"])
def test_model_data_with_string_operators(app: DjangoTestApp, operator: str):
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
    prop_1 = PropertyFactory(model=model, metadata_version=version)
    prop_2 = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name="prop_1",
        type="string",
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name="prop_2",
        type="integer",
        metadata_version=version,
    )

    data = {
        "_data": [
            {"prop_1": "test 1"},
        ]
    }
    resp = app.post(
        reverse("model-data-table", args=[dataset.pk, version.pk, model.name]),
        {
            "data": json.dumps(data),
            "query": f"?select(prop_1)&{operator}('test')",
        },
    )
    assert resp.context["headers"] == ["prop_1"]
    assert resp.context["tags"] == [f"{operator}('test')"]
    assert resp.context["select"] == "select(prop_1)"
    assert resp.context["selected_cols"] == ["prop_1"]


def test_model_data_page_contains_correct_table_url(client):
    user = UserFactory(is_staff=True)
    client.force_login(user)

    dataset = DatasetFactory(metadata="test/dataset")
    dataset_metadata = Metadata.objects.get(object_id=dataset.pk, dataset=dataset)
    version = dataset_metadata.metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)

    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )

    resp = client.get(
        reverse(
            "model-data",
            kwargs={
                "pk": dataset.pk,
                "version_id": version.pk,
                "model": model.name,
            },
        )
    )

    assert resp.status_code == 200

    expected_url = reverse(
        "model-data-table",
        kwargs={
            "pk": dataset.pk,
            "version_id": version.pk,
            "model": model.name,
        },
    )

    assert expected_url in resp.content.decode()


@pytest.mark.django_db
def test_object_data(app: DjangoTestApp):
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
    prop_1 = PropertyFactory(model=model, metadata_version=version)
    prop_2 = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name="prop_1",
        type="string",
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name="prop_2",
        type="integer",
        metadata_version=version,
    )

    data = {"_id": "c7d66fa2-a880-443d-8ab5-2ab7f9c79886", "prop_1": "test 1", "prop_2": 1}
    resp = app.post(
        reverse("object-data-table", args=[dataset.pk, version.pk, model.name, "c7d66fa2-a880-443d-8ab5-2ab7f9c79886"]),
        {
            "data": json.dumps(data),
        },
    )
    assert resp.context["headers"] == ["_id", "prop_1", "prop_2"]
    assert resp.context["properties"] == {"prop_1": prop_1, "prop_2": prop_2}


@pytest.mark.django_db
def test_structure_tab_from_dataset_detail(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(dataset.get_absolute_url()).follow()
    resp = resp.click(linkid="structure_tab").follow()
    assert resp.request.path == reverse("dataset-structure", args=[dataset.pk, version.pk])


@pytest.mark.django_db
def test_structure_tab_from_model_structure(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(model.get_absolute_url())
    resp = resp.click(linkid="structure_tab")
    assert resp.request.path == reverse("dataset-structure", args=[dataset.pk, version.pk])


@pytest.mark.django_db
def test_structure_tab_from_property_structure(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(prop.get_absolute_url())
    resp = resp.click(linkid="structure_tab")
    assert resp.request.path == reverse("dataset-structure", args=[dataset.pk, version.pk])


@pytest.mark.django_db
def test_structure_tab_from_model_data(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(model.get_data_url())
    resp = resp.click(linkid="structure_tab")
    assert resp.request.path == model.get_absolute_url()


@pytest.mark.skip(reason="Not sure if test is correct")
@pytest.mark.django_db
def test_data_tab_from_dataset_detail(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(dataset.get_absolute_url())

    resp = resp.click(linkid="data_tab")
    assert resp.request.path == model.get_data_url()


@pytest.mark.django_db
def test_data_tab_from_dataset_structure(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(reverse("dataset-structure", args=[dataset.pk, version.pk]))
    resp = resp.click(linkid="data_tab")
    assert resp.request.path == model.get_data_url()


@pytest.mark.parametrize("structure_view", ["dataset-structure", "dataset-structure-history"])
@pytest.mark.django_db
def test_history_tab_from_dataset_structure(app: DjangoTestApp, structure_view: str):
    user = UserFactory(is_staff=True)
    app.set_user(user)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(reverse(structure_view, args=[dataset.pk, version.pk]))
    view = resp.context["view"]

    history_url = view.get_history_url()
    resp = resp.click(linkid="history-tab")
    assert resp.request.path == history_url


@pytest.mark.django_db
def test_history_tab_from_model_history(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(reverse("model-history", args=[dataset.pk, version.pk, "TestModel"]))
    view = resp.context["view"]

    history_url = view.get_history_url()
    resp = resp.click(linkid="history-tab")
    assert resp.request.path == history_url


@pytest.mark.django_db
def test_history_tab_from_property_history(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(reverse("property-history", args=[dataset.pk, version.pk, "TestModel", "prop"]))
    view = resp.context["view"]

    history_url = view.get_history_url()
    resp = resp.click(linkid="history-tab")
    assert resp.request.path == history_url


@pytest.mark.django_db
def test_data_tab_from_model_structure(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(model.get_absolute_url())
    resp = resp.click(linkid="data_tab")
    assert resp.request.path == model.get_data_url()


@pytest.mark.django_db
def test_data_tab_from_property_structure(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(prop.get_absolute_url())
    resp = resp.click(linkid="data_tab")
    assert resp.request.path == model.get_data_url()


@pytest.mark.django_db
def test_data_tab_from_object_data(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(reverse("object-data", args=[dataset.pk, version.pk, model.name, str(uuid.uuid4())]))
    resp = resp.click(linkid="data_tab")
    assert resp.request.path == model.get_data_url()


@pytest.mark.django_db
def test_private_model(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,,dct:title,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,private,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk, version.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == ["datasets/gov/ivpk/adp/Country"]

    resp = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "City"]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_private_model_with_access(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,private,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct, object_id=structure.dataset.pk, role=Representative.RESOURCE_MANAGER
    )
    app.set_user(representative.user)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk, version.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == [
        "datasets/gov/ivpk/adp/City",
        "datasets/gov/ivpk/adp/Country",
    ]

    resp = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "City"]))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_private_property(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    resp = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]))
    assert list(resp.context["props"].values_list("metadata__name", flat=True)) == ["id"]

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "title"]), expect_errors=True
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_private_property_with_access(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.pk,
    )
    app.set_user(representative.user)

    resp = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]))
    assert list(resp.context["props"].values_list("metadata__name", flat=True)) == ["id", "title"]

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "title"]), expect_errors=True
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_private_comment(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,,comment,type,,,,,,public,,,Public comment,,\n"
        ",,,,,,comment,type,,,,,,private,,,Private comment,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    resp = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]))
    assert sorted([comment.body for comment, _, _ in resp.context["comments"]]) == ["Public comment"]


@pytest.mark.django_db
def test_private_comment_with_access(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,\n"
        ",,,,,,comment,type,,,,public,,,,,Public comment,,\n"
        ",,,,,,comment,type,,,,private,,,,,Private comment,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.pk,
    )
    app.set_user(representative.user)

    resp = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]))
    assert sorted([comment.body for comment, _, _ in resp.context["comments"]]) == [
        "Private comment",
        "Public comment",
    ]


@pytest.mark.django_db
def test_getall(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    with patch("vitrina.structure.services.requests.get") as mock_get:
        data = {
            "_data": [
                {"_id": "c7d66fa2-a880-443d-8ab5-2ab7f9c79886", "prop_1": "test 1", "prop_2": 1},
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse("getall-api", args=[dataset.pk, version.pk, model.name]))
        assert resp.context["tabs"] == {
            "http": {
                "name": "HTTP",
                "query": highlight(f"{SPINTA_SERVER_URL}/test/dataset/TestModel", TextLexer(), HtmlFormatter()),
            },
            "httpie": {
                "name": "HTTPie",
                "query": highlight(
                    f'http GET "{SPINTA_SERVER_URL}/test/dataset/TestModel"', TextLexer(), HtmlFormatter()
                ),
            },
            "curl": {
                "name": "curl",
                "query": highlight(f'curl "{SPINTA_SERVER_URL}/test/dataset/TestModel"', TextLexer(), HtmlFormatter()),
            },
        }
        assert resp.context["response"] == highlight(
            json.dumps(
                {
                    "_data": [
                        {"_id": "c7d66fa2-a880-443d-8ab5-2ab7f9c79886", "prop_1": "test 1", "prop_2": 1},
                    ]
                },
                indent=2,
                ensure_ascii=False,
            ),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name("borland"), noclasses=True),
        )


@pytest.mark.django_db
def test_getall_with_query(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    with patch("vitrina.structure.services.requests.get") as mock_get:
        data = {
            "_data": [
                {"_id": "5bfd5a54-0ded-4803-9363-349f6e1b4523", "prop_2": 2},
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(
            "%s%s"
            % (reverse("getall-api", args=[dataset.pk, version.pk, model.name]), "?select(_id,prop_2)&sort(-prop2)")
        )
        assert resp.context["tabs"] == {
            "http": {
                "name": "HTTP",
                "query": highlight(
                    f"{SPINTA_SERVER_URL}/test/dataset/TestModel?select(_id,prop_2)&sort(-prop2)",
                    TextLexer(),
                    HtmlFormatter(),
                ),
            },
            "httpie": {
                "name": "HTTPie",
                "query": highlight(
                    f'http GET "{SPINTA_SERVER_URL}/test/dataset/TestModel?select(_id,prop_2)&sort(-prop2)"',
                    TextLexer(),
                    HtmlFormatter(),
                ),
            },
            "curl": {
                "name": "curl",
                "query": highlight(
                    f'curl "{SPINTA_SERVER_URL}/test/dataset/TestModel?select(_id,prop_2)&sort(-prop2)"',
                    TextLexer(),
                    HtmlFormatter(),
                ),
            },
        }
        assert resp.context["response"] == highlight(
            json.dumps(
                {
                    "_data": [
                        {"_id": "5bfd5a54-0ded-4803-9363-349f6e1b4523", "prop_2": 2},
                    ]
                },
                indent=2,
                ensure_ascii=False,
            ),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name("borland"), noclasses=True),
        )


@pytest.mark.django_db
def test_getone(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    with patch("vitrina.structure.services.requests.get") as mock_get:
        data = {"_id": "c7d66fa2-a880-443d-8ab5-2ab7f9c79886", "prop_1": "test 1", "prop_2": 1}
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(
            reverse("getone-api", args=[dataset.pk, version.pk, model.name, "c7d66fa2-a880-443d-8ab5-2ab7f9c79886"])
        )
        assert resp.context["tabs"] == {
            "http": {
                "name": "HTTP",
                "query": highlight(
                    f"{SPINTA_SERVER_URL}/test/dataset/TestModel/c7d66fa2-a880-443d-8ab5-2ab7f9c79886",
                    TextLexer(),
                    HtmlFormatter(),
                ),
            },
            "httpie": {
                "name": "HTTPie",
                "query": highlight(
                    f'http GET "{SPINTA_SERVER_URL}/test/dataset/TestModel/c7d66fa2-a880-443d-8ab5-2ab7f9c79886"',
                    TextLexer(),
                    HtmlFormatter(),
                ),
            },
            "curl": {
                "name": "curl",
                "query": highlight(
                    f'curl "{SPINTA_SERVER_URL}/test/dataset/TestModel/c7d66fa2-a880-443d-8ab5-2ab7f9c79886"',
                    TextLexer(),
                    HtmlFormatter(),
                ),
            },
        }
        assert resp.context["response"] == highlight(
            json.dumps(
                {"_id": "c7d66fa2-a880-443d-8ab5-2ab7f9c79886", "prop_1": "test 1", "prop_2": 1},
                indent=2,
                ensure_ascii=False,
            ),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name("borland"), noclasses=True),
        )


@pytest.mark.django_db
def test_changes(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    with patch("vitrina.structure.services.requests.get") as mock_get:
        data = {
            "_data": [{"_id": "c7d66fa2-a880-443d-8ab5-2ab7f9c79886", "_op": "insert", "prop_1": "test 1", "prop_2": 1}]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse("changes-api", args=[dataset.pk, version.pk, model.name]))
        assert resp.context["tabs"] == {
            "http": {
                "name": "HTTP",
                "query": highlight(
                    f"{SPINTA_SERVER_URL}/test/dataset/TestModel/:changes", TextLexer(), HtmlFormatter()
                ),
            },
            "httpie": {
                "name": "HTTPie",
                "query": highlight(
                    f'http GET "{SPINTA_SERVER_URL}/test/dataset/TestModel/:changes"', TextLexer(), HtmlFormatter()
                ),
            },
            "curl": {
                "name": "curl",
                "query": highlight(
                    f'curl "{SPINTA_SERVER_URL}/test/dataset/TestModel/:changes"', TextLexer(), HtmlFormatter()
                ),
            },
        }
        assert resp.context["response"] == highlight(
            json.dumps(
                {
                    "_data": [
                        {
                            "_id": "c7d66fa2-a880-443d-8ab5-2ab7f9c79886",
                            "_op": "insert",
                            "prop_1": "test 1",
                            "prop_2": 1,
                        },
                    ]
                },
                indent=2,
                ensure_ascii=False,
            ),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name("borland"), noclasses=True),
        )


@pytest.mark.django_db
def test_api_tab_from_model_data(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(reverse("model-data", args=[dataset.pk, version.pk, model.name]))
    resp = resp.click(linkid="api_tab")
    assert resp.request.path == model.get_api_url()


@pytest.mark.django_db
def test_api_tab_from_model_data_with_query(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get("%s%s" % (reverse("model-data", args=[dataset.pk, version.pk, model.name]), "?select(prop)"))
    resp = resp.click(linkid="api_tab")
    assert resp.request.path_qs == "%s%s" % (model.get_api_url(), "?select(prop)")


@pytest.mark.django_db
def test_api_tab_from_object_data(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    _id = str(uuid.uuid4())
    resp = app.get(reverse("object-data", args=[dataset.pk, version.pk, model.name, _id]))
    resp = resp.click(linkid="api_tab")
    assert resp.request.path == reverse("getone-api", args=[dataset.pk, version.pk, model.name, _id])


@pytest.mark.django_db
def test_data_tab_from_getone(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    _id = str(uuid.uuid4())
    resp = app.get(reverse("getone-api", args=[dataset.pk, version.pk, model.name, _id]))
    resp = resp.click(linkid="data_tab")
    assert resp.request.path == reverse("object-data", args=[dataset.pk, version.pk, model.name, _id])


@pytest.mark.django_db
def test_data_tab_from_getall(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get(reverse("getall-api", args=[dataset.pk, version.pk, model.name]))
    resp = resp.click(linkid="data_tab")
    assert resp.request.path == reverse("model-data", args=[dataset.pk, version.pk, model.name])


@pytest.mark.django_db
def test_data_tab_from_getall_with_query(app: DjangoTestApp):
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    resp = app.get("%s%s" % (reverse("getall-api", args=[dataset.pk, version.pk, model.name]), "?select(prop)"))
    resp = resp.click(linkid="data_tab")
    assert resp.request.path_qs == "%s%s" % (model.get_data_url(), "?select(prop)")


@pytest.mark.django_db
def test_property_enum_item_create__string(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("enum-create", args=[dataset.pk, version.pk, model.name, prop.name])).forms["enum-form"]
    form["value"] = "test"
    form["source"] = "TEST"
    form["access"] = Metadata.OPEN
    form["title"] = "Test value"
    form["description"] = "For testing"
    resp = form.submit()

    assert resp.url == prop.get_absolute_url()
    assert Enum.objects.filter(content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk).count() == 1
    assert list(
        EnumItem.objects.filter(
            enum__content_type=ContentType.objects.get_for_model(prop), enum__object_id=prop.pk
        ).values(
            "metadata_version_id",
            "metadata__prepare",
            "metadata__source",
            "metadata__access",
            "metadata__title",
            "metadata__description",
        )
    ) == [
        {
            "metadata_version_id": version.pk,
            "metadata__prepare": '"test"',
            "metadata__source": "TEST",
            "metadata__access": Metadata.OPEN,
            "metadata__title": "Test value",
            "metadata__description": "For testing",
        }
    ]


@pytest.mark.django_db
def test_property_enum_item_create__integer(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        metadata_version=version,
    )

    form = app.get(reverse("enum-create", args=[dataset.pk, version.pk, model.name, prop.name])).forms["enum-form"]
    form["value"] = 1
    form["source"] = "TEST"
    form["access"] = Metadata.OPEN
    form["title"] = "Test value"
    form["description"] = "For testing"
    resp = form.submit()

    assert resp.url == prop.get_absolute_url()
    assert Enum.objects.filter(content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk).count() == 1
    assert list(
        EnumItem.objects.filter(
            enum__content_type=ContentType.objects.get_for_model(prop), enum__object_id=prop.pk
        ).values(
            "metadata_version_id",
            "metadata__prepare",
            "metadata__source",
            "metadata__access",
            "metadata__title",
            "metadata__description",
        )
    ) == [
        {
            "metadata_version_id": version.pk,
            "metadata__prepare": "1",
            "metadata__source": "TEST",
            "metadata__access": Metadata.OPEN,
            "metadata__title": "Test value",
            "metadata__description": "For testing",
        }
    ]
    assert Version.objects.get_for_object(prop).count() == 1
    assert Version.objects.get_for_object(prop).first().revision.user == user


@pytest.mark.django_db
def test_property_enum_item_create__integer_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        metadata_version=version,
    )

    form = app.get(reverse("enum-create", args=[dataset.pk, version.pk, model.name, prop.name])).forms["enum-form"]
    form["value"] = "invalid"
    form["source"] = "TEST"
    form["access"] = Metadata.OPEN
    form["title"] = "Test value"
    form["description"] = "For testing"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [["Reikšmė turi būti integer tipo."]]


@pytest.mark.django_db
def test_property_enum_item_update(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        metadata_version=version,
    )

    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk, metadata_version=version
    )
    enum_item = EnumItemFactory(enum=enum, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title="Test value",
        description="For testing",
        prepare="1",
        access=Metadata.OPEN,
        source="TEST",
        metadata_version=version,
    )

    form = app.get(reverse("enum-update", args=[dataset.pk, version.pk, model.name, prop.name, enum_item.pk])).forms[
        "enum-form"
    ]
    form["access"] = Metadata.PUBLIC
    form["title"] = "Test value (updated)"
    resp = form.submit()

    assert resp.url == prop.get_absolute_url()
    assert Enum.objects.filter(content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk).count() == 1
    assert list(
        EnumItem.objects.filter(
            enum__content_type=ContentType.objects.get_for_model(prop), enum__object_id=prop.pk
        ).values(
            "metadata__prepare", "metadata__source", "metadata__access", "metadata__title", "metadata__description"
        )
    ) == [
        {
            "metadata__prepare": "1",
            "metadata__source": "TEST",
            "metadata__access": Metadata.PUBLIC,
            "metadata__title": "Test value (updated)",
            "metadata__description": "For testing",
        }
    ]
    assert Version.objects.get_for_object(prop).count() == 1
    assert Version.objects.get_for_object(prop).first().revision.user == user


@pytest.mark.django_db
def test_property_enum_item_delete(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        metadata_version=version,
    )

    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk, metadata_version=version
    )
    enum_item = EnumItemFactory(enum=enum, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title="Test value",
        description="For testing",
        prepare="1",
        access=Metadata.OPEN,
        source="TEST",
        metadata_version=version,
    )

    resp = app.post(reverse("enum-delete", args=[dataset.pk, version.pk, model.name, prop.name, enum_item.pk]))

    assert resp.url == prop.get_absolute_url()
    assert EnumItem.objects.filter(pk=enum_item.pk).count() == 0
    assert (
        Metadata.objects.filter(
            content_type=ContentType.objects.get_for_model(enum_item), object_id=enum_item.pk
        ).count()
        == 0
    )
    assert Version.objects.get_for_object(prop).count() == 1
    assert Version.objects.get_for_object(prop).first().revision.user == user


@pytest.mark.django_db
def test_property_enum_item_delete_in_pre_released_property(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    version = VersionFactory(status=VersionStatus.PRE_RELEASE)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        metadata_version=version,
    )

    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk, metadata_version=version
    )
    enum_item = EnumItemFactory(enum=enum, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title="Test value",
        description="For testing",
        prepare="1",
        access=Metadata.OPEN,
        source="TEST",
        metadata_version=version,
    )

    response = app.post(
        reverse("enum-delete", args=[dataset.pk, version.pk, model.name, prop.name, enum_item.pk]), expect_errors=True
    )

    assert response.status_code == 302
    assert response.location == prop.get_absolute_url()
    assert EnumItem.objects.filter(pk=enum_item.pk).count() == 1
    assert (
        Metadata.objects.filter(
            content_type=ContentType.objects.get_for_model(enum_item), object_id=enum_item.pk
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_model_create_with_lowercase_first_name_letter(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("model-create-no-version", args=[dataset.pk])).forms["model-form"]
    form["name"] = "invalidName"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Pirmas kodinio pavadinimo simbolis turi būti didžioji raidė."]
    ]


@pytest.mark.parametrize("status", [s for s in VersionStatus.values if s != VersionStatus.DRAFT])
@pytest.mark.django_db
def test_model_create_with_in_not_draft_version(app: DjangoTestApp, status: str):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory(status=status)
    dataset = version.dataset
    form = app.get(reverse("model-create", args=[dataset.pk, version.pk]), expect_errors=True)
    assert form.status_code == 302
    assert form.location == dataset.get_absolute_url()


@pytest.mark.django_db
def test_model_create_with_number_as_first_name_letter(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("model-create-no-version", args=[dataset.pk])).forms["model-form"]
    form["name"] = "1nvalidName"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Pirmas kodinio pavadinimo simbolis turi būti didžioji raidė."]
    ]


@pytest.mark.django_db
def test_model_create_with_special_symbol_in_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("model-create-no-version", args=[dataset.pk])).forms["model-form"]
    form["name"] = "Invalid_name1"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, jokie kiti simboliai negalimi."]
    ]


@pytest.mark.django_db
def test_model_create_with_invalid_prepare(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("model-create-no-version", args=[dataset.pk])).forms["model-form"]
    form["name"] = "Model"
    form["prepare"] = "sort(id)"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ['Duomenų filtre nurodytas modelyje neegzistuojantis laukas: "id".']
    ]


@pytest.mark.django_db
def test_model_create_with_invalid_uri(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("model-create-no-version", args=[dataset.pk])).forms["model-form"]
    form["name"] = "Model"
    form["uri"] = "dcat:invalid:format"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [['Nevalidus uri "dcat:invalid:format" formatas.']]


@pytest.mark.django_db
def test_model_create_with_invalid_uri_prefix(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("model-create-no-version", args=[dataset.pk])).forms["model-form"]
    form["name"] = "Model"
    form["uri"] = "dcat:invalid"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [['Neatpažintas "dcat" prefiksas.']]


@pytest.mark.django_db
def test_model_create(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    dataset = DatasetFactory(metadata="test/dataset")
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    PrefixFactory(name="dcat", metadata_version=version)

    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        uri="dcat:TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        metadata_version=version,
    )

    url = reverse("model-create", args=[dataset.pk, version.pk])
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="model-create",
        http_method="POST",
        path=url,
        args=(),
        kwargs={"pk": dataset.pk, "version_id": version.pk},
    )
    form = app.get(url).forms["model-form"]
    form["name"] = "Model"
    form["uri"] = "dcat:model"
    form["source"] = "MODEL"
    form["level"] = 3
    form["title"] = "Test model"
    form["description"] = "Model for testing"
    form["base"].force_value([model.pk])
    form["base_level"] = 4
    form["base_ref"].force_value([prop.pk])
    form["comment"] = "Added Model"
    resp = form.submit()

    new_model = dataset.model_set.exclude(pk=model.pk).first()
    assert resp.url == new_model.get_absolute_url()
    assert new_model.metadata.count() == 1
    assert new_model.metadata.first().name == "test/dataset/Model"
    assert new_model.metadata.first().uri == "dcat:model"
    assert new_model.metadata.first().source == "MODEL"
    assert new_model.metadata.first().level == 5
    assert new_model.metadata.first().level_given == 3
    assert new_model.metadata.first().title == "Test model"
    assert new_model.metadata.first().description == "Model for testing"
    assert new_model.metadata.first().metadata_version == version

    assert new_model.base.model == model
    assert new_model.base.property_list.count() == 1
    assert new_model.base.property_list.first().property == prop
    assert new_model.base.metadata.first().level == 5
    assert new_model.base.metadata.first().level_given == 4
    assert new_model.base.metadata.first().name == "test/dataset/TestModel"
    assert new_model.base.metadata.first().ref == "prop"
    assert new_model.base.metadata.first().metadata_version == version

    assert Version.objects.get_for_object(new_model).count() == 1
    version = Version.objects.get_for_object(new_model).select_related("revision").first()
    assert version.revision.comment == revision_comment.to_json()
    assert version.revision.user == user


@pytest.mark.django_db
def test_model_update(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    dataset = DatasetFactory(metadata="test/dataset")
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    PrefixFactory(name="dcat", metadata_version=version)

    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        uri="dcat:TestModel",
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset",
        metadata_version=version,
    )
    prop1 = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop1),
        object_id=prop1.pk,
        dataset=dataset,
        name="prop1",
        type="integer",
        metadata_version=version,
    )
    prop2 = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop2),
        object_id=prop2.pk,
        dataset=dataset,
        name="prop2",
        type="integer",
        metadata_version=version,
    )

    base_model = ModelFactory(dataset=dataset, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(base_model),
        object_id=base_model.pk,
        dataset=dataset,
        name="test/dataset/BaseModel",
        metadata_version=version,
    )
    kwargs_dict = {"pk": dataset.pk, "version_id": version.pk, "model": model.name}
    url = reverse("model-update", kwargs=kwargs_dict)
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW, action="model-update", http_method="POST", path=url, args=(), kwargs=kwargs_dict
    )
    form = app.get(url).forms["model-form"]
    form["name"] = "UpdatedModel"
    form["prepare"] = "sort(prop1)"
    form["ref"].force_value([prop2.pk, prop1.pk])
    form["base"].force_value([base_model.pk])
    form["comment"] = "Updated Model"
    resp = form.submit()
    model.refresh_from_db()
    assert resp.url == model.get_absolute_url()
    assert model.metadata.count() == 1
    assert model.metadata.first().name == "test/dataset/UpdatedModel"
    assert model.metadata.first().prepare == "sort(prop1)"
    assert model.metadata.first().prepare_ast == {"args": [{"args": ["prop1"], "name": "bind"}], "name": "sort"}

    assert model.base.model == base_model
    assert model.base.metadata.first().name == "test/dataset/BaseModel"
    assert model.base.metadata.first().ref == ""

    assert Version.objects.get_for_object(model).count() == 1
    version = Version.objects.get_for_object(model).select_related("revision").first()
    assert version.revision.comment == revision_comment.to_json()
    assert version.revision.user == user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_param_create_for_resource(app: DjangoTestApp, role: str):
    distribution = DatasetDistributionFactory(is_parameterized=True)
    dataset = distribution.dataset
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    app.set_user(representative.user)

    ct = ContentType.objects.get_for_model(distribution)
    form = app.get(reverse("param-create", args=[dataset.pk, ct.pk, distribution.pk])).forms["param-form"]
    form["name"] = "test"
    form["prepare"] = "param"
    form["title"] = "Test param"
    form["source"] = "src"
    form["description"] = "Param for testing"
    resp = form.submit()

    assert resp.url == distribution.get_absolute_url()
    assert list(distribution.params.values_list("name", flat=True)) == ["test"]
    assert distribution.params.first().paramitem_set.count() == 1
    assert distribution.params.first().paramitem_set.first().metadata.first().name == "test"
    assert distribution.params.first().paramitem_set.first().metadata.first().prepare == "param"
    assert distribution.params.first().paramitem_set.first().metadata.first().title == "Test param"
    assert distribution.params.first().paramitem_set.first().metadata.first().source == "src"
    assert distribution.params.first().paramitem_set.first().metadata.first().description == "Param for testing"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_COORDINATOR,
        Representative.RESOURCE_COORDINATOR,
    ],
)
def test_param_create_for_model(app: DjangoTestApp, role: str):
    dataset = DatasetFactory()
    model = ModelFactory(dataset=dataset, is_parameterized=True)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    app.set_user(representative.user)

    ct = ContentType.objects.get_for_model(model)
    form = app.get(reverse("param-create", args=[dataset.pk, ct.pk, model.pk])).forms["param-form"]
    form["name"] = "test"
    form["prepare"] = "param"
    form["title"] = "Test param"
    form["source"] = "src"
    form["description"] = "Param for testing"
    resp = form.submit()

    assert resp.url == model.get_absolute_url()
    assert list(model.params.values_list("name", flat=True)) == ["test"]
    assert model.params.first().paramitem_set.count() == 1
    assert model.params.first().paramitem_set.first().metadata.first().name == "test"
    assert model.params.first().paramitem_set.first().metadata.first().prepare == "param"
    assert model.params.first().paramitem_set.first().metadata.first().title == "Test param"
    assert model.params.first().paramitem_set.first().metadata.first().source == "src"
    assert model.params.first().paramitem_set.first().metadata.first().description == "Param for testing"
    assert Version.objects.get_for_object(model).count() == 1
    assert Version.objects.get_for_object(model).first().revision.user == representative.user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_COORDINATOR,
        Representative.RESOURCE_COORDINATOR,
    ],
)
def test_param_update(app: DjangoTestApp, role: str):
    distribution = DatasetDistributionFactory(is_parameterized=True)
    dataset = distribution.dataset
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=role,
    )
    app.set_user(representative.user)
    ct = ContentType.objects.get_for_model(distribution)
    param = ParamFactory(content_type=ct, object_id=distribution.pk)
    param_item = ParamItemFactory(param=param)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(param_item),
        object_id=param_item.pk,
        dataset=dataset,
        name="test",
        title="Test param",
        prepare="param",
    )

    form = app.get(reverse("param-update", args=[dataset.pk, param_item.pk])).forms["param-form"]
    form["title"] = "Updated test param"
    resp = form.submit()

    assert resp.url == distribution.get_absolute_url()
    assert distribution.params.first().paramitem_set.count() == 1
    assert distribution.params.first().paramitem_set.first().metadata.first().title == "Updated test param"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_param_delete(app: DjangoTestApp, role: str):
    distribution = DatasetDistributionFactory(is_parameterized=True)
    dataset = distribution.dataset
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    app.set_user(representative.user)
    ct = ContentType.objects.get_for_model(distribution)
    param = ParamFactory(content_type=ct, object_id=distribution.pk)
    param_item = ParamItemFactory(param=param)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(param_item),
        object_id=param_item.pk,
        dataset=dataset,
        name="test",
        title="Test param",
        prepare="param",
    )

    resp = app.post(reverse("param-delete", args=[dataset.pk, param_item.pk]))
    assert resp.url == distribution.get_absolute_url()
    assert distribution.params.first().paramitem_set.count() == 0


@pytest.mark.parametrize("status", [s for s in VersionStatus.values if s != VersionStatus.DRAFT])
@pytest.mark.django_db
def test_new_version_when_chosen_version_not_draft(app: DjangoTestApp, status: str):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory(status=status)
    form = app.get(reverse("version-create", args=[version.dataset.pk, version.pk]), expect_errors=True)
    assert form.status_code == 302
    assert form.location == version.dataset.get_absolute_url()


@pytest.mark.django_db
def test_new_version_with_released_date_earlier_than_two_weeks(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    form = app.get(reverse("version-create", args=[version.dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today()
    form["version_type"] = "MAJOR"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [["Versija gali įsigalioti ne anksčiau kaip po 2 savaičių."]]


@pytest.mark.django_db
def test_new_version_with_released_date_earlier_than_last_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()

    dataset_metadata = MetadataFactory(
        dataset=version.dataset,
        metadata_version=version,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=version.dataset.pk,
    )

    form = app.get(reverse("version-create", args=[version.dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["metadata"] = [dataset_metadata.pk]
    form["version_type"] = "MAJOR"
    form.submit()

    form = app.get(reverse("version-create", args=[version.dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["metadata"] = [dataset_metadata.pk]
    form["version_type"] = "MAJOR"
    resp = form.submit()

    assert list(resp.context["form"].errors.values()) == [["Versija negali įsigalioti anksčiau už praėjusią versiją."]]


@pytest.mark.django_db
def test_new_version_with_new_structure(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )

    prop = PropertyFactory(model=model, metadata_version=version)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()

    assert _Version.objects.filter(dataset=dataset).count() == 2
    assert _Version.objects.exclude(status=VersionStatus.DRAFT).first().dataset == dataset
    assert (
        len(
            list(_Version.objects.exclude(status=VersionStatus.DRAFT).first().metadata_set.values_list("pk", flat=True))
        )
        == 3
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__dataset_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(model=model, metadata_version=version)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    dataset_meta.name = "test/dataset1"
    dataset_meta.draft = True
    dataset_meta.save()
    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3

    assert first_version_metadata.count() == 3
    assert (
        first_version_metadata.filter(content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk)
        .first()
        .name
        == "test/dataset"
    )

    assert second_version_metadata.count() == 1
    assert second_version_metadata.first().object == dataset
    assert second_version_metadata.first().name == "test/dataset1"


@pytest.mark.django_db
def test_new_version_with_updated_structure__model_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(model=model, metadata_version=version)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    model_meta.name = "test/dataset/TestModel1"
    model_meta.draft = True
    model_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3

    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(model),
        )
        .first()
        .name
        == "test/dataset/TestModel"
    )

    assert second_version_metadata.count() == 2
    assert second_version_metadata.first().object.pk != model.pk
    assert (
        second_version_metadata.filter(content_type=ContentType.objects.get_for_model(Model)).first().name
        == "test/dataset/TestModel1"
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(model=model, metadata_version=version)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    prop_meta.name = "prop1"
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3

    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .name
        == "prop"
    )

    assert second_version_metadata.count() == 3
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .object.pk
        != prop.pk
    )
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .name
        == "prop1"
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__model_base(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(model=model, metadata_version=version)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    base_model = ModelFactory(
        dataset=dataset,
        metadata_version=version,
    )
    base_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(base_model),
        object_id=base_model.pk,
        dataset=dataset,
        name="test/dataset/BaseModel",
        metadata_version=version,
    )
    base = BaseFactory(
        model=base_model,
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(base),
        object_id=base.pk,
        dataset=dataset,
        name="test/dataset/BaseModel",
        metadata_version=version,
    )
    model.base = base
    model.save()
    model_meta.draft = True
    model_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, base_model_meta.pk, model_meta.pk]
    form["description"] = "Update structure version"
    form.submit()

    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3

    assert first_version_metadata.count() == 3
    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(model),
        )
        .first()
        .object.base
        is None
    )

    assert second_version_metadata.count() == 4
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(model),
        )
        .first()
        .object.pk
        != model.pk
    )
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(model),
            name="test/dataset/TestModel",
        )
        .first()
        .object.base
        is not None
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__model_ref(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    model_meta.ref = "id"
    model_meta.draft = True
    model_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3
    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(model),
        )
        .first()
        .ref
        == ""
    )

    assert second_version_metadata.count() == 2
    assert second_version_metadata.first().object.pk != model.pk
    assert second_version_metadata.filter(content_type=ContentType.objects.get_for_model(Model)).first().ref == "id"


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_type(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    prop_meta.type = "integer"
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3
    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .type
        == "string"
    )

    assert second_version_metadata.count() == 3
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .object.pk
        != prop.pk
    )
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .type
        == "integer"
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_ref(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    prop_meta.ref = "test/dataset/TestModel"
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3
    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .ref
        == ""
    )

    assert second_version_metadata.count() == 3
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .object.pk
        != prop.pk
    )
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .ref
        == "test/dataset/TestModel"
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__model_level(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        level_given=3,
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    model_meta.level_given = 5
    model_meta.draft = True
    model_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3
    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(model),
        )
        .first()
        .level_given
        == 3
    )

    assert second_version_metadata.count() == 2
    assert second_version_metadata.first().object.pk != model.pk
    assert (
        second_version_metadata.filter(content_type=ContentType.objects.get_for_model(Model)).first().level_given == 5
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_level(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        level_given=3,
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    prop_meta.level_given = 5
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3
    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .level_given
        == 3
    )

    assert second_version_metadata.count() == 3
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .object.pk
        != prop.pk
    )
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .level_given
        == 5
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_access(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        access=3,
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    prop_meta.access = 5
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3
    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .access
        == 3
    )

    assert second_version_metadata.count() == 3
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .object.pk
        != prop.pk
    )
    assert (
        second_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(prop),
        )
        .first()
        .access
        == 5
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__enum_prepare(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        access=3,
        metadata_version=version,
    )
    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        metadata_version=version,
    )
    enum_item = EnumItemFactory(
        enum=enum,
        metadata_version=version,
    )
    enum_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title="Test value",
        description="For testing",
        prepare="1",
        access=Metadata.OPEN,
        source="TEST",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk, enum_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    enum_meta.prepare = "2"
    enum_meta.draft = True
    enum_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk, enum_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3
    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(enum_item),
        )
        .first()
        .prepare
        == "1"
    )

    assert second_version_metadata.count() == 4
    assert (
        second_version_metadata.filter(content_type=ContentType.objects.get_for_model(enum_item)).first().object.pk
        != enum_item.pk
    )
    assert (
        second_version_metadata.filter(content_type=ContentType.objects.get_for_model(enum_item)).first().prepare == "2"
    )


@pytest.mark.django_db
def test_new_version_with_updated_structure__enum_source(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="test/dataset")
    dataset_meta = dataset.metadata.first()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        access=3,
        metadata_version=version,
    )
    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        metadata_version=version,
    )
    enum_item = EnumItemFactory(
        enum=enum,
        metadata_version=version,
    )
    enum_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title="Test value",
        description="For testing",
        prepare="1",
        access=Metadata.OPEN,
        source="TEST",
        metadata_version=version,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=14)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk, enum_meta.pk]
    form["description"] = "Add new structure to version"
    form.submit()
    first_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=first_published_version).all()

    enum_meta.source = "TEST1"
    enum_meta.draft = True
    enum_meta.save()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk, enum_meta.pk]
    form["description"] = "Update structure version"
    form.submit()
    second_published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_version_metadata = Metadata.objects.filter(dataset=dataset, metadata_version=second_published_version).all()

    assert dataset.dataset_version.count() == 3
    assert (
        first_version_metadata.filter(
            content_type=ContentType.objects.get_for_model(enum_item),
        )
        .first()
        .source
        == "TEST"
    )

    assert second_version_metadata.count() == 4
    assert (
        second_version_metadata.filter(content_type=ContentType.objects.get_for_model(enum_item)).first().object.pk
        != enum_item.pk
    )
    assert (
        second_version_metadata.filter(content_type=ContentType.objects.get_for_model(enum_item)).first().source
        == "TEST1"
    )


@pytest.mark.django_db
def test_structure_tab_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse("dataset-structure-no-version", args=[dataset.pk])).follow(expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_structure_tab_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=role,
    )
    app.set_user(user)
    response = app.get(reverse("dataset-structure-no-version", args=[dataset.pk])).follow()
    assert response.context["dataset"] == dataset


@pytest.mark.django_db
def test_version_list_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    VersionFactory(dataset=dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse("version-list", args=[dataset.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_version_list_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    VersionFactory(dataset=dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk, user=user, role=role
    )
    app.set_user(user)
    response = app.get(reverse("version-list", args=[dataset.pk]))
    assert list(response.context["versions"]) == []  # Version that gets created is Draft which is not displayed


@pytest.mark.django_db
def test_version_detail_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse("version-detail", args=[dataset.pk, version.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_version_detail_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk, user=user, role=role
    )
    app.set_user(user)
    response = app.get(reverse("version-detail", args=[dataset.pk, version.pk]))
    assert response.context["version"] == version


@pytest.mark.django_db
def test_model_structure_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse("model-structure", args=[dataset.pk, version.pk, model.name]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_model_structure_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk, user=user, role=role
    )
    app.set_user(user)
    response = app.get(reverse("model-structure", args=[dataset.pk, version.pk, model.name]))
    assert response.context["model"] == model


@pytest.mark.django_db
def test_property_structure_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    app.set_user(user)
    response = app.get(
        reverse("property-structure", args=[dataset.pk, version.pk, model.name, prop.name]), expect_errors=True
    )
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_property_structure_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk, user=user, role=role
    )
    app.set_user(user)
    response = app.get(reverse("property-structure", args=[dataset.pk, version.pk, model.name, prop.name]))
    assert response.context["prop"] == prop


@pytest.mark.django_db
def test_model_data_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse("model-data", args=[dataset.pk, version.pk, model.name]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_model_data_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk, user=user, role=role
    )
    app.set_user(user)
    response = app.get(reverse("model-data", args=[dataset.pk, version.pk, model.name]))
    assert response.context["model"] == model


@pytest.mark.django_db
def test_object_data_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    app.set_user(user)
    response = app.get(
        reverse("object-data", args=[dataset.pk, version.pk, model.name, "123456789"]), expect_errors=True
    )
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_object_data_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk, user=user, role=role
    )
    app.set_user(user)
    response = app.get(reverse("object-data", args=[dataset.pk, version.pk, model.name, "123456789"]))
    assert response.context["model"] == model


@pytest.mark.django_db
def test_api_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse("getall-api", args=[dataset.pk, version.pk, model.name]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_api_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=version)
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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk, user=user, role=role
    )
    app.set_user(user)
    response = app.get(reverse("getall-api", args=[dataset.pk, version.pk, model.name]))
    assert response.context["model"] == model


@pytest.mark.django_db
def test_visibility_without_access(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,private,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,City,,,,,,,,protected,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,Province,,,,,,,,package,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,State,,,,,,,,public,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,,residence,string,,,,5,,public,open,dct:residence,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk, version.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == [
        "datasets/gov/ivpk/adp/Province",
        "datasets/gov/ivpk/adp/State",
    ]

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "City"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "City", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "City", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "Province"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "State"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "residence"]),
        expect_errors=True,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_model_visibility_with_manager_access(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,private,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,City,,,,,,,,protected,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,Province,,,,,,,,package,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,State,,,,,,,,public,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,,residence,string,,,,5,,public,open,dct:residence,,,,\n"
    )

    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct, object_id=structure.dataset.pk, role=Representative.RESOURCE_MANAGER
    )
    app.set_user(representative.user)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk, version.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == [
        "datasets/gov/ivpk/adp/City",
        "datasets/gov/ivpk/adp/Country",
        "datasets/gov/ivpk/adp/Province",
        "datasets/gov/ivpk/adp/State",
    ]
    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "City"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "City", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "City", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "Province"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "State"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "residence"]),
        expect_errors=True,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_model_visibility_with_open_data_representative_access(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,private,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,City,,,,,,,,protected,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,Province,,,,,,,,package,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,State,,,,,,,,public,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,,residence,string,,,,5,,public,open,dct:residence,,,,\n"
    )
    organization = OrganizationFactory(kind=Organization.GOV)
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.organization = organization
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)
    representative = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(structure.dataset.organization),
        object_id=structure.dataset.organization.pk,
        role=Representative.OPEN_DATA_MANAGER,
    )
    app.set_user(representative.user)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk, version.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == [
        "datasets/gov/ivpk/adp/Province",
        "datasets/gov/ivpk/adp/State",
    ]
    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "City"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "City", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "City", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "Province"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "State"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "residence"]),
        expect_errors=True,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_model_visibility_with_information_system_representative_access(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,private,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,City,,,,,,,,protected,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,Province,,,,,,,,package,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,State,,,,,,,,public,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,,residence,string,,,,5,,public,open,dct:residence,,,,\n"
    )
    organization = OrganizationFactory(kind=Organization.GOV)
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.organization = organization
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    representative = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(structure.dataset.organization),
        object_id=structure.dataset.organization.pk,
        role=Representative.RESOURCE_MANAGER,
    )
    app.set_user(representative.user)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk, version.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == [
        "datasets/gov/ivpk/adp/City",
        "datasets/gov/ivpk/adp/Country",
        "datasets/gov/ivpk/adp/Province",
        "datasets/gov/ivpk/adp/State",
    ]
    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "City"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "City", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "City", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "Province"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Province", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, version.pk, "State"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "State", "residence"]),
        expect_errors=True,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_model_create_with_public_visibility_without_uri_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("model-create-no-version", args=[dataset.pk])).forms["model-form"]
    form["name"] = "Test"
    form["visibility"] = Metadata.VISIBILITY_PUBLIC
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Stulpelis 'Klasė' turi būti užpildytas pasirenkant šį metaduomenų matomumo lygį."]
    ]


@pytest.mark.django_db
def test_property_create_with_in_released_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    version = VersionFactory(status=VersionStatus.PRE_RELEASE)
    model = ModelFactory(dataset=version.dataset, metadata_version=version)
    dataset = version.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        visibility=Metadata.PRIVATE,
        metadata_version=version,
    )
    form = app.get(reverse("property-create", args=[dataset.pk, version.pk, model.name]), expect_errors=True)
    assert form.status_code == 302
    assert form.location == model.get_absolute_url()


@pytest.mark.django_db
def test_property_create__higher_visibility_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    version = VersionFactory()
    model = ModelFactory(dataset=version.dataset, metadata_version=version)
    dataset = version.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        visibility=Metadata.PRIVATE,
        metadata_version=version,
    )
    form = app.get(reverse("property-create", args=[dataset.pk, version.pk, model.name])).forms["property-form"]
    form["name"] = "property"
    form["access"] = Metadata.OPEN
    form["visibility"] = Metadata.PROTECTED
    form["type"] = "any"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Metaduomenų matomumas 'protected' negali būti didesnis nei duomenų modelio matomumas 'private'."]
    ]


@pytest.mark.django_db
def test_property_enum_item_create__higher_visibility_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

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
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        visibility=Metadata.PRIVATE,
        metadata_version=version,
    )
    form = app.get(reverse("enum-create", args=[dataset.pk, version.pk, model.name, prop.name])).forms["enum-form"]
    form["value"] = 2
    form["source"] = 2
    form["access"] = Metadata.OPEN
    form["title"] = "Test value"
    form["description"] = "For testing"
    form["visibility"] = Metadata.PROTECTED
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Metaduomenų matomumas 'protected' negali būti didesnis nei duomenų lauko matomumas 'private'."]
    ]


@pytest.mark.django_db
def test_property_enum_create_with_in_released_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    version = VersionFactory(status=VersionStatus.PRE_RELEASE)
    model = ModelFactory(dataset=version.dataset, metadata_version=version)
    dataset = version.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        visibility=Metadata.PRIVATE,
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset",
        metadata_version=version,
    )
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        metadata_version=version,
    )
    resp = app.get(
        reverse("enum-create", args=[dataset.pk, version.pk, model.name, prop.name]),
    )
    assert resp.status_code == 302
    assert resp.location == prop.get_absolute_url()


@pytest.mark.django_db
def test_property_enum_item_create__higher_visibility_then_model_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    version = VersionFactory()
    model = ModelFactory(dataset=version.dataset, metadata_version=version)
    dataset = version.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        visibility=Metadata.PRIVATE,
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset",
        metadata_version=version,
    )
    prop = PropertyFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        metadata_version=version,
    )
    form = app.get(reverse("enum-create", args=[dataset.pk, version.pk, model.name, prop.name])).forms["enum-form"]
    form["value"] = 2
    form["source"] = 2
    form["access"] = Metadata.OPEN
    form["title"] = "Test value"
    form["description"] = "For testing"
    form["visibility"] = Metadata.PROTECTED
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Metaduomenų matomumas 'protected' negali būti didesnis nei duomenų modelio matomumas 'private'."]
    ]


@pytest.mark.django_db
def test_manifest_export_openapi(app: DjangoTestApp):
    """Test OpenAPI manifest export returns valid spec with correct metadata, schemas, tags, and paths."""
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure, structure.dataset.metadata.first().metadata_version)

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.pk,
    )
    app.set_user(representative.user)
    resp = app.get(reverse("dataset-structure-export-openapi", args=[structure.dataset.pk, version.pk]))

    assert resp.status_code == 200
    assert resp.content_type == "application/json"

    openapi_spec = resp.json

    expected_keys = ["openapi", "info", "externalDocs", "servers", "tags", "components", "paths"]
    assert list(openapi_spec.keys()) == expected_keys, "OpenAPI spec missing required top-level fields"

    info = openapi_spec["info"]
    assert info["summary"] == structure.dataset.title, "Info summary should match dataset title"
    assert info["description"] == structure.dataset.description, "Info description should match dataset description"
    assert info["version"] == "1.0.0", "API version should be 1.0.0"

    schemas = set(openapi_spec["components"]["schemas"].keys())
    expected_schemas = {"Country", "CountryCollection", "CountryChange", "CountryChanges"}
    assert expected_schemas <= schemas, f"Missing required schemas: {expected_schemas - schemas}"

    tag_names = {tag["name"] for tag in openapi_spec["tags"]}
    expected_tags = {"utility", "Country"}
    assert tag_names == expected_tags, f"Tags mismatch. Expected: {expected_tags}, Got: {tag_names}"

    utility_paths = {"/version", "/health"}
    model_paths = {
        "/datasets/gov/ivpk/adp/Country",
        "/datasets/gov/ivpk/adp/Country/{id}",
        "/datasets/gov/ivpk/adp/Country/:changes/{cid}",
    }
    expected_paths = utility_paths | model_paths
    actual_paths = set(openapi_spec["paths"].keys())
    assert actual_paths == expected_paths, (
        f"Paths mismatch. Missing: {expected_paths - actual_paths}, Extra: {actual_paths - expected_paths}"
    )


@pytest.mark.django_db
def test_manifest_export_openapi_soap_params(app: DjangoTestApp):
    """Test OpenAPI manifest export returns valid spec with correct metadata, schemas, tags, and paths."""
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,rc_wsdl,,,,wsdl,,https://test-data.data.gov.lt/api/v1/rc/get-data/?wsdl,,,,,,,,,,\n"
        ",,get_data,,,,soap,,Get.GetPort.GetPort.GetData,wsdl(rc_wsdl),,,,,,,,,\n"
        ",,,,,,param,action_type,input/ActionType,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.pk,
    )
    app.set_user(representative.user)
    resp = app.get(reverse("dataset-structure-export-openapi", args=[structure.dataset.pk, version.pk]))

    assert resp.status_code == 200
    assert resp.content_type == "application/json"

    openapi_spec = resp.json

    expected_keys = ["openapi", "info", "externalDocs", "servers", "tags", "components", "paths"]
    assert list(openapi_spec.keys()) == expected_keys, "OpenAPI spec missing required top-level fields"


@pytest.mark.django_db
def test_imported_metadata_gets_develop_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,Size,,SMALL,,,,,,,,,\n"
        ",,,,,,,,,MEDIUM,,,,,,,,,\n"
        ",,,,,,,,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]
    assert list(resp_models.context["props"].values_list("metadata__status__codename", flat=True)) == [
        "develop",
        "develop",
        "develop",
    ]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "id"]))
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]
    assert resp_props.context["prop"].metadata.get().status.codename == "develop"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "title"]))
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]
    assert resp_props.context["prop"].metadata.get().status.codename == "develop"

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    )
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]

    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        assert enum_item.metadata.first().status.codename == "develop"


@pytest.mark.parametrize("status", [s for s in VersionStatus.values if s != VersionStatus.DRAFT])
@pytest.mark.django_db
def test_updating_metadata_in_not_draft_version_not_allowed(app: DjangoTestApp, status: str):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)
    version.status = status
    version.save()
    enum_meta = Metadata.objects.filter(dataset=structure.dataset, name="small", metadata_version=version).first()

    enum = enum_meta.object
    enum_id = enum.id

    model_form = app.get(
        reverse("model-update", args=[structure.dataset.pk, version.pk, "Country"]), expect_errors=True
    )
    assert model_form.status_code == 302
    assert model_form.location == structure.dataset.get_absolute_url()

    property_form = app.get(
        reverse("property-update", args=[structure.dataset.pk, version.pk, "Country", "administration"]),
        expect_errors=True,
    )
    assert property_form.status_code == 302

    expected_location = reverse(
        "model-structure",
        args=[structure.dataset.pk, version.pk, "Country"],
    )
    assert property_form.location == expected_location

    enum_form = app.get(
        reverse("enum-update", args=[structure.dataset.pk, version.pk, "Country", "administration", enum_id]),
        expect_errors=True,
    )
    assert enum_form.status_code == 302

    expected_location = reverse(
        "property-structure", args=[structure.dataset.pk, version.pk, "Country", "administration"]
    )

    assert enum_form.location == expected_location


@pytest.mark.django_db
def test_published_metadata_gets_completed_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,Size,,SMALL,,,,,,,,,\n"
        ",,,,,,,,,MEDIUM,,,,,,,,,\n"
        ",,,,,,,,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    metadata_ids = list(
        Metadata.objects.filter(
            dataset=structure.dataset,
            draft=True,
        ).values_list("id", flat=True)
    )

    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = metadata_ids
    form.submit()

    published_version = _Version.objects.exclude(status=VersionStatus.DRAFT).first()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, published_version.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["completed"]
    assert list(resp_models.context["props"].values_list("metadata__status__codename", flat=True)) == [
        "completed",
        "completed",
        "completed",
    ]

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, published_version.pk, "Country", "id"])
    )
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["completed"]
    assert resp_props.context["prop"].metadata.get().status.codename == "completed"

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, published_version.pk, "Country", "title"])
    )
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["completed"]
    assert resp_props.context["prop"].metadata.get().status.codename == "completed"

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, published_version.pk, "Country", "administration"])
    )
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["completed"]

    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        assert enum_item.metadata.first().status.codename == "completed"


@pytest.mark.django_db
def test_changed_metadata_keeps_status_after_publishing(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, name="small", metadata_version=version).first()

    enum = enum_meta.object
    enum_id = enum.id

    metadata_ids = list(
        Metadata.objects.filter(
            dataset=structure.dataset,
            draft=True,
            metadata_version=version,
        ).values_list("id", flat=True)
    )

    model_form = app.get(reverse("model-update", args=[structure.dataset.pk, version.pk, "Country"])).forms[
        "model-form"
    ]
    model_form["status"] = Status.objects.filter(codename="discont").first().id
    model_form.submit()

    property_form = app.get(
        reverse("property-update", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    ).forms["property-form"]
    property_form["status"] = Status.objects.filter(codename="deprecated").first().id
    property_form.submit()

    enum_form = app.get(
        reverse("enum-update", args=[structure.dataset.pk, version.pk, "Country", "administration", enum_id])
    ).forms["enum-form"]
    enum_form["status"] = Status.objects.filter(codename="withdrawn").first().id
    enum_form.submit()

    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = metadata_ids
    form.submit()
    published_version = _Version.objects.exclude(status=VersionStatus.DRAFT).first()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, published_version.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["discont"]

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, published_version.pk, "Country", "id"])
    )
    assert resp_props.context["prop"].metadata.get().status.codename == "discont"

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, published_version.pk, "Country", "title"])
    )
    assert resp_props.context["prop"].metadata.get().status.codename == "completed"

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, published_version.pk, "Country", "administration"])
    )
    assert resp_props.context["prop"].metadata.get().status.codename == "deprecated"

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, published_version.pk, "Country", "administration"])
    )
    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        assert enum_item.metadata.first().status.codename == "withdrawn"


@pytest.mark.django_db
def test_draft_metadata_defaults_to_develop_after_hard_change(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,big,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, metadata_version=version, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id
    new_enum_name = "Largety"

    model_form = app.get(reverse("model-update", args=[structure.dataset.pk, version.pk, "Country"])).forms[
        "model-form"
    ]
    model_form["level"] = 3
    model_form.submit()

    property_form = app.get(
        reverse("property-update", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    ).forms["property-form"]
    property_form["access"] = 2
    property_form.submit()

    enum_form = app.get(
        reverse("enum-update", args=[structure.dataset.pk, version.pk, "Country", "administration", enum_id])
    ).forms["enum-form"]
    enum_form["value"] = new_enum_name
    enum_form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    )
    assert resp_props.context["prop"].metadata.get().status.codename == "develop"

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    )
    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        enum_metadata = enum_item.metadata.first()
        assert enum_metadata.status.codename == "develop"


@pytest.mark.django_db
def test_changing_multiple_fields_in_draft_structure_respects_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,big,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, metadata_version=version, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id
    new_enum_name = "Largety"

    model_form = app.get(reverse("model-update", args=[structure.dataset.pk, version.pk, "Country"])).forms[
        "model-form"
    ]
    model_form["level"] = 2
    model_form["status"] = 5
    model_form.submit()

    property_form = app.get(
        reverse("property-update", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    ).forms["property-form"]
    property_form["access"] = 2
    property_form["status"] = 5
    property_form.submit()

    enum_form = app.get(
        reverse("enum-update", args=[structure.dataset.pk, version.pk, "Country", "administration", enum_id])
    ).forms["enum-form"]
    enum_form["value"] = new_enum_name
    enum_form["status"] = 5
    enum_form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["deprecated"]

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    )
    assert resp_props.context["prop"].metadata.get().status.codename == "deprecated"

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    )
    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        enum_metadata = enum_item.metadata.first()
        if enum_metadata.name == new_enum_name:
            assert enum_metadata.status.codename == "completed"
        else:
            assert enum_metadata.status.codename == "deprecated"


@pytest.mark.django_db
def test_draft_metadata_form_does_not_change_status_is_kept(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,big,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, metadata_version=version, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id

    model_form = app.get(reverse("model-update", args=[structure.dataset.pk, version.pk, "Country"])).forms[
        "model-form"
    ]
    model_form.submit()

    property_form = app.get(
        reverse("property-update", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    ).forms["property-form"]
    property_form.submit()

    enum_form = app.get(
        reverse("enum-update", args=[structure.dataset.pk, version.pk, "Country", "administration", enum_id])
    ).forms["enum-form"]
    enum_form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, version.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    )
    assert resp_props.context["prop"].metadata.get().status.codename == "develop"

    resp_props = app.get(
        reverse("property-structure", args=[structure.dataset.pk, version.pk, "Country", "administration"])
    )
    prop = resp_props.context["prop"]
    # TODO the status of enum should also be completed but because of a bug the name of the enum is changed even though nothing is submited. Change after bug fix
    for enum_item in prop.enums.first().enumitem_set.all():
        enum_metadata = enum_item.metadata.first()
        assert enum_metadata.status.codename == "develop"


@pytest.mark.django_db
def test_props_metadata_rendering(app: DjangoTestApp) -> None:
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

    prop_1 = PropertyFactory(model=model, metadata_version=version)
    prop_2 = PropertyFactory(model=model, metadata_version=version)

    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name="prop_1",
        type="string",
        eli="https://example.com/prop_1",
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name="prop_2",
        type="integer",
        eli="https://example.com/prop_2",
        metadata_version=version,
    )

    response = app.get(
        reverse("model-structure", kwargs={"pk": dataset.pk, "version_id": version.pk, "model": model.name})
    )

    assert response.status_code == 200
    assert 'href="https://example.com/prop_1"' in response.content.decode()
    assert 'href="https://example.com/prop_2"' in response.content.decode()


@pytest.mark.django_db
def test_only_major_version_allowed_when_new_metadata(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    dataset = version.dataset

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]

    assert form["version_type"].options[0][0] == "MAJOR"


@pytest.mark.django_db
def test_minor_version_available_if_major_exists(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    dataset = version.dataset
    dataset_metadata = MetadataFactory(
        dataset=version.dataset,
        metadata_version=version,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=version.dataset.pk,
    )

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["metadata"] = [dataset_metadata.pk]
    form["version_type"] = "MAJOR"
    form.submit()

    second_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]

    assert [opt[0] for opt in second_version_form["version_type"].options] == ["MAJOR", "MINOR", "PATCH"]


@pytest.mark.django_db
def test_patch_version_available_if_minor_exists(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    dataset = version.dataset
    dataset_metadata = MetadataFactory(
        dataset=version.dataset,
        metadata_version=version,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=version.dataset.pk,
    )
    major_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["metadata"] = [dataset_metadata.pk]
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MAJOR)

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["metadata"] = [dataset_metadata.pk]
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = major_version.pk
    minor_version_form.submit()

    patch_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]

    assert [opt[0] for opt in patch_version_form["version_type"].options] == ["MAJOR", "MINOR", "PATCH"]


@pytest.mark.django_db
def test_form_errors_if_major_not_selected(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    dataset = version.dataset
    dataset_metadata = MetadataFactory(
        dataset=version.dataset,
        metadata_version=version,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=version.dataset.pk,
    )

    major_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["version_type"] = "MAJOR"
    major_version_form["metadata"] = [dataset_metadata.pk]
    major_version_form.submit()

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["metadata"] = [dataset_metadata.pk]
    minor_version_form["version_type"] = "MINOR"

    res = minor_version_form.submit(expect_errors=True)

    assert "Tėvinė versija turi būti pasirinkta" in res.text


@pytest.mark.django_db
def test_form_errors_if_minor_not_selected(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    dataset = version.dataset
    dataset_metadata = MetadataFactory(
        dataset=version.dataset,
        metadata_version=version,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=version.dataset.pk,
    )

    major_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["metadata"] = [dataset_metadata.pk]
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MAJOR)

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["metadata"] = [dataset_metadata.pk]
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = major_version.pk
    minor_version_form.submit()

    patch_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    patch_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    patch_version_form["metadata"] = [dataset_metadata.pk]
    patch_version_form["version_type"] = "PATCH"

    res = patch_version_form.submit(expect_errors=True)

    assert "Tėvinė versija turi būti pasirinkta" in res.text


@pytest.mark.django_db
def test_multiple_major_versions_increment_external_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    dataset = version.dataset
    dataset_metadata = MetadataFactory(
        dataset=version.dataset,
        metadata_version=version,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=version.dataset.pk,
    )

    major_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["metadata"] = [dataset_metadata.pk]
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["metadata"] = [dataset_metadata.pk]
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_versions = _Version.objects.filter(dataset=dataset, version_type=VersionType.MAJOR).order_by("created")

    assert major_versions[0].external_version == "1.0.0"
    assert major_versions[1].external_version == "2.0.0"


@pytest.mark.django_db
def test_multiple_minor_versions_increment_external_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    dataset = version.dataset
    dataset_metadata = MetadataFactory(
        dataset=version.dataset,
        metadata_version=version,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=version.dataset.pk,
    )

    major_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["metadata"] = [dataset_metadata.pk]
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MAJOR)

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["metadata"] = [dataset_metadata.pk]
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = major_version.pk
    minor_version_form.submit()

    latest_version = _Version.objects.last()

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["metadata"] = [dataset_metadata.pk]
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = latest_version.pk
    minor_version_form.submit()

    minor_versions = _Version.objects.filter(dataset=dataset, version_type=VersionType.MINOR).order_by("created")

    assert minor_versions[0].external_version == "1.1.0"
    assert minor_versions[1].external_version == "1.2.0"


@pytest.mark.django_db
def test_multiple_patch_versions_increment_external_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    dataset = version.dataset
    dataset_metadata = MetadataFactory(
        dataset=version.dataset,
        metadata_version=version,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=version.dataset.pk,
    )

    major_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["metadata"] = [dataset_metadata.pk]
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MAJOR)

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["metadata"] = [dataset_metadata.pk]
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = major_version.pk
    minor_version_form.submit()

    minor_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MINOR)

    patch_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    patch_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    patch_version_form["metadata"] = [dataset_metadata.pk]
    patch_version_form["related_version"] = minor_version.pk
    patch_version_form["version_type"] = "PATCH"
    patch_version_form.submit()

    latest_version = _Version.objects.last()

    patch_version_form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    patch_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    patch_version_form["metadata"] = [dataset_metadata.pk]
    patch_version_form["related_version"] = latest_version.pk
    patch_version_form["version_type"] = "PATCH"
    patch_version_form.submit()

    patch_versions = _Version.objects.filter(dataset=dataset, version_type=VersionType.PATCH).order_by("created")

    assert patch_versions[0].external_version == "1.1.1"
    assert patch_versions[1].external_version == "1.1.2"


def test_publish_form_shows_all_metadata_rows_params(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        '2,,,,,,param,country,,"lt",,,,,,,,,\n'
        '3,,,,,,,,,"lv",,,,,,,,,\n'
        '4,,,,,,,,,"ee",,,,,,,,,\n'
        "5,,,,City,,,,,,,,,,,,,,\n"
        '6,,,,,,param,type,,"created",,,,,,,,,\n'
        '7,,,,,,,,,"modified",,,,,,,,,\n'
        "8,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "9,,,,,type,string,,,,5,,,open,dct:type,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 10


def test_publish_form_shows_all_metadata_rows_base(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "1,,,,Base,,,,,,4,,,,,,,,,\n"
        ",,,Base,,,,,,,4,,,,,,,,,\n"
        "2,,,,City,,,,,,5,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,,,,,,,\n"
        ",,,,,title,string,,,,5,,,,,,,,,\n"
        ",,,,,country,ref,Country,,,4,,,,,,,,,\n"
        "3,,,,Country,,,,,,4,,,,,,,,,\n"
        ",,,,,id,integer,,,,3,,,,,,,,,\n"
        ",,,,,title,string,,,,2,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 9


def test_publish_form_shows_all_metadata_rows_enum(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,,,,,enum,Size,,SMALL,,,,,,,,,,\n"
        "4,,,,,,,,,MEDIUM,,,,,,,,,\n"
        "5,,,,,,,,,BIG,,,,,,,,,\n"
        "6,,,,City,,,,,,,,,,,,,,\n"
        "7,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
        "8,,,,,size,Size,,,,,5,,,open,dct:size,,,\n"
        "9,,,,,type,string,,,,,5,,,open,dct:type,,,\n"
        "10,,,,,,enum,Type,,CREATED,,,,,,,,,\n"
        "11,,,,,,,,,MODIFIED,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 11


def test_publish_form_shows_all_metadata_rows_single_defined_resource(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/govsssss/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,City,,,,,,5,,,,,,,,,\n"
        "3,,,,,id,integer,,,,5,,,,,,,,,\n"
        "4,,,,,title,string,,,,5,,,,,,,,,\n"
        "5,,,,,country,ref,Country,,,4,,,,,,,,,\n"
        "6,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "7,,,,Country,,,,,,4,,,,,,,,,\n"
        "8,,,,,id,integer,,,,3,,,,,,,,,\n"
        "9,,,,,title,string,,,,2,,,,,,,,,\n"
    )

    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 9


def test_publish_form_shows_all_metadata_rows_multiple_resources(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/govsssss/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,resource1,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "3,,,,City,,,,,,5,,,,,,,,,\n"
        "4,,,,,id,integer,,,,5,,,,,,,,,\n"
        "5,,,,,title,string,,,,5,,,,,,,,,\n"
        "6,,,,,country,ref,Country,,,4,,,,,,,,,\n"
        "7,,resource,,,,,,http://www.example2.com,,,,,,,,,Title,Description\n"
        "8,,,,Country,,,,,,4,,,,,,,,,\n"
        "9,,,,,id,integer,,,,3,,,,,,,,,\n"
        "10,,,,,title,string,,,,2,,,,,,,,,\n"
    )

    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    dataset_distributions = DatasetDistribution.objects.filter(dataset=structure.dataset)

    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 10
    assert len(dataset_distributions) == 2
    assert dataset_distributions.first().metadata.first().name == "resource1"
    assert dataset_distributions.last().metadata.first().name == "resource"


def test_publish_form_shows_all_metadata_rows_denorm_props(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/govsssss/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,City,,,,,,,,,,,,,,\n"
        "3,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        "4,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "5,,,,,country,ref,Country,,,5,,,open,,,,,,\n"
        "6,,,,,country.id,,,,,5,,,open,,,,,,\n"
        "7,,,,,country.continent.id,,,,,5,,,open,,,,,,\n"
        "8,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "9,,,,Country,,,,,,4,,,,,,,,,\n"
        "10,,,,,id,integer,,,,3,,,,,,,,,\n"
        "11,,,,,title,string,,,,2,,,,,,,,,\n"
    )

    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 12  # Denorm props create an additional property country.continent


def test_publishing_dataset_duplicates_metadata_but_not_dataset(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    original_metadata_count = 1
    origin_version_count = 1

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Dataset.objects.count() == 2  # One Dataset created through a migration
    assert _Version.objects.filter(dataset=dataset).count() == origin_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = dataset_meta.pk
    form.submit()

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count * 2
    assert Dataset.objects.count() == 2  # One Dataset created through a migration
    assert _Version.objects.filter(dataset=dataset).count() == origin_version_count * 2


def test_if_dataset_not_published_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(Model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset",
        metadata_version=version,
    )
    assert Metadata.objects.filter(dataset=dataset).count() == 2
    assert Dataset.objects.count() == 2  # One Dataset created through a migration
    assert _Version.objects.filter(dataset=dataset).count() == 1

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [model_meta]
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert "Privalote publikuoti duomenų rinkinį." in response.context["form"].errors["__all__"][0]


def test_publishing_model_duplicates_metadata_and_model(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )

    original_metadata_count = 2
    original_model_count = 1
    original_version_count = 1

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Model.objects.filter(dataset=dataset).count() == original_model_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk]
    form.submit()

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count * 2
    assert Model.objects.filter(dataset=dataset).count() == original_model_count * 2
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count * 2


def test_publishing_model_duplicates_metadata_and_dataset_distribution(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    distribution = DatasetDistributionFactory(dataset=dataset, is_parameterized=True)
    model = ModelFactory(dataset=dataset, metadata_version=version, distribution=distribution)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )

    original_metadata_count = 3
    original_model_count = 1
    original_distribution_count = 1
    original_version_count = 1

    distribution_meta = distribution.metadata.first()
    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Model.objects.filter(dataset=dataset).count() == original_model_count
    assert DatasetDistribution.objects.filter(dataset=dataset).count() == original_distribution_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, distribution_meta.pk, model_meta.pk]
    form.submit()

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count * 2
    assert Model.objects.filter(dataset=dataset).count() == original_model_count * 2
    assert DatasetDistribution.objects.filter(dataset=dataset).count() == original_distribution_count * 2
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count * 2


def test_publishing_model_without_resource_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    distribution = DatasetDistributionFactory(dataset=dataset, is_parameterized=True, metadata_version=version)
    model = ModelFactory(dataset=dataset, metadata_version=version, distribution=distribution)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )

    original_metadata_count = 3
    original_model_count = 1
    original_distribution_count = 1
    original_version_count = 1

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Model.objects.filter(dataset=dataset).count() == original_model_count
    assert DatasetDistribution.objects.filter(dataset=dataset).count() == original_distribution_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk]
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert "laukas TestModel turi nuorodą į jį" in response.context["form"].errors["__all__"][0]

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Model.objects.filter(dataset=dataset).count() == original_model_count
    assert DatasetDistribution.objects.filter(dataset=dataset).count() == original_distribution_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count


def test_publishing_property_duplicates_metadata_and_property(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(model=model, metadata_version=version)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    original_metadata_count = 3
    original_property_count = 1
    original_version_count = 1

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Property.objects.count() == original_property_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form.submit()

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count * 2
    assert Property.objects.count() == original_property_count * 2
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count * 2


def test_publishing_property_without_model_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    model = ModelFactory(dataset=dataset, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(model=model, metadata_version=version)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=version,
    )

    original_metadata_count = 3
    original_property_count = 1
    original_version_count = 1

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Property.objects.count() == original_property_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, prop_meta.pk]
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert "laukas prop turi nuorodą į jį" in response.context["form"].errors["__all__"][0]

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Property.objects.count() == original_property_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count


def test_publishing_enum_duplicates_enum_item_and_enum(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        access=3,
        metadata_version=version,
    )
    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        metadata_version=version,
    )
    enum_item = EnumItemFactory(
        enum=enum,
        metadata_version=version,
    )
    enum_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title="Test value",
        description="For testing",
        prepare="1",
        access=Metadata.OPEN,
        source="TEST",
        metadata_version=version,
    )

    original_metadata_count = 4
    original_enum_item_count = 1
    original_enum_count = 1
    original_version_count = 1

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert EnumItem.objects.count() == original_enum_item_count
    assert Enum.objects.count() == original_enum_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk, prop_meta.pk, enum_meta.pk]
    form.submit()

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count * 2
    assert EnumItem.objects.count() == original_enum_item_count * 2
    assert Enum.objects.count() == original_enum_count * 2
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count * 2


def test_publishing_enum_without_property_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    model = ModelFactory(dataset=dataset, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=model,
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        access=3,
        metadata_version=version,
    )
    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        metadata_version=version,
    )
    enum_item = EnumItemFactory(
        enum=enum,
        metadata_version=version,
    )
    enum_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title="Test value",
        description="For testing",
        prepare="1",
        access=Metadata.OPEN,
        source="TEST",
        metadata_version=version,
    )

    original_metadata_count = 4
    original_enum_item_count = 1
    original_enum_count = 1
    original_version_count = 1

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert EnumItem.objects.count() == original_enum_item_count
    assert Enum.objects.count() == original_enum_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, enum_meta.pk]
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert (
        response.context["form"].errors["__all__"][0]
        == "Laukas 1 turi nuorodą į nepublikuojamą lauką tame pačiame duomenų ištekliuje."
    )

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert EnumItem.objects.count() == original_enum_item_count
    assert Enum.objects.count() == original_enum_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count


def test_publishing_model_with_base_duplicates_model_and_base(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        uri="dcat:TestModel",
        metadata_version=version,
    )
    base_model = ModelFactory(dataset=dataset, metadata_version=version)
    base_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(base_model),
        object_id=base_model.pk,
        dataset=dataset,
        name="test/dataset/BaseModel",
        metadata_version=version,
    )
    base = BaseFactory(
        model=base_model,
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(base),
        object_id=base.pk,
        dataset=dataset,
        name="test/dataset/BaseModel",
        metadata_version=version,
    )

    model.base = base
    model.save()

    original_metadata_count = 4
    original_model_count = 2
    original_base_count = 1
    original_version_count = 1

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Model.objects.filter(dataset=dataset).count() == original_model_count
    assert Base.objects.count() == original_base_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, base_model_meta.pk, model_meta.pk]
    form.submit()

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count * 2
    assert Model.objects.filter(dataset=dataset).count() == original_model_count * 2
    assert Base.objects.count() == original_base_count * 2
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count * 2


def test_publishing_model_with_without_base_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    model = ModelFactory(dataset=dataset, metadata_version=version)
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        uri="dcat:TestModel",
        metadata_version=version,
    )
    base_model = ModelFactory(dataset=dataset, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(base_model),
        object_id=base_model.pk,
        dataset=dataset,
        name="test/dataset/BaseModel",
        metadata_version=version,
    )
    base = BaseFactory(
        model=base_model,
        metadata_version=version,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(base),
        object_id=base.pk,
        dataset=dataset,
        name="test/dataset/BaseModel",
        metadata_version=version,
    )

    model.base = base
    model.save()

    original_metadata_count = 4
    original_model_count = 2
    original_base_count = 1
    original_version_count = 1

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Model.objects.filter(dataset=dataset).count() == original_model_count
    assert Base.objects.count() == original_base_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, model_meta.pk]
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert "laukas test/dataset/BaseModel turi nuorodą į jį." in response.context["form"].errors["__all__"][0]

    assert Metadata.objects.filter(dataset=dataset).count() == original_metadata_count
    assert Model.objects.filter(dataset=dataset).count() == original_model_count
    assert Base.objects.count() == original_base_count
    assert _Version.objects.filter(dataset=dataset).count() == original_version_count


def test_publishing_property_with_ref_to_another_model(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/govsssss/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "3,,,,City,,,,,,5,,,,,,,City,,\n"
        "4,,,,,id,ref,Country,,,5,,,,,,,Id,,\n"
        "8,,,,Country,,,,,,4,,,,,,,Country,,\n"
    )

    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure, structure.dataset.metadata.first().metadata_version)

    original_metadata_count = 4
    original_model_count = 2
    original_property_count = 1
    original_version_count = 1

    assert Metadata.objects.filter(dataset=structure.dataset).count() == original_metadata_count
    assert Model.objects.filter(dataset=structure.dataset).count() == original_model_count
    assert Property.objects.count() == original_property_count
    assert _Version.objects.filter(dataset=structure.dataset).count() == original_version_count

    publish_metadata = list(
        Metadata.objects.filter(
            dataset=structure.dataset, name__in=["datasets/govsssss/ivpk/adp", "datasets/govsssss/ivpk/adp/City", "id"]
        ).values_list("pk", flat=True)
    )
    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = publish_metadata
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert (
        response.context["form"].errors["__all__"][0]
        == "Laukas Country privalo būti publikuojamas, nes laukas id turi nuorodą į jį."
    )

    assert Metadata.objects.filter(dataset=structure.dataset).count() == original_metadata_count
    assert Model.objects.filter(dataset=structure.dataset).count() == original_model_count
    assert Property.objects.count() == original_property_count
    assert _Version.objects.filter(dataset=structure.dataset).count() == original_version_count


def test_publishing_property_with_ref_to_another_property(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/govsssss/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "3,,,,City,,,,,,5,,,,,,,City,,\n"
        "4,,,,,country,integer,Country,,,5,,,,,,,country_prop,,\n"
        "5,,,,,country.id,integer,,,,5,,,,,,,country_id,,\n"
        "8,,,,Country,,,,,,4,,,,,,,Country,,\n"
    )

    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure, structure.dataset.metadata.first().metadata_version)

    assert Metadata.objects.filter(dataset=structure.dataset).count() == 5
    assert Model.objects.filter(dataset=structure.dataset).count() == 2
    assert Property.objects.count() == 2
    assert _Version.objects.filter(dataset=structure.dataset).count() == 1

    publish_metadata = list(
        Metadata.objects.filter(
            dataset=structure.dataset,
            name__in=[
                "datasets/govsssss/ivpk/adp",
                "datasets/govsssss/ivpk/adp/City",
                "datasets/govsssss/ivpk/adp/Country",
                "country.id",
            ],
        ).values_list("pk", flat=True)
    )
    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = publish_metadata
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert (
        "Laukas country privalo būti publikuojamas, nes laukas country.id turi nuorodą į jį."
        in response.context["form"].errors["__all__"][0]
    )


def test_publishing_model_with_base_from_published_version_same_dataset(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/govsssss/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "3,,,,City,,,,,,5,,,,,,,City,,\n"
        "8,,,,Country,,,,,,4,,,,,,,Country,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure, structure.dataset.metadata.first().metadata_version)

    assert Metadata.objects.filter(dataset=structure.dataset).count() == 3
    assert Model.objects.filter(dataset=structure.dataset).count() == 2
    assert Base.objects.count() == 0

    publish_metadata = list(
        Metadata.objects.filter(
            dataset=structure.dataset, name__in=["datasets/govsssss/ivpk/adp", "datasets/govsssss/ivpk/adp/City"]
        ).values_list("pk", flat=True)
    )
    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = publish_metadata
    form.submit()

    assert Metadata.objects.filter(dataset=structure.dataset).count() == 5
    assert Model.objects.filter(dataset=structure.dataset).count() == 3
    assert Base.objects.count() == 0

    published_version = _Version.objects.filter(dataset=structure.dataset).order_by("-created").first()
    base_model = Model.objects.filter(dataset=structure.dataset, metadata_version=published_version).first()

    form = app.get(reverse("model-update", args=[structure.dataset.pk, version.pk, "Country"])).forms["model-form"]
    form["base"].force_value(str(base_model.pk))
    form.submit()

    assert Metadata.objects.filter(dataset=structure.dataset).count() == 6
    assert Base.objects.count() == 1

    publish_metadata = list(
        Metadata.objects.filter(
            dataset=structure.dataset, name__in=["datasets/govsssss/ivpk/adp", "datasets/govsssss/ivpk/adp/Country"]
        ).values_list("pk", flat=True)
    )

    form = app.get(reverse("version-create", args=[structure.dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = publish_metadata
    form.submit()
    published_version = _Version.objects.filter(dataset=structure.dataset).order_by("-created").first()
    published_model = Model.objects.filter(dataset=structure.dataset, metadata_version=published_version).first()

    assert base_model.pk == published_model.base.model.pk
    assert Metadata.objects.filter(dataset=structure.dataset).count() == 9
    assert Model.objects.filter(dataset=structure.dataset).count() == 4
    assert Base.objects.count() == 2


def test_publishing_model_with_base_from_published_version_different_dataset(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    first_dataset = DatasetFactory()
    first_version = first_dataset.metadata.first().metadata_version
    first_dataset_meta = first_dataset.metadata.first()
    first_model = ModelFactory(dataset=first_dataset, metadata_version=first_version)
    first_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(first_model),
        object_id=first_model.pk,
        dataset=first_dataset,
        name="test/dataset/TestModel1",
        metadata_version=first_version,
    )

    second_dataset = DatasetFactory()
    second_version = second_dataset.metadata.first().metadata_version
    second_dataset_meta = second_dataset.metadata.first()
    second_model = ModelFactory(dataset=second_dataset, metadata_version=second_version)
    second_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(second_model),
        object_id=second_model.pk,
        dataset=second_dataset,
        name="test/dataset/TestModel2",
        metadata_version=second_version,
    )

    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 4
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 2
    assert _Version.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 2
    assert Base.objects.count() == 0

    form = app.get(reverse("version-create", args=[first_dataset.pk, first_version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [first_dataset_meta.pk, first_model_meta.pk]
    form.submit()

    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 6
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 3
    assert _Version.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 3
    assert Base.objects.count() == 0

    first_published_version = _Version.objects.filter(dataset=first_dataset).order_by("-created").first()
    first_published_model = Model.objects.filter(
        dataset=first_dataset, metadata_version=first_published_version
    ).first()

    form = app.get(reverse("model-update", args=[second_dataset.pk, second_version.pk, "TestModel2"])).forms[
        "model-form"
    ]
    form["base"].force_value(str(first_published_model.pk))
    form.submit()

    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 7
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 3
    assert _Version.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 3
    assert Base.objects.count() == 1

    form = app.get(reverse("version-create", args=[second_dataset.pk, second_version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [second_dataset_meta.pk, second_model_meta.pk]
    form.submit()
    published_version = _Version.objects.filter(dataset=second_dataset).order_by("-created").first()
    published_model_with_base = Model.objects.filter(dataset=second_dataset, metadata_version=published_version).first()

    assert first_published_model.pk == published_model_with_base.base.model.pk
    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 10
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 4
    assert _Version.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 4
    assert Base.objects.count() == 2


def test_publishing_model_with_base_from_draft_version_different_dataset(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    first_dataset = DatasetFactory()
    first_version = first_dataset.metadata.first().metadata_version
    first_dataset.metadata.first()
    first_model = ModelFactory(dataset=first_dataset, metadata_version=first_version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(first_model),
        object_id=first_model.pk,
        dataset=first_dataset,
        name="test/dataset/TestModel1",
        metadata_version=first_version,
    )

    second_dataset = DatasetFactory()
    second_version = second_dataset.metadata.first().metadata_version
    second_dataset_meta = second_dataset.metadata.first()
    second_model = ModelFactory(dataset=second_dataset, metadata_version=second_version)
    second_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(second_model),
        object_id=second_model.pk,
        dataset=second_dataset,
        name="test/dataset/TestModel2",
        metadata_version=second_version,
    )

    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 4
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 2
    assert _Version.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 2
    assert Base.objects.count() == 0

    form = app.get(reverse("model-update", args=[second_dataset.pk, second_version.pk, "TestModel2"])).forms[
        "model-form"
    ]
    form["base"].force_value(str(first_model.pk))
    form.submit()
    second_model.refresh_from_db()

    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 5
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 2
    assert _Version.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 2
    assert Base.objects.count() == 1

    form = app.get(reverse("version-create", args=[second_dataset.pk, second_version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [second_dataset_meta.pk, second_model_meta.pk]
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert (
        response.context["form"].errors["__all__"][0]
        == "Laukas test/dataset/TestModel1 turi nuorodą į nepublikuotą lauką kitame duomenų ištekliuje."
    )


def test_publishing_property_with_published_model_ref_same_dataset(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    first_model = ModelFactory(dataset=dataset, metadata_version=version)
    first_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(first_model),
        object_id=first_model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=version,
    )
    second_model = ModelFactory(dataset=dataset, metadata_version=version)
    second_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(second_model),
        object_id=second_model.pk,
        dataset=dataset,
        name="test/dataset/TestModel2",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=second_model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop2",
        type="ref",
        access=3,
        metadata_version=version,
    )

    assert Metadata.objects.filter(dataset=dataset).count() == 4
    assert Property.objects.count() == 1
    assert Model.objects.filter(dataset=dataset).count() == 2

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, first_model_meta.pk]
    form.submit()
    published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    first_published_model = Model.objects.filter(metadata_version=published_version).first()

    assert Metadata.objects.filter(dataset=dataset).count() == 6
    assert Property.objects.count() == 1
    assert Model.objects.filter(dataset=dataset).count() == 3

    property_form = app.get(reverse("property-update", args=[dataset.pk, version.pk, "TestModel2", "prop2"])).forms[
        "property-form"
    ]
    property_form["ref"].force_value(str(first_published_model.pk))
    property_form.submit()
    prop.refresh_from_db()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, second_model_meta.pk, prop_meta.pk]
    form.submit()

    published_version = _Version.objects.filter(dataset=dataset).order_by("-created").first()
    second_published_property = Property.objects.filter(metadata_version=published_version).first()

    assert first_published_model.pk == second_published_property.ref_model_id
    assert Metadata.objects.filter(dataset=dataset).count() == 9
    assert Property.objects.count() == 2
    assert Model.objects.filter(dataset=dataset).count() == 4


def test_publishing_property_with_published_model_ref_different_dataset(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    first_dataset = DatasetFactory()
    first_version = first_dataset.metadata.first().metadata_version
    first_dataset_meta = first_dataset.metadata.first()
    first_model = ModelFactory(dataset=first_dataset, metadata_version=first_version)
    first_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(first_model),
        object_id=first_model.pk,
        dataset=first_dataset,
        name="test/dataset/TestModel1",
        metadata_version=first_version,
    )

    second_dataset = DatasetFactory()
    second_version = second_dataset.metadata.first().metadata_version
    second_dataset_meta = second_dataset.metadata.first()
    second_model = ModelFactory(dataset=second_dataset, metadata_version=second_version)
    second_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(second_model),
        object_id=second_model.pk,
        dataset=second_dataset,
        name="test/dataset/TestModel2",
        metadata_version=second_version,
    )
    prop = PropertyFactory(
        model=second_model,
        metadata_version=second_version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=second_dataset,
        name="prop2",
        type="ref",
        access=3,
        metadata_version=second_version,
    )

    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 5
    assert Property.objects.count() == 1
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 2

    form = app.get(reverse("version-create", args=[first_dataset.pk, first_version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [first_dataset_meta.pk, first_model_meta.pk]
    form.submit()
    published_version = _Version.objects.filter(dataset=first_dataset).order_by("-created").first()
    first_published_model = Model.objects.filter(metadata_version=published_version).first()

    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 7
    assert Property.objects.count() == 1
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 3

    property_form = app.get(
        reverse("property-update", args=[second_dataset.pk, second_version.pk, "TestModel2", "prop2"])
    ).forms["property-form"]
    property_form["ref"].force_value(str(first_published_model.pk))
    property_form.submit()
    prop.refresh_from_db()

    form = app.get(reverse("version-create", args=[second_dataset.pk, second_version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [second_dataset_meta.pk, second_model_meta.pk, prop_meta.pk]
    form.submit()

    published_version = _Version.objects.filter(dataset=second_dataset).order_by("-created").first()
    second_published_property = Property.objects.filter(metadata_version=published_version).first()

    assert first_published_model.pk == second_published_property.ref_model_id
    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 10
    assert Property.objects.count() == 2
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 4


def test_publishing_property_with_draft_model_ref_same_dataset(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = dataset.metadata.first().metadata_version
    dataset_meta = dataset.metadata.first()
    first_model = ModelFactory(dataset=dataset, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(first_model),
        object_id=first_model.pk,
        dataset=dataset,
        name="test/dataset/TestModel1",
        metadata_version=version,
    )

    second_model = ModelFactory(dataset=dataset, metadata_version=version)
    second_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(second_model),
        object_id=second_model.pk,
        dataset=dataset,
        name="test/dataset/TestModel2",
        metadata_version=version,
    )
    prop = PropertyFactory(
        model=second_model,
        metadata_version=version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop2",
        type="ref",
        access=3,
        metadata_version=version,
    )

    assert Metadata.objects.filter(dataset=dataset).count() == 4
    assert Property.objects.count() == 1
    assert Model.objects.filter(dataset=dataset).count() == 2

    property_form = app.get(reverse("property-update", args=[dataset.pk, version.pk, "TestModel2", "prop2"])).forms[
        "property-form"
    ]
    property_form["ref"].force_value(str(first_model.pk))
    property_form.submit()
    prop.refresh_from_db()

    form = app.get(reverse("version-create", args=[dataset.pk, version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [dataset_meta.pk, second_model_meta.pk, prop_meta.pk]
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert (
        response.context["form"].errors["__all__"][0]
        == "Laukas TestModel1 privalo būti publikuojamas, nes laukas prop2 turi nuorodą į jį."
    )


def test_publishing_property_with_draft_model_ref_different_dataset(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    first_dataset = DatasetFactory()
    first_version = first_dataset.metadata.first().metadata_version
    first_dataset.metadata.first()
    first_model = ModelFactory(dataset=first_dataset, metadata_version=first_version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(first_model),
        object_id=first_model.pk,
        dataset=first_dataset,
        name="test/dataset/TestModel1",
        metadata_version=first_version,
    )

    second_dataset = DatasetFactory()
    second_version = second_dataset.metadata.first().metadata_version
    second_dataset_meta = second_dataset.metadata.first()
    second_model = ModelFactory(dataset=second_dataset, metadata_version=second_version)
    second_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(second_model),
        object_id=second_model.pk,
        dataset=second_dataset,
        name="test/dataset/TestModel2",
        metadata_version=second_version,
    )
    prop = PropertyFactory(
        model=second_model,
        metadata_version=second_version,
    )
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=second_dataset,
        name="prop2",
        type="ref",
        access=3,
        metadata_version=second_version,
    )

    assert Metadata.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 5
    assert Property.objects.count() == 1
    assert Model.objects.filter(dataset__in=[first_dataset, second_dataset]).count() == 2

    property_form = app.get(
        reverse("property-update", args=[second_dataset.pk, second_version.pk, "TestModel2", "prop2"])
    ).forms["property-form"]
    property_form["ref"].force_value(str(first_model.pk))
    property_form.submit()
    prop.refresh_from_db()

    form = app.get(reverse("version-create", args=[second_dataset.pk, second_version.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form["metadata"] = [second_dataset_meta.pk, second_model_meta.pk, prop_meta.pk]
    response = form.submit()

    assert response.status_code == 200
    assert response.context["form"].errors
    assert (
        response.context["form"].errors["__all__"][0]
        == "Laukas prop2 turi nuorodą į nepublikuotą lauką kitame duomenų ištekliuje."
    )


@pytest.mark.django_db
class TestModelDelete:
    def test_success(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        metadata_version = dataset.metadata.first().metadata_version
        model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
        MetadataFactory(
            dataset=dataset,
            content_type=ContentType.objects.get_for_model(Model),
            object_id=model.pk,
            name=f"{dataset}/{model.pk}/TestModel",
            metadata_version=metadata_version,
        )

        resp = app.post(reverse("model-delete", args=[dataset.pk, metadata_version.pk, "TestModel"]))
        assert resp.json == {"success": True}
        assert not Model.objects.filter(pk=model.pk).exists()

    def test_permission_denied(self, app: DjangoTestApp):
        user = UserFactory(is_staff=False)
        app.set_user(user)
        dataset = DatasetFactory()
        metadata_version = dataset.metadata.first().metadata_version
        model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
        MetadataFactory(
            dataset=dataset,
            content_type=ContentType.objects.get_for_model(Model),
            object_id=model.pk,
            name=f"{dataset}/{model.pk}/TestModel",
            metadata_version=metadata_version,
        )

        resp = app.post(
            reverse("model-delete", args=[dataset.pk, metadata_version.pk, "TestModel"]), expect_errors=True
        )
        assert resp.status_code == 403
        assert resp.json == {"error": "Permission denied"}
        assert Model.objects.filter(pk=model.pk).exists()

    @pytest.mark.parametrize("status", [s for s in VersionStatus.values if s != VersionStatus.DRAFT])
    def test_delete_on_not_draft_version(self, app: DjangoTestApp, status: str):
        user = UserFactory(is_staff=False)
        app.set_user(user)
        dataset = DatasetFactory()
        metadata_version = dataset.metadata.first().metadata_version
        metadata_version.status = status
        model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
        MetadataFactory(
            dataset=dataset,
            content_type=ContentType.objects.get_for_model(Model),
            object_id=model.pk,
            name=f"{dataset}/{model.pk}/TestModel",
            metadata_version=metadata_version,
        )

        resp = app.post(
            reverse("model-delete", args=[dataset.pk, metadata_version.pk, "TestModel"]), expect_errors=True
        )
        assert resp.status_code == 403
        assert resp.json == {"error": "Permission denied"}
        assert Model.objects.filter(pk=model.pk).exists()

    def test_not_found(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        metadata_version = dataset.metadata.first().metadata_version
        resp = app.post(
            reverse("model-delete", args=[dataset.pk, metadata_version.pk, "NonExistent"]), expect_errors=True
        )
        assert resp.status_code == 404

    def test_requires_login(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        metadata_version = dataset.metadata.first().metadata_version
        model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
        MetadataFactory(
            dataset=dataset,
            content_type=ContentType.objects.get_for_model(Model),
            object_id=model.pk,
            name=f"{dataset}/{model.pk}/TestModel",
            metadata_version=metadata_version,
        )

        resp = app.post(reverse("model-delete", args=[dataset.pk, metadata_version.pk, "TestModel"]))
        assert resp.status_code == 302  # redirect to login
        assert Model.objects.filter(pk=model.pk).exists()

    def test_deletes_related_metadata(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        metadata_version = dataset.metadata.first().metadata_version
        model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
        metadata = MetadataFactory(
            dataset=dataset,
            content_type=ContentType.objects.get_for_model(Model),
            object_id=model.pk,
            name=f"{dataset}/{model.pk}/TestModel",
            metadata_version=metadata_version,
        )

        app.post(reverse("model-delete", args=[dataset.pk, metadata_version.pk, "TestModel"]))

        assert not Model.objects.filter(pk=model.pk).exists()
        assert not Metadata.objects.filter(pk=metadata.pk).exists()

    def test_get_method_not_allowed(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        metadata_version = dataset.metadata.first().metadata_version
        model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
        MetadataFactory(
            dataset=dataset,
            content_type=ContentType.objects.get_for_model(Model),
            object_id=model.pk,
            name=f"{dataset}/{model.pk}/TestModel",
            metadata_version=metadata_version,
        )

        resp = app.get(reverse("model-delete", args=[dataset.pk, metadata_version.pk, "TestModel"]), expect_errors=True)
        assert resp.status_code == 405


class TestStructure(BaseTestCreateManifest):
    def test_import_and_export_does_not_strip_ref_property_source_prefixes(self, app: DjangoTestApp):
        """The problem is that type `ref` property.ref removed prefixes `/`, they should not be removed.

        Incorrect: `/datasets/gov/ref/dataset/Continent` -> `datasets/gov/ref/dataset/Continent`
        Correct:   `/datasets/gov/ref/dataset/Continent` -> `/datasets/gov/ref/dataset/Continent`
        """
        user = UserFactory(is_staff=True)
        app.set_user(user)

        manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\n"
            '3,,,,Country,,,"id,title",,,,,,,,,,,\n'
            "4,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "5,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,5,,,open,dct:continent,,,,\n"
        )
        dataset = self._create_manifest(manifest, "Dataset", "Dataset with ref property")

        response = app.get(reverse("dataset-structure-export", args=[dataset.pk, dataset.latest_version().pk]))

        assert response.status_code == HTTPStatus.OK
        assert response.text.splitlines() == [
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description",
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,,Dataset,Dataset with ref property",
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,",
            "3,,,,Country,,,id,,,,,,,develop,,,,,,",
            "4,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,",
            "5,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,,,,5,develop,,open,dct:continent,,,",
            ",,,,,,,,,,,,,,,,,,,,",
        ]

    def test_export__resource_and_param_rows_exported_with_all_columns(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\n"
            "1,dataset,,,,,,,,,,,,,,,,,,,\n"
            "2,,resource_wsdl,,,,wsdl,,http://127.0.0.1:8001/api/v1/test/testing/?wsdl,,,,,,,,,,,,\n"
            "3,,resource_soap,,,,soap,,TestTesting.TestPort.TestPort.test,,wsdl(rc_wsdl),,,,,,,,,,\n"
            "4,,,,,,param,action_type,input/ActionType,,input(),,,,,,,,,,\n"
            "5,,,,Soap,,,,/,,,,,,,,open,,,,\n"
            "6,,,,,response_data,string,,ResponseData,,base64(),,,,,,,,,,\n"
            "7,,,,,action_type,string required,,,,param(action_type),,,,,,,,,,\n"
            ",,,,,,,,,,,,,,,,,,,,\n"
            "8,,resource_xml,,,,dask/xml,,,,eval(param(nested_xml)),,,,,,,\n"
            "9,,,,,,param,nested_xml,Soap,,read().response_data,,,,,,,\n"
            "10,,,,Approver,,,,,,,,,0,,,,,,Approver,\n"
            "11,,,,,company_name,string,,ApproverCompanyName/text(),,,,,4,,,,,,,\n"
        )
        dataset = self._create_manifest(manifest, "Title", "Description")

        response = app.get(reverse("dataset-structure-export", args=[dataset.pk, dataset.latest_version().pk]))

        assert response.status_code == HTTPStatus.OK
        assert response.text.splitlines() == [
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description",
            "1,dataset,,,,,,,,,,,,,,,,,,Title,Description",
            "2,,resource_wsdl,,,,wsdl,,http://127.0.0.1:8001/api/v1/test/testing/?wsdl,,,,,,,,,,,resource_wsdl,",
            "3,,resource_soap,,,,soap,,TestTesting.TestPort.TestPort.test,,wsdl(rc_wsdl),,,,,,,,,resource_soap,",
            "4,,,,,,param,action_type,input/ActionType,,input(),,,,develop,,,,,,",
            "5,,,,Soap,,,,/,,,,,,develop,,open,,,,",
            "6,,,,,response_data,string,,ResponseData,,base64(),,,,develop,,,,,,",
            "7,,,,,action_type,string required,,,,param(action_type),,,,develop,,,,,,",
            ",,,,,,,,,,,,,,,,,,,,",
            ",,/,,,,,,,,,,,,,,,,,,",
            "8,,resource_xml,,,,dask/xml,,,,eval(param(nested_xml)),,,,,,,,,resource_xml,",
            "9,,,,,,param,nested_xml,Soap,,read().response_data,,,,develop,,,,,,",
            "10,,,,Approver,,,,,,,,,0,develop,,,,,Approver,",
            "11,,,,,company_name,string,,ApproverCompanyName/text(),,,,,4,develop,,,,,,",
            ",,,,,,,,,,,,,,,,,,,,",
        ]

    def test_export__repeat_import_correctly_updates_manifest_rows(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        manifest_no_prepare = (
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\n"
            "1,dataset,,,,,,,,,,,,,,,,,,,\n"
            "2,,service,,,,dask/xml,,,,,,,,,,,,,\n"
        )
        dataset = self._create_manifest(manifest_no_prepare, "Title", "Description")
        version = dataset.latest_version()

        manifest_with_prepare = (
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\n"
            "1,dataset,,,,,,,,,,,,,,,,,,,\n"
            "2,,service,,,,dask/xml,,,,eval(param(nested_xml)),,,,,,,,\n"
        )

        # Second import to test updates
        structure = DatasetStructureFactory(
            file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest_with_prepare)), dataset=dataset
        )
        dataset.current_structure = structure
        dataset.save()
        create_structure_objects(structure, metadata_version=version)

        response = app.get(reverse("dataset-structure-export", args=[dataset.pk, version.pk]))

        assert response.status_code == HTTPStatus.OK
        assert response.text.splitlines() == [
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description",
            "1,dataset,,,,,,,,,,,,,,,,,,Title,Description",
            "2,,service,,,,dask/xml,,,,eval(param(nested_xml)),,,,,,,,,service,",
        ]

    def test_export__duplicated_source_exports_resources_correctly(self, app: DjangoTestApp):
        """Ensure that resources that have an identical source column value are exported correctly."""
        user = UserFactory(is_staff=True)
        app.set_user(user)

        manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            "1,dataset,,,,,dataset,,,,,,,,,,,\n"
            "2,,nested_read,,,,dask/xml,,,eval(param(nested_xml)),,,,,,,,\n"
            "3,,,,,,param,nested_xml,GetData,read().response_data,,,,,,,,\n"
            "4,,,,,,param,action_type,input/ActionType,input(),,,,,,,,\n"
            "5,,,,Country,,,,countries/countryData,,,,,open,,,,\n"
            "6,,,,,id,string,,id,,,,,,,,,\n"
            ",,,,,,,,,,,,,,,,,\n"
            "7,,nested_read_multiple,,,,dask/xml,,,eval(param(nested_xml)),,,,,,,,\n"
            "8,,,,,,param,nested_xml,GetDataMultiple,read().response_data,,,,,,,,\n"
            "9,,,,CountryMultiple,,,,countries/countryData,,,,,public,,,,\n"
            "10,,,,,id,string,,id,,,,,,,,,\n"
            ",,,,,,,,,,,,,,,,,\n"
        )
        dataset = self._create_manifest(manifest, "Dataset", "Dataset with ref property")

        response = app.get(reverse("dataset-structure-export", args=[dataset.pk, dataset.latest_version().pk]))

        assert response.status_code == HTTPStatus.OK
        assert response.text.splitlines() == [
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description",
            "1,dataset,,,,,,,,,,,,,,,,,,Dataset,Dataset with ref property",
            "2,,nested_read,,,,dask/xml,,,,eval(param(nested_xml)),,,,,,,,,nested_read,",
            "3,,,,,,param,nested_xml,GetData,,read().response_data,,,,develop,,,,,,",
            "4,,,,,,param,action_type,input/ActionType,,input(),,,,develop,,,,,,",
            "5,,,,Country,,,,countries/countryData,,,,,,develop,,open,,,,",
            "6,,,,,id,string,,id,,,,,,develop,,,,,,",
            ",,,,,,,,,,,,,,,,,,,,",
            ",,/,,,,,,,,,,,,,,,,,,",
            "7,,nested_read_multiple,,,,dask/xml,,,,eval(param(nested_xml)),,,,,,,,,nested_read_multiple,",
            "8,,,,,,param,nested_xml,GetDataMultiple,,read().response_data,,,,develop,,,,,,",
            "9,,,,CountryMultiple,,,,countries/countryData,,,,,,develop,,public,,,,",
            "10,,,,,id,string,,id,,,,,,develop,,,,,,",
            ",,,,,,,,,,,,,,,,,,,,",
        ]

    def test_export__model_and_reference_as_base_in_file(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            "1,example,,,,,,,,,,,,,,,,\n"
            "2,,,,Animal,,,,,,0,completed,public,,,,,\n"
            "3,,,,,id,string,,source_animal_id,,4,completed,package,protected,,,,\n"
            "4,,,Animal,,,,,,,1,completed,public,,,,,\n"
            "5,,,,Dog,,,,,,0,completed,public,,,,,\n"
            "6,,,,,action,string,,source_dog_action,,4,completed,package,protected,,,,\n"
            ",,,/,,,,,,,,,,,,,,\n"
        )

        dataset = self._create_manifest(manifest, "Dataset", "Dataset with ref property")

        response = app.get(reverse("dataset-structure-export", args=[dataset.pk, dataset.latest_version().pk]))

        assert response.status_code == HTTPStatus.OK
        assert response.text.splitlines() == [
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description",
            "1,example,,,,,,,,,,,,,,,,,,Dataset,Dataset with ref property",
            "2,,,,Animal,,,,,,,,,0,completed,public,,,,,",
            "3,,,,,id,string,,source_animal_id,,,,,4,completed,package,protected,,,,",
            ",,,,,,,,,,,,,,,,,,,,",
            "4,,,Animal,,,,,,,,,,,,,,,,,",
            "5,,,,Dog,,,,,,,,,0,completed,public,,,,,",
            "6,,,,,action,string,,source_dog_action,,,,,4,completed,package,protected,,,,",
            ",,,,,,,,,,,,,,,,,,,,",
        ]

    def test_export__model_and_reference_as_base_in_two_different_files(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        model_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            "1,example,,,,,,,,,,,,,,,,\n"
            "2,,,,Animal,,,,,,0,completed,public,,,,,\n"
            "3,,,,,id,string,,source_animal_id,,4,completed,package,protected,,,,\n"
        )
        model_dataset = self._create_manifest(model_manifest, "Model Dataset", "Dataset that defines base model.")
        model_version = model_dataset.latest_version()
        model_version.status = VersionStatus.STABLE
        model_version.save()

        base_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            "1,example2,,,,,,,,,,,,,,,,\n"
            "2,,,example/Animal,,,,,,,1,completed,public,,,,,\n"
            "3,,,,Dog,,,,,,0,completed,public,,,,,\n"
            "4,,,,,action,string,,source_dog_action,,4,completed,package,protected,,,,\n"
            ",,,/,,,,,,,,,,,,,,\n"
        )
        dataset = self._create_manifest(base_manifest, "Base Dataset", "Dataset that references model with base")

        response = app.get(reverse("dataset-structure-export", args=[dataset.pk, dataset.latest_version().pk]))

        assert response.status_code == HTTPStatus.OK
        assert response.text.splitlines() == [
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description",
            "1,example2,,,,,,,,,,,,,,,,,,Base Dataset,Dataset that references model with base",
            "2,,,example/Animal,,,,,,,,,,,,,,,,,",
            "3,,,,Dog,,,,,,,,,0,completed,public,,,,,",
            "4,,,,,action,string,,source_dog_action,,,,,4,completed,package,protected,,,,",
            ",,,,,,,,,,,,,,,,,,,,",
        ]

    def test_export__model_and_reference_different_files_model_is_not_released(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        model_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            "1,example,,,,,,,,,,,,,,,,\n"
            "2,,,,Animal,,,,,,0,completed,public,,,,,\n"
            "3,,,,,id,string,,source_animal_id,,4,completed,package,protected,,,,\n"
        )
        self._create_manifest(model_manifest, "Model Dataset", "Dataset that defines base model.")

        base_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            "1,example2,,,,,,,,,,,,,,,,\n"
            "2,,,example/Animal,,,,,,,1,completed,public,,,,,\n"
            "3,,,,Dog,,,,,,0,completed,public,,,,,\n"
            "4,,,,,action,string,,source_dog_action,,4,completed,package,protected,,,,\n"
            ",,,/,,,,,,,,,,,,,,\n"
        )
        dataset = self._create_manifest(base_manifest, "Base Dataset", "Dataset that references model with base")

        response = app.get(reverse("dataset-structure-export", args=[dataset.pk, dataset.latest_version().pk]))

        assert response.status_code == HTTPStatus.OK
        assert response.text.splitlines() == [
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description",
            "1,example2,,,,,,,,,,,,,,,,,,Base Dataset,Dataset that references model with base",
            "3,,,,Dog,,,,,,,,,0,completed,public,,,,,",
            "4,,,,,action,string,,source_dog_action,,,,,4,completed,package,protected,,,,",
            ",,,,,,,,,,,,,,,,,,,,",
        ]

        error_comment = Comment.objects.get(content_type=ContentType.objects.get_for_model(Model))
        assert error_comment.type == Comment.STRUCTURE_ERROR
        assert error_comment.body == (
            "Nepavyko susieti bazinio modelio „example/Animal“. "
            "Įsitikinkite, kad jis egzistuoja ir turi patvirtintą (stabilią) versiją."
        )

    def test_export__base_reference_without_defined_model(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            "1,example,,,,,,,,,,,,,,,,\n"
            "2,,,Animal,,,,,,,1,completed,public,,,,,\n"
            "3,,,,Dog,,,,,,0,completed,public,,,,,\n"
            "4,,,,,action,string,,source_dog_action,,4,completed,package,protected,,,,\n"
            ",,,/,,,,,,,,,,,,,,\n"
        )

        dataset = self._create_manifest(manifest, "Dataset", "Dataset with ref property")

        response = app.get(reverse("dataset-structure-export", args=[dataset.pk, dataset.latest_version().pk]))

        assert response.status_code == HTTPStatus.OK
        assert response.text.splitlines() == [  # Base could not be linked, so it is missing.
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description",
            "1,example,,,,,,,,,,,,,,,,,,Dataset,Dataset with ref property",
            "3,,,,Dog,,,,,,,,,0,completed,public,,,,,",
            "4,,,,,action,string,,source_dog_action,,,,,4,completed,package,protected,,,,",
            ",,,,,,,,,,,,,,,,,,,,",
        ]

        error_comment = Comment.objects.get(content_type=ContentType.objects.get_for_model(Model))
        assert error_comment.type == Comment.STRUCTURE_ERROR
        assert error_comment.body == (
            "Nepavyko susieti bazinio modelio „example/Animal“. "
            "Įsitikinkite, kad jis egzistuoja ir turi patvirtintą (stabilią) versiją."
        )


class TestStructureExportDependentModels(BaseTestCreateManifest):
    @pytest.mark.django_db
    def test_structure_export_dependent_models(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        ref_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "7,datasets/gov/ref/dataset,,,,,,,,,,,,,,,,,\n"
            "8,,,,Continent,,,id,,,,,,,,,,,\n"
            "9,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "10,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        )
        ref_dataset = self._create_manifest(ref_manifest, "Referenced Dataset", "Dataset that will be referenced")

        main_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\n"
            '3,,,,Country,,,"id,title",,,,,,,,,,,\n'
            "4,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "5,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
            "6,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,5,,,open,dct:continent,,,,\n"
        )
        main_dataset = self._create_manifest(main_manifest, "Main Dataset", "Dataset with reference to other dataset")

        country_model = Model.objects.get(dataset=main_dataset, metadata__name="datasets/gov/main/dataset/Country")
        continent_model = Model.objects.get(dataset=ref_dataset, metadata__name="datasets/gov/ref/dataset/Continent")
        assert country_model is not None
        assert continent_model is not None

        assert Property.objects.filter(
            model=country_model,
            ref_model=continent_model,
        ).exists()

        resp = app.get(reverse("dataset-structure-export", args=[main_dataset.pk, main_dataset.latest_version().pk]))
        assert resp.text == (
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
            "7,datasets/gov/ref/dataset,,,,,,,,,,,,,,,,,,Referenced Dataset,Dataset that will be referenced\r\n"
            "8,,,,Continent,,,id,,,,,,,develop,,,,,,\r\n"
            "9,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,,Main Dataset,Dataset with reference to other dataset\r\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\r\n"
            '3,,,,Country,,,"id, title",,,,,,,develop,,,,,,\r\n'
            "4,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "5,,,,,title,string,,,,,,,5,develop,,open,dct:title,,,\r\n"
            "6,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,,,,5,develop,,open,dct:continent,,,\r\n"
            ",,,,,,,,,,,,,,,,,,,,\r\n"
        )

    @pytest.mark.django_db
    def test_structure_export_dependent_models_multiple_pk(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        ref_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "7,datasets/gov/ref/dataset,,,,,,,,,,,,,,,,,\n"
            '8,,,,Continent,,,"id, title",,,,,,,,,,,\n'
            "9,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "10,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
            "11,,,,,other,string,,,,5,,,open,dct:other,,,,\n"
        )
        self._create_manifest(ref_manifest, "Referenced Dataset", "Dataset that will be referenced")

        main_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\n"
            '3,,,,Country,,,"id,title",,,,,,,,,,,\n'
            "4,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "5,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
            "6,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,5,,,open,dct:continent,,,,\n"
        )
        main_dataset = self._create_manifest(main_manifest, "Main Dataset", "Dataset with reference to other dataset")

        resp = app.get(reverse("dataset-structure-export", args=[main_dataset.pk, main_dataset.latest_version().pk]))
        assert resp.text == (
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
            "7,datasets/gov/ref/dataset,,,,,,,,,,,,,,,,,,Referenced Dataset,Dataset that will be referenced\r\n"
            '8,,,,Continent,,,"id, title",,,,,,,develop,,,,,,\r\n'
            "9,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "10,,,,,title,string,,,,,,,5,develop,,open,dct:title,,,\r\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,,Main Dataset,Dataset with reference to other dataset\r\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\r\n"
            '3,,,,Country,,,"id, title",,,,,,,develop,,,,,,\r\n'
            "4,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "5,,,,,title,string,,,,,,,5,develop,,open,dct:title,,,\r\n"
            "6,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,,,,5,develop,,open,dct:continent,,,\r\n"
            ",,,,,,,,,,,,,,,,,,,,\r\n"
        )

    @pytest.mark.django_db
    def test_structure_export_dependent_models__depth_2(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        other_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "12,datasets/gov/other/dataset,,,,,,,,,,,,,,,,,\n"
            "13,,,,Other,,,title,,,,,,,,,,,\n"
            "14,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
            "15,,,,,other,string,,,,5,,,open,dct:other,,,,\n"
        )
        self._create_manifest(other_manifest, "Other Dataset", "Dependent dataset depth 2")
        ref_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "7,datasets/gov/ref/dataset,,,,,,,,,,,,,,,,,\n"
            '8,,,,Continent,,,"id, title",,,,,,,,,,,\n'
            "9,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "10,,,,,title,ref,/datasets/gov/other/dataset/Other,,,5,,,open,dct:title,,,,\n"
            "11,,,,,other,string,,,,5,,,open,dct:other,,,,\n"
        )
        self._create_manifest(ref_manifest, "Referenced Dataset", "Dependent dataset depth 1")

        main_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\n"
            '3,,,,Country,,,"id,title",,,,,,,,,,,\n'
            "4,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "5,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
            "6,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,5,,,open,dct:continent,,,,\n"
        )
        main_dataset = self._create_manifest(main_manifest, "Main Dataset", "Root dataset")

        resp = app.get(reverse("dataset-structure-export", args=[main_dataset.pk, main_dataset.latest_version().pk]))
        assert resp.text == (
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
            "12,datasets/gov/other/dataset,,,,,,,,,,,,,,,,,,Other Dataset,Dependent dataset depth 2\r\n"
            "13,,,,Other,,,title,,,,,,,develop,,,,,,\r\n"
            "14,,,,,title,string,,,,,,,5,develop,,open,dct:title,,,\r\n"
            "7,datasets/gov/ref/dataset,,,,,,,,,,,,,,,,,,Referenced Dataset,Dependent dataset depth 1\r\n"
            '8,,,,Continent,,,"id, title",,,,,,,develop,,,,,,\r\n'
            "9,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "10,,,,,title,ref,/datasets/gov/other/dataset/Other,,,,,,5,develop,,open,dct:title,,,\r\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,,Main Dataset,Root dataset\r\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\r\n"
            '3,,,,Country,,,"id, title",,,,,,,develop,,,,,,\r\n'
            "4,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "5,,,,,title,string,,,,,,,5,develop,,open,dct:title,,,\r\n"
            "6,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,,,,5,develop,,open,dct:continent,,,\r\n"
            ",,,,,,,,,,,,,,,,,,,,\r\n"
        )

    @pytest.mark.django_db
    def test_structure_export_dependent_models__ref_non_existent(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        main_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\n"
            '3,,,,Country,,,"id,title",,,,,,,,,,,\n'
            "4,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "5,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
            "6,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,5,,,open,dct:continent,,,,\n"
        )
        main_dataset = self._create_manifest(main_manifest, "Main Dataset", "Dataset with reference to other dataset")

        resp = app.get(reverse("dataset-structure-export", args=[main_dataset.pk, main_dataset.latest_version().pk]))
        assert resp.text == (
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,,Main Dataset,Dataset with reference to other dataset\r\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\r\n"
            '3,,,,Country,,,"id, title",,,,,,,develop,,,,,,\r\n'
            "4,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "5,,,,,title,string,,,,,,,5,develop,,open,dct:title,,,\r\n"
            "6,,,,,continent,ref,/datasets/gov/ref/dataset/Continent,,,,,,5,develop,,open,dct:continent,,,\r\n"
            ",,,,,,,,,,,,,,,,,,,,\r\n"
        )

    @pytest.mark.django_db
    def test_structure_export_dependent_models__with_base(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        ref_depth_1_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "7,datasets/gov/ref/d1,,,,,,,,,,,,,,,,,\n"
            "8,,,,D1BaseModel,,,id,,,,,,,,,,,\n"
            "9,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "10,,,,,prop1,string,,,,5,,,open,dct:prop1,,,,\n"
            "11,,,D1BaseModel,,,,,,,,,,,,,,\n"
            "12,,,,D1Model1,,,id,,,,,,,,,,,\n"
            "13,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "14,,,,,prop1,string,,,,5,,,open,dct:prop1,,,,\n"
            '15,,,,D1Model2,,,"id, prop2",,,,,,,,,,,\n'
            "16,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "17,,,,,prop2,string,,,,5,,,open,dct:prop2,,,,\n"
        )
        self._create_manifest(ref_depth_1_manifest, "Referenced Dataset", "Dataset with reference to other dataset")
        main_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\n"
            '3,,,,MainModel,,,"id,prop1",,,,,,,,,,,\n'
            "4,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
            "5,,,,,prop1,string,,,,5,,,open,dct:prop1,,,,\n"
            "6,,,,,prop2,ref,/datasets/gov/ref/d1/D1Model1,,,5,,,open,dct:prop2,,,,\n"
            "7,,,,,prop3,ref,/datasets/gov/ref/d1/D1Model2,,,5,,,open,dct:prop3,,,,\n"
        )
        main_dataset = self._create_manifest(main_manifest, "Main Dataset", "Dataset with reference to other dataset")
        resp = app.get(reverse("dataset-structure-export", args=[main_dataset.pk, main_dataset.latest_version().pk]))
        assert resp.text == (
            "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
            "7,datasets/gov/ref/d1,,,,,,,,,,,,,,,,,,Referenced Dataset,Dataset with reference to other dataset\r\n"
            "8,,,,D1BaseModel,,,id,,,,,,,develop,,,,,,\r\n"
            "9,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "11,,,D1BaseModel,,,,,,,,,,,,,,,,,\r\n"
            "12,,,,D1Model1,,,id,,,,,,,develop,,,,,,\r\n"
            "13,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            '15,,,,D1Model2,,,"id, prop2",,,,,,,develop,,,,,,\r\n'
            "16,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "17,,,,,prop2,string,,,,,,,5,develop,,open,dct:prop2,,,\r\n"
            "1,datasets/gov/main/dataset,,,,,,,,,,,,,,,,,,Main Dataset,Dataset with reference to other dataset\r\n"
            "2,,dataset,,,,,,https://get.data.gov.lt/datasets/gov/main/dataset/:ns,,,,,,,,,,,dataset,\r\n"
            '3,,,,MainModel,,,"id, prop1",,,,,,,develop,,,,,,\r\n'
            "4,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
            "5,,,,,prop1,string,,,,,,,5,develop,,open,dct:prop1,,,\r\n"
            "6,,,,,prop2,ref,/datasets/gov/ref/d1/D1Model1,,,,,,5,develop,,open,dct:prop2,,,\r\n"
            "7,,,,,prop3,ref,/datasets/gov/ref/d1/D1Model2,,,,,,5,develop,,open,dct:prop3,,,\r\n"
            ",,,,,,,,,,,,,,,,,,,,\r\n"
        )

    @pytest.mark.django_db
    def test_structure_export_dependent_models__non_pk_ref_not_followed(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        orphan_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "20,datasets/gov/orphan,,,,,,,,,,,,,,,,,\n"
            "21,,,,Orphan,,,id,,,,,,,,,,,\n"
            "22,,,,,id,integer,,,,5,,,open,,,,,\n"
        )
        self._create_manifest(orphan_manifest, "Orphan Dataset", "Should not be included")

        ref_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "10,datasets/gov/ref,,,,,,,,,,,,,,,,,\n"
            "11,,,,RefModel,,,id,,,,,,,,,,,\n"
            "12,,,,,id,integer,,,,5,,,open,,,,,\n"
            "13,,,,,non_pk_ref,ref,/datasets/gov/orphan/Orphan,,,5,,,open,,,,,\n"
        )
        self._create_manifest(ref_manifest, "Ref Dataset", "Has non-PK ref")

        main_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "1,datasets/gov/main,,,,,,,,,,,,,,,,,\n"
            "2,,,,Main,,,id,,,,,,,,,,,\n"
            "3,,,,,id,integer,,,,5,,,open,,,,,\n"
            "4,,,,,ref_prop,ref,/datasets/gov/ref/RefModel,,,5,,,open,,,,,\n"
        )
        main_dataset = self._create_manifest(main_manifest, "Main Dataset", "Root")

        resp = app.get(reverse("dataset-structure-export", args=[main_dataset.pk, main_dataset.latest_version().pk]))

        assert "datasets/gov/ref" in resp.text
        assert "RefModel" in resp.text
        assert "datasets/gov/orphan" not in resp.text
        assert "Orphan" not in resp.text

    @pytest.mark.django_db
    def test_structure_export_dependent_models__no_pk_included_but_no_traversal(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)

        orphan_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "20,datasets/gov/orphan,,,,,,,,,,,,,,,,,\n"
            "21,,,,OrphanModel,,,id,,,,,,,,,,,\n"
            "22,,,,,id,integer,,,,5,,,open,dct:identifier,,,,\n"
        )
        self._create_manifest(orphan_manifest, "Orphan Dataset", "Should NOT be included - no path through no-PK model")

        ref_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "10,datasets/gov/ref,,,,,,,,,,,,,,,,,\n"
            "11,,,,NoPkModel,,,,,,,,,,,,,,\n"  # No PK defined (empty ref column)
            "12,,,,,id,integer,,,,5,,,open,dct:identifier,,,,\n"
            "13,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
            "14,,,,,orphan_ref,ref,/datasets/gov/orphan/OrphanModel,,,5,,,open,dct:orphan,,,,\n"
        )
        self._create_manifest(ref_manifest, "Ref Dataset", "Has no PK, refs to orphan")

        main_manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
            "1,datasets/gov/main,,,,,,,,,,,,,,,,,\n"
            "2,,,,MainModel,,,id,,,,,,,,,,,\n"
            "3,,,,,id,integer,,,,5,,,open,dct:identifier,,,,\n"
            "4,,,,,no_pk_ref,ref,/datasets/gov/ref/NoPkModel,,,5,,,open,dct:ref,,,,\n"
        )
        main_dataset = self._create_manifest(main_manifest, "Main Dataset", "Root")

        resp = app.get(reverse("dataset-structure-export", args=[main_dataset.pk, main_dataset.latest_version().pk]))

        assert "datasets/gov/ref" in resp.text
        assert "NoPkModel" in resp.text

        assert "datasets/gov/orphan" not in resp.text
        assert "OrphanModel" not in resp.text

        lines = resp.text.split("\r\n")
        no_pk_model_line = [line for line in lines if "NoPkModel" in line][0]
        assert no_pk_model_line == "11,,,,NoPkModel,,,,,,,,,,develop,,,,,,"

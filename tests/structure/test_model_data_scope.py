import json
from unittest.mock import patch

import pytest
import requests_mock
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from tests.structure.test_views import _setup_download_model
from vitrina.structure.factories import MetadataFactory, ModelScopeFactory, VersionFactory
from vitrina.structure.models import ModelScope
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db

SPINTA = "https://spinta.test"


def _scope(model, version, name: str, prepare: str = "prop='x'") -> None:
    scope = ModelScopeFactory(model=model, metadata_version=version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(ModelScope),
        object_id=scope.pk,
        dataset=model.dataset,
        ref=name,
        prepare=prepare,
        metadata_version=version,
    )


def _model_with_scope():
    version = VersionFactory()
    dataset, model = _setup_download_model(version)
    _scope(model, version, "ltu")
    return version, dataset, model


@patch("vitrina.structure.services.SPINTA_SERVER_URL", SPINTA)
def test_table_data_reads_through_the_selected_scope(client):
    _, dataset, _ = _model_with_scope()
    url = reverse("model-data-table-data", args=[dataset.pk, "test-dataset-TestModel"])

    with requests_mock.Mocker() as spinta:
        spinta.get(requests_mock.ANY, json={"_data": []})
        assert client.get(f'{url}?_scope=ltu&prop="x"').status_code == 200

    assert spinta.last_request.url == f"{SPINTA}/test/dataset/TestModel/@ltu/?limit(100)&prop=%22x%22"


@patch("vitrina.structure.services.SPINTA_SERVER_URL", SPINTA)
def test_count_reads_through_the_selected_scope(client):
    _, dataset, _ = _model_with_scope()
    url = reverse("model-data-count", args=[dataset.pk, "test-dataset-TestModel"])

    with requests_mock.Mocker() as spinta:
        spinta.get(requests_mock.ANY, json={"_data": [{"count()": 2}]})
        assert client.get(f"{url}?_scope=ltu").status_code == 200

    assert spinta.last_request.url == f"{SPINTA}/test/dataset/TestModel/@ltu/?count()"


@pytest.mark.parametrize("scope", ["../admin", "ltu/:changes", "a b"])
def test_invalid_scope_name_is_refused_without_calling_spinta(client, scope: str):
    _, dataset, _ = _model_with_scope()
    url = reverse("model-data-table-data", args=[dataset.pk, "test-dataset-TestModel"])

    with requests_mock.Mocker() as spinta:
        resp = client.get(url, {"_scope": scope})

    assert resp.status_code == 400
    assert not spinta.called


@patch("vitrina.structure.views.SPINTA_SERVER_URL", "https://get.data.gov.lt")
def test_download_reads_through_the_selected_scope(app: DjangoTestApp):
    version, dataset, model = _model_with_scope()
    url = reverse("model-data", args=[dataset.pk, version.pk, model.name])

    resp = app.get(f"{url}?format=csv&_scope=ltu")

    assert resp.status_code == 302
    assert resp.location == "https://get.data.gov.lt/test/dataset/TestModel/@ltu/:format/csv"


def test_data_page_lists_the_model_scopes(app: DjangoTestApp):
    version, dataset, model = _model_with_scope()
    _scope(model, version, "names", prepare="select(prop)")
    app.set_user(UserFactory(is_staff=True))
    url = reverse("model-data", args=[dataset.pk, version.pk, model.name])

    resp = app.get(f"{url}?_scope=ltu")

    assert resp.context["scopes"] == ["ltu", "names"]
    assert resp.context["selected_scope"] == "ltu"
    assert 'id="scope-select"' in resp.text


def test_data_page_without_scopes_has_no_selector(app: DjangoTestApp):
    version = VersionFactory()
    dataset, model = _setup_download_model(version)
    app.set_user(UserFactory(is_staff=True))

    resp = app.get(reverse("model-data", args=[dataset.pk, version.pk, model.name]))

    assert resp.context["scopes"] == []
    assert 'id="scope-select"' not in resp.text


def test_selected_scope_is_not_shown_as_a_filter(app: DjangoTestApp):
    version, dataset, model = _model_with_scope()
    data = {"_data": [{"_id": "c7d66fa2-a880-443d-8ab5-2ab7f9c79886", "prop": "x"}]}

    resp = app.post(
        reverse("model-data-table", args=[dataset.pk, version.pk, model.name]),
        {"data": json.dumps(data), "query": '?_scope=ltu&prop="x"'},
    )

    assert resp.context["tags"] == ['prop="x"']

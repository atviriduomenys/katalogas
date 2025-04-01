from io import BytesIO

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.api_example.models import ApiExample
from vitrina.datasets.factories import DatasetFactory
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_api_example_yaml_file_import_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()

    app.set_user(user)
    url = reverse("file_upload", args=[dataset.pk])
    resp = app.get(url, expect_errors=True)

    assert resp.status_code == 403


@pytest.mark.django_db
def test_api_example_yaml_file_import_success(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()

    app.set_user(user)
    resp = app.get(reverse("file_upload", args=[dataset.pk]))
    form = resp.forms["file_upload_form"]

    yaml_content = b"""
        type: yaml
        """
    form["yaml_file"] = (BytesIO(yaml_content), "test.yaml")
    form.submit()

    api_example = ApiExample.objects.first()
    assert api_example is not None
    assert api_example.dataset == dataset
    assert api_example.yaml_file.name.endswith("test.yaml")

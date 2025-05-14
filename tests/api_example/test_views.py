import pytest

from django.urls import reverse
from django_webtest import DjangoTestApp

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

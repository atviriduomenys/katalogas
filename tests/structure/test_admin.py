import pytest
from unittest.mock import patch
from django_webtest import DjangoTestApp
from django.urls import reverse
from django.test import override_settings
from vitrina.structure.models import ManifestValidationEntry
from vitrina.users.models import User


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
@pytest.mark.django_db(transaction=True)
def test_manifestvalidationentry_add_executes_task(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="test@test.com", password="test123")
    app.set_user(admin)

    url = reverse("admin:vitrina_structure_manifestvalidationentry_add")

    form = app.get(url).forms["manifestvalidationentry_form"]

    response = form.submit(upload_files=[("manifest_file", "test.csv", b"0")])
    assert response.status_code == 302

    entry = ManifestValidationEntry.objects.latest("created_at")
    assert entry.validation_status != "PENDING"


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
@pytest.mark.django_db()
def test_manifestvalidationentry_does_not_execute_task_without_commit(app: DjangoTestApp):
    admin = User.objects.create_superuser(email="test@test.com", password="test123")
    app.set_user(admin)

    url = reverse("admin:vitrina_structure_manifestvalidationentry_add")

    form = app.get(url).forms["manifestvalidationentry_form"]

    with patch("vitrina.structure.admin.validate_manifest_task.delay") as mocked_task:
        response = form.submit(upload_files=[("manifest_file", "test.csv", b"0")])

    assert response.status_code == 302

    entry = ManifestValidationEntry.objects.latest("created_at")
    assert entry.validation_status == "PENDING"

    mocked_task.assert_not_called()

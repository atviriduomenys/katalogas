import pytest
from django.test import override_settings
from vitrina.structure.models import ManifestValidationEntry
from vitrina.users.factories import UserFactory
from reversion.models import Version
from vitrina.structure.tasks import validate_manifest_task
from vitrina.utils import RevisionComment, RevisionSource
from django.core.files.uploadedfile import SimpleUploadedFile


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("include_user", [True, False])
def test_celery_tasks_create_versions_with_or_without_user(include_user: bool):
    user = UserFactory() if include_user else None
    dummy_csv = SimpleUploadedFile(
        name="empty.csv",
        content=b"",
        content_type="text/csv",
    )
    manifest_validation_entry = ManifestValidationEntry.objects.create(manifest_file=dummy_csv)

    revision_comment = RevisionComment(
        source=RevisionSource.TASK,
        action="vitrina.structure.tasks.validate_manifest_task",
        args=[manifest_validation_entry.pk],
        kwargs={},
    )
    if user:
        validate_manifest_task.delay(manifest_validation_entry.pk, _reversion_user_id=user.id)
    else:
        validate_manifest_task.delay(manifest_validation_entry.pk)

    versions = Version.objects.get_for_model(manifest_validation_entry)

    assert versions.count() == 1
    revision = versions.first().revision
    assert revision.user == user
    assert revision.comment == revision_comment.to_json()

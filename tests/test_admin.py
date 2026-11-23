import warnings

import pytest
import reversion
from django.contrib import admin
from django.urls import resolve, reverse
from django.utils.deprecation import RemovedInDjango60Warning

from vitrina.classifiers.factories import LicenceFactory
from vitrina.classifiers.models import Licence
from vitrina.users.models import User
from vitrina.utils import RevisionComment, RevisionSource


@pytest.mark.django_db
def test_log_deletions_sets_revision_comment(rf):
    licence = LicenceFactory()
    url = reverse("admin:vitrina_classifiers_licence_delete", args=[licence.pk])
    request = rf.post(url)
    request.resolver_match = resolve(url)
    request.user = User.objects.create_superuser(email="admin@gmail.com", password="test123")
    model_admin = admin.site._registry[Licence]

    with warnings.catch_warnings():
        warnings.simplefilter("error", RemovedInDjango60Warning)
        with reversion.create_revision():
            model_admin.log_deletions(request, Licence.objects.filter(pk=licence.pk))
            comment = RevisionComment.from_json(reversion.get_comment())

    assert comment.source == RevisionSource.ADMIN
    assert comment.action == "delete"
    assert comment.path == url

import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.comments.forms import DatasetCommentForm, CommentForm, RequestCommentForm
from vitrina.comments.services import get_comment_form_class
from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory, RequestAssignmentFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_get_comment_form_class_for_dataset():
    dataset = DatasetFactory()
    user = UserFactory()
    res = get_comment_form_class(dataset, user)
    assert res == DatasetCommentForm


@pytest.mark.django_db
def test_get_comment_form_class_for_request_without_perm():
    request = RequestFactory()
    user = UserFactory()
    res = get_comment_form_class(request, user)
    assert res == CommentForm


@pytest.mark.django_db
def test_get_comment_form_class_for_request_with_staff_perm():
    request = RequestFactory()
    user = UserFactory(is_staff=True)
    res = get_comment_form_class(request, user)
    assert res == RequestCommentForm


@pytest.mark.django_db
def test_get_comment_form_class_for_request_with_manager_perm():
    request_assignment = RequestAssignmentFactory()
    request = request_assignment.request
    organization = request_assignment.organization
    request.save()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.MANAGER
    )
    res = get_comment_form_class(request, manager.user)
    assert res == RequestCommentForm


@pytest.mark.django_db
def test_get_comment_form_class_for_request_with_coordinator_perm():
    request_assignment = RequestAssignmentFactory()
    request = request_assignment.request
    organization = request_assignment.organization
    request.save()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.COORDINATOR
    )
    res = get_comment_form_class(request, coordinator.user)
    assert res == RequestCommentForm


@pytest.mark.django_db
def test_get_comment_form_class_for_project():
    project = ProjectFactory()
    user = UserFactory()
    res = get_comment_form_class(project, user)
    assert res == CommentForm

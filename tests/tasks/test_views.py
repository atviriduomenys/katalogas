from datetime import datetime

import pytest
import pytz
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.tasks.factories import TaskFactory
from vitrina.tasks.models import Task
from vitrina.users.factories import UserFactory
from vitrina.users.models import User

timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.fixture
def set_up_data():
    organization = OrganizationFactory()
    content_type = ContentType.objects.get_for_model(organization)
    user = User.objects.create_user(
        email="user1@test.com",
        password="test123"
    )
    user_with_organization = User.objects.create(
        email="user3@test.com",
        password="test123",
        organization=organization
    )
    RepresentativeFactory(
        user=user_with_organization,
        content_type=content_type,
        object_id=organization.pk
    )
    task_for_user = TaskFactory(user=user)
    task_for_organization = TaskFactory(organization=organization,
                                        created=timezone.localize(datetime(2022, 8, 23, 11, 30)))
    return {
        'organization': organization,
        'user': user,
        'user_with_organization': user_with_organization,
        'task_for_user': task_for_user,
        'task_for_organization': task_for_organization
    }


@pytest.mark.haystack
def test_task_list_with_user(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data['user'])
    resp = app.get('%s?owner=user' % reverse("user-task-list", kwargs={'pk': set_up_data['user'].pk}))
    assert list([int(task.pk) for task in resp.context["object_list"]]) == [set_up_data['task_for_user'].pk]


@pytest.mark.haystack
def test_task_list_with_organization(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data['user_with_organization'])
    resp = app.get('%s?owner=all' % reverse("user-task-list", kwargs={'pk': set_up_data['user_with_organization'].pk}))
    assert list([int(task.pk) for task in resp.context["object_list"]]) == [set_up_data['task_for_organization'].pk]


@pytest.mark.django_db
def test_task_detail_with_no_user(app: DjangoTestApp):
    user = UserFactory()
    organization = OrganizationFactory()
    task = TaskFactory(organization=organization)
    url = reverse("user-task-detail", args=[user.pk, task.pk])
    resp = app.get(url)
    assert resp.status_code == 302
    assert resp.url == "%s?next=%s" % (reverse('login'), url)


@pytest.mark.django_db
def test_task_detail_with_user_with_no_access(app: DjangoTestApp):
    user = UserFactory()
    organization = OrganizationFactory()
    task = TaskFactory(organization=organization)
    app.set_user(user)
    url = reverse("user-task-detail", args=[user.pk, task.pk])
    resp = app.get(url, expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_task_detail_with_user_with_access(app: DjangoTestApp):
    user = UserFactory()
    task = TaskFactory(user=user)
    app.set_user(user)
    url = reverse("user-task-detail", args=[user.pk, task.pk])
    resp = app.get(url)
    assert resp.context['object'].pk == task.pk


@pytest.mark.django_db
def test_task_close_with_no_user(app: DjangoTestApp):
    user = UserFactory()
    organization = OrganizationFactory()
    task = TaskFactory(organization=organization)
    url = reverse("user-task-close", args=[user.pk, task.pk])
    resp = app.get(url)
    assert resp.status_code == 302
    assert resp.url == "%s?next=%s" % (reverse('login'), url)


@pytest.mark.django_db
def test_task_close_with_user_with_no_access(app: DjangoTestApp):
    user = UserFactory()
    organization = OrganizationFactory()
    task = TaskFactory(organization=organization)
    app.set_user(user)
    url = reverse("user-task-close", args=[user.pk, task.pk])
    resp = app.get(url, expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_task_close_with_user_with_already_closed_task(app: DjangoTestApp):
    user = UserFactory()
    task = TaskFactory(user=user, status=Task.COMPLETED)
    app.set_user(user)
    url = reverse("user-task-close", args=[user.pk, task.pk])
    resp = app.get(url, expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_task_close_with_user_with_access(app: DjangoTestApp):
    user = UserFactory()
    task = TaskFactory(user=user)
    app.set_user(user)
    url = reverse("user-task-close", args=[user.pk, task.pk])
    resp = app.get(url)
    form = resp.forms['close-form']
    form.submit()
    task.refresh_from_db()
    assert task.status == Task.COMPLETED


@pytest.mark.django_db
def test_task_assign_with_no_user(app: DjangoTestApp):
    user = UserFactory()
    organization = OrganizationFactory()
    task = TaskFactory(organization=organization)
    url = reverse("user-task-assign", args=[user.pk, task.pk])
    resp = app.get(url)
    assert resp.status_code == 302
    assert resp.url == "%s?next=%s" % (reverse('login'), url)


@pytest.mark.django_db
def test_task_assign_with_user_with_no_access(app: DjangoTestApp):
    user = UserFactory()
    organization = OrganizationFactory()
    task = TaskFactory(organization=organization)
    app.set_user(user)
    url = reverse("user-task-close", args=[user.pk, task.pk])
    resp = app.get(url, expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_task_close_with_user_with_already_closed_task(app: DjangoTestApp):
    user = UserFactory()
    task = TaskFactory(user=user, status=Task.COMPLETED)
    app.set_user(user)
    url = reverse("user-task-assign", args=[user.pk, task.pk])
    resp = app.get(url, expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_task_assign_with_user_with_access(app: DjangoTestApp):
    user = UserFactory()
    task = TaskFactory(user=user)
    app.set_user(user)
    url = reverse("user-task-assign", args=[user.pk, task.pk])
    resp = app.get(url)
    form = resp.forms['assign-form']
    form.submit()
    task.refresh_from_db()
    assert task.status == Task.ASSIGNED


@pytest.mark.haystack
def test_task_search_with_title(app: DjangoTestApp):
    user = UserFactory()
    task1 = TaskFactory(user=user, title="Test: task")
    task2 = TaskFactory(user=user, title="Test: task 2")
    TaskFactory(user=user, title="Something else")
    app.set_user(user)
    resp = app.get('%s?q=Test:' % reverse("user-task-list", kwargs={'pk': user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([
        task1.pk, task2.pk
    ])


@pytest.mark.haystack
def test_task_search_with_description(app: DjangoTestApp):
    user = UserFactory()
    task1 = TaskFactory(user=user, description="Test description")
    task2 = TaskFactory(user=user, description="Test description 2")
    TaskFactory(user=user, description="Something else")
    app.set_user(user)
    resp = app.get('%s?q=description' % reverse("user-task-list", kwargs={'pk': user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([
        task1.pk, task2.pk
    ])


@pytest.mark.haystack
def test_task_search_with_user_name(app: DjangoTestApp):
    user = UserFactory(first_name="Test", last_name="User")
    task1 = TaskFactory(user=user)
    task2 = TaskFactory(user=user)
    TaskFactory()
    app.set_user(user)
    resp = app.get('%s?q=Test+User' % reverse("user-task-list", kwargs={'pk': user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([
        task1.pk, task2.pk
    ])


@pytest.mark.haystack
def test_task_search_with_organization_name(app: DjangoTestApp):
    organization = OrganizationFactory(title="Organization")
    user = UserFactory(organization=organization)
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    task1 = TaskFactory(organization=organization)
    task2 = TaskFactory(organization=organization)
    TaskFactory()
    app.set_user(user)
    resp = app.get('%s?q=Organization' % reverse("user-task-list", kwargs={'pk': user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([
        task1.pk, task2.pk
    ])


@pytest.mark.haystack
def test_task_search_with_filter(app: DjangoTestApp):
    user = UserFactory()
    task1 = TaskFactory(user=user, title="Test: task", status=Task.CREATED)
    TaskFactory(user=user, title="Test: task 2", status=Task.COMPLETED)
    TaskFactory(user=user, title="Something else", status=Task.CREATED)
    app.set_user(user)
    resp = app.get('%s?q=Test:&selected_facets=status_exact:created' %
                   reverse("user-task-list", kwargs={'pk': user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([task1.pk])


@pytest.mark.haystack
def test_task_list_with_owner_filter__user(app: DjangoTestApp):
    organization = OrganizationFactory(title="Organization")
    user = UserFactory(organization=organization)
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    task1 = TaskFactory(user=user)
    task2 = TaskFactory(user=user)
    TaskFactory(organization=organization)
    app.set_user(user)
    resp = app.get('%s?owner=user' % reverse("user-task-list", kwargs={'pk': user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([task1.pk, task2.pk])


@pytest.mark.haystack
def test_task_list_with_owner_filter__all(app: DjangoTestApp):
    organization = OrganizationFactory(title="Organization")
    user = UserFactory(organization=organization)
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk
    )
    task1 = TaskFactory(user=user)
    task2 = TaskFactory(user=user)
    task3 = TaskFactory(organization=organization)
    app.set_user(user)
    resp = app.get('%s?owner=all' % reverse("user-task-list", kwargs={'pk': user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == \
           sorted([task1.pk, task2.pk, task3.pk])

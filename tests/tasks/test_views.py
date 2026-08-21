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
    user = User.objects.create_user(email="user1@test.com", password="test123")
    user_with_organization = User.objects.create(email="user3@test.com", password="test123", organization=organization)
    RepresentativeFactory(user=user_with_organization, content_type=content_type, object_id=organization.pk)
    task_for_user = TaskFactory(user=user)
    task_for_organization = TaskFactory(
        organization=organization, created=timezone.localize(datetime(2022, 8, 23, 11, 30))
    )
    return {
        "organization": organization,
        "user": user,
        "user_with_organization": user_with_organization,
        "task_for_user": task_for_user,
        "task_for_organization": task_for_organization,
    }


def test_task_list_with_user(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data["user"])
    resp = app.get("%s?owner=user" % reverse("user-task-list", kwargs={"pk": set_up_data["user"].pk}))
    assert list([int(task.pk) for task in resp.context["object_list"]]) == [set_up_data["task_for_user"].pk]


def test_task_list_with_organization(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data["user_with_organization"])
    resp = app.get("%s?owner=all" % reverse("user-task-list", kwargs={"pk": set_up_data["user_with_organization"].pk}))
    assert list([int(task.pk) for task in resp.context["object_list"]]) == [set_up_data["task_for_organization"].pk]


@pytest.mark.django_db
def test_task_detail_with_no_user(app: DjangoTestApp):
    user = UserFactory()
    organization = OrganizationFactory()
    task = TaskFactory(organization=organization)
    url = reverse("user-task-detail", args=[user.pk, task.pk])
    resp = app.get(url)
    assert resp.status_code == 302
    assert resp.url == "%s?next=%s" % (reverse("login"), url)


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
    assert resp.context["object"].pk == task.pk


@pytest.mark.django_db
def test_task_close_with_no_user(app: DjangoTestApp):
    user = UserFactory()
    organization = OrganizationFactory()
    task = TaskFactory(organization=organization)
    url = reverse("user-task-close", args=[user.pk, task.pk])
    resp = app.get(url)
    assert resp.status_code == 302
    assert resp.url == "%s?next=%s" % (reverse("login"), url)


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
    form = resp.forms["close-form"]
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
    assert resp.url == "%s?next=%s" % (reverse("login"), url)


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
def test_task_assign_with_user_with_already_closed_task(app: DjangoTestApp):
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
    form = resp.forms["assign-form"]
    form.submit()
    task.refresh_from_db()
    assert task.status == Task.ASSIGNED


def test_task_search_with_title(app: DjangoTestApp):
    user = UserFactory()
    task1 = TaskFactory(user=user, title="Test: task")
    task2 = TaskFactory(user=user, title="Test: task 2")
    TaskFactory(user=user, title="Something else")
    app.set_user(user)
    resp = app.get("%s?q=Test:" % reverse("user-task-list", kwargs={"pk": user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([task1.pk, task2.pk])


def test_task_search_with_description(app: DjangoTestApp):
    user = UserFactory()
    task1 = TaskFactory(user=user, description="Test description")
    task2 = TaskFactory(user=user, description="Test description 2")
    TaskFactory(user=user, description="Something else")
    app.set_user(user)
    resp = app.get("%s?q=description" % reverse("user-task-list", kwargs={"pk": user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([task1.pk, task2.pk])


def test_task_search_with_user_name(app: DjangoTestApp):
    user = UserFactory(first_name="Test", last_name="User")
    task1 = TaskFactory(user=user)
    task2 = TaskFactory(user=user)
    TaskFactory()
    app.set_user(user)
    resp = app.get("%s?q=Test+User" % reverse("user-task-list", kwargs={"pk": user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([task1.pk, task2.pk])


def test_task_search_with_organization_name(app: DjangoTestApp):
    organization = OrganizationFactory(title="Organization")
    user = UserFactory(organization=organization)
    RepresentativeFactory(
        user=user, content_type=ContentType.objects.get_for_model(organization), object_id=organization.pk
    )
    task1 = TaskFactory(organization=organization)
    task2 = TaskFactory(organization=organization)
    TaskFactory()
    app.set_user(user)
    resp = app.get("%s?q=Organization" % reverse("user-task-list", kwargs={"pk": user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([task1.pk, task2.pk])


def test_task_search_with_filter(app: DjangoTestApp):
    user = UserFactory()
    task1 = TaskFactory(user=user, title="Test: task", status=Task.CREATED)
    TaskFactory(user=user, title="Test: task 2", status=Task.COMPLETED)
    TaskFactory(user=user, title="Something else", status=Task.CREATED)
    app.set_user(user)
    resp = app.get("%s?q=Test:&status=created" % reverse("user-task-list", kwargs={"pk": user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([task1.pk])


def test_task_list_with_owner_filter__user(app: DjangoTestApp):
    organization = OrganizationFactory(title="Organization")
    user = UserFactory(organization=organization)
    RepresentativeFactory(
        user=user, content_type=ContentType.objects.get_for_model(organization), object_id=organization.pk
    )
    task1 = TaskFactory(user=user)
    task2 = TaskFactory(user=user)
    TaskFactory(organization=organization)
    app.set_user(user)
    resp = app.get("%s?owner=user" % reverse("user-task-list", kwargs={"pk": user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted([task1.pk, task2.pk])


def test_task_list_with_owner_filter__all(app: DjangoTestApp):
    organization = OrganizationFactory(title="Organization")
    user = UserFactory(organization=organization)
    RepresentativeFactory(
        user=user, content_type=ContentType.objects.get_for_model(organization), object_id=organization.pk
    )
    task1 = TaskFactory(user=user)
    task2 = TaskFactory(user=user)
    task3 = TaskFactory(organization=organization)
    app.set_user(user)
    resp = app.get("%s?owner=all" % reverse("user-task-list", kwargs={"pk": user.pk}))
    assert sorted(list([int(task.pk) for task in resp.context["object_list"]])) == sorted(
        [task1.pk, task2.pk, task3.pk]
    )


@pytest.mark.django_db
def test_task_list_regular_user_cannot_access_other_users_tasks(app: DjangoTestApp):
    user1 = UserFactory()
    user2 = UserFactory()
    TaskFactory(user=user2)

    app.set_user(user1)
    url = reverse("user-task-list", kwargs={"pk": user2.pk})
    resp = app.get(url, expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_task_list_staff_can_access_other_users_tasks(app: DjangoTestApp):
    staff_user = UserFactory(is_staff=True)
    regular_user = UserFactory()
    task = TaskFactory(user=regular_user)

    app.set_user(staff_user)
    url = reverse("user-task-list", kwargs={"pk": regular_user.pk})
    resp = app.get(url)
    assert resp.status_code == 200
    assert task.pk in [t.pk for t in resp.context["object_list"]]


@pytest.mark.django_db
def test_task_list_superuser_can_access_other_users_tasks(app: DjangoTestApp):
    superuser = UserFactory(is_superuser=True)
    regular_user = UserFactory()
    task = TaskFactory(user=regular_user)

    app.set_user(superuser)
    url = reverse("user-task-list", kwargs={"pk": regular_user.pk})
    resp = app.get(url)
    assert resp.status_code == 200
    assert task.pk in [t.pk for t in resp.context["object_list"]]


@pytest.mark.django_db
def test_task_detail_staff_can_access_other_users_tasks(app: DjangoTestApp):
    staff_user = UserFactory(is_staff=True)
    regular_user = UserFactory()
    task = TaskFactory(user=regular_user)

    app.set_user(staff_user)
    url = reverse("user-task-detail", args=[regular_user.pk, task.pk])
    resp = app.get(url)
    assert resp.status_code == 200
    assert resp.context["object"].pk == task.pk


@pytest.mark.django_db
def test_task_detail_superuser_can_access_other_users_tasks(app: DjangoTestApp):
    superuser = UserFactory(is_superuser=True)
    regular_user = UserFactory()
    task = TaskFactory(user=regular_user)

    app.set_user(superuser)
    url = reverse("user-task-detail", args=[regular_user.pk, task.pk])
    resp = app.get(url)
    assert resp.status_code == 200
    assert resp.context["object"].pk == task.pk


def test_task_list_status_filter(app: DjangoTestApp):
    user = UserFactory()
    task_created = TaskFactory(user=user, status=Task.CREATED)
    task_assigned = TaskFactory(user=user, status=Task.ASSIGNED)
    TaskFactory(user=user, status=Task.COMPLETED)

    app.set_user(user)

    # Test CREATED filter
    resp = app.get(f"{reverse('user-task-list', kwargs={'pk': user.pk})}?status={Task.CREATED}")
    result_pks = [t.pk for t in resp.context["object_list"]]
    assert task_created.pk in result_pks
    assert task_assigned.pk not in result_pks

    # Test ASSIGNED filter
    resp = app.get(f"{reverse('user-task-list', kwargs={'pk': user.pk})}?status={Task.ASSIGNED}")
    result_pks = [t.pk for t in resp.context["object_list"]]
    assert task_assigned.pk in result_pks
    assert task_created.pk not in result_pks


def test_task_list_type_filter(app: DjangoTestApp):
    user = UserFactory()
    task_request = TaskFactory(user=user, type=Task.REQUEST)
    task_error = TaskFactory(user=user, type=Task.ERROR)
    TaskFactory(user=user, type=Task.DATASET)

    app.set_user(user)

    # Test REQUEST filter
    resp = app.get(f"{reverse('user-task-list', kwargs={'pk': user.pk})}?type={Task.REQUEST}")
    result_pks = [t.pk for t in resp.context["object_list"]]
    assert task_request.pk in result_pks
    assert task_error.pk not in result_pks

    # Test ERROR filter
    resp = app.get(f"{reverse('user-task-list', kwargs={'pk': user.pk})}?type={Task.ERROR}")
    result_pks = [t.pk for t in resp.context["object_list"]]
    assert task_error.pk in result_pks
    assert task_request.pk not in result_pks


def test_task_list_combined_filters(app: DjangoTestApp):
    user = UserFactory()
    task_match = TaskFactory(user=user, status=Task.CREATED, type=Task.REQUEST)
    # Wrong status
    TaskFactory(user=user, status=Task.COMPLETED, type=Task.REQUEST)
    # Wrong type
    TaskFactory(user=user, status=Task.CREATED, type=Task.ERROR)

    app.set_user(user)
    resp = app.get(f"{reverse('user-task-list', kwargs={'pk': user.pk})}?status={Task.CREATED}&type={Task.REQUEST}")
    result_pks = [t.pk for t in resp.context["object_list"]]
    assert result_pks == [task_match.pk]


def test_task_list_filter_counts_are_accurate(app: DjangoTestApp):
    user = UserFactory()
    TaskFactory(user=user, status=Task.CREATED)
    TaskFactory(user=user, status=Task.CREATED)
    TaskFactory(user=user, status=Task.ASSIGNED)
    TaskFactory(user=user, status=Task.COMPLETED)

    app.set_user(user)
    resp = app.get(reverse("user-task-list", kwargs={"pk": user.pk}))

    status_filter = next(f for f in resp.context["filters"] if f["title"] == "Būsena")

    created_item = next(item for item in status_filter["items"] if item["title"] == Task.FILTER_STATUSES[Task.CREATED])
    assert created_item["count"] == 2

    assigned_item = next(
        item for item in status_filter["items"] if item["title"] == Task.FILTER_STATUSES[Task.ASSIGNED]
    )
    assert assigned_item["count"] == 1

    completed_item = next(
        item for item in status_filter["items"] if item["title"] == Task.FILTER_STATUSES[Task.COMPLETED]
    )
    assert completed_item["count"] == 1


def test_task_list_owner_filter_counts_with_organization(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(organization=organization)
    RepresentativeFactory(
        user=user, content_type=ContentType.objects.get_for_model(organization), object_id=organization.pk
    )

    # 2 tasks assigned to user
    TaskFactory(user=user)
    TaskFactory(user=user)
    # 3 tasks assigned to organization (not directly to user)
    TaskFactory(organization=organization)
    TaskFactory(organization=organization)
    TaskFactory(organization=organization)

    app.set_user(user)
    resp = app.get(reverse("user-task-list", kwargs={"pk": user.pk}))

    owner_filter = next(f for f in resp.context["filters"] if f["title"] == "Vykdytojas")

    user_tasks = next(item for item in owner_filter["items"] if "Mano užduotys" in item["title"])
    all_tasks = next(item for item in owner_filter["items"] if "Visos užduotys" in item["title"])

    assert user_tasks["count"] == 2
    assert all_tasks["count"] == 5  # 2 user tasks + 3 org tasks

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.tasks.factories import TaskFactory
from vitrina.tasks.models import Task
from vitrina.tasks.services import get_active_tasks
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_get_active_tasks():
    organization = OrganizationFactory()
    user = UserFactory(organization=organization)
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(organization),
        object_id=organization.pk,
        user=user
    )

    task_for_user = TaskFactory(user=user)
    task_for_organization1 = TaskFactory(organization=organization)
    task_for_organization2 = TaskFactory(organization=OrganizationFactory())

    active_tasks = get_active_tasks(user)
    assert list(active_tasks) == [
        task_for_user,
        task_for_organization1,
    ]


@pytest.mark.django_db
def test_get_active_tasks_with_task_organization_supervisor_after_5_days():
    parent_organization = OrganizationFactory()
    child_organization = parent_organization.add_child(instance=OrganizationFactory.build())

    task_for_parent_organization = TaskFactory(organization=parent_organization)
    task_for_child_organization = TaskFactory(organization=child_organization)
    for task in Task.objects.all():
        task.created = timezone.datetime(2022, 11, 18)
        task.save()

    parent_organization_user = UserFactory(organization=parent_organization)
    child_organization_user = UserFactory(organization=child_organization)

    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(parent_organization),
        object_id=parent_organization.pk,
        role=Representative.COORDINATOR,
        user=parent_organization_user
    )
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(child_organization),
        object_id=child_organization.pk,
        role=Representative.COORDINATOR,
        user=child_organization_user
    )

    active_tasks = get_active_tasks(
        parent_organization_user,
        now=timezone.datetime(2022, 11, 23).date()
    )
    assert list(active_tasks) == [task_for_parent_organization]

    active_tasks = get_active_tasks(
        child_organization_user,
        now=timezone.datetime(2022, 11, 23).date()
    )
    assert list(active_tasks) == [task_for_child_organization]


@pytest.mark.django_db
def test_get_active_tasks_with_task_organization_supervisor_after_5_work_days():
    parent_organization = OrganizationFactory()
    child_organization = parent_organization.add_child(instance=OrganizationFactory.build())

    task_for_parent_organization = TaskFactory(organization=parent_organization)
    task_for_child_organization = TaskFactory(organization=child_organization)
    for task in Task.objects.all():
        task.created = timezone.datetime(2022, 11, 18)
        task.save()

    parent_organization_user = UserFactory(organization=parent_organization)
    child_organization_user = UserFactory(organization=child_organization)

    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(parent_organization),
        object_id=parent_organization.pk,
        role=Representative.COORDINATOR,
        user=parent_organization_user
    )
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(child_organization),
        object_id=child_organization.pk,
        role=Representative.COORDINATOR,
        user=child_organization_user
    )

    active_tasks = get_active_tasks(
        parent_organization_user,
        now=timezone.datetime(2022, 11, 25).date()
    )
    assert list(active_tasks) == [
        task_for_parent_organization,
        task_for_child_organization
    ]

    active_tasks = get_active_tasks(
        child_organization_user,
        now=timezone.datetime(2022, 11, 25).date()
    )
    assert list(active_tasks) == [task_for_child_organization]


@pytest.mark.django_db
def test_get_active_tasks_with_staff_after_10_days():
    parent_organization = OrganizationFactory()
    child_organization1 = parent_organization.add_child(instance=OrganizationFactory.build())
    child_organization2 = child_organization1.add_child(instance=OrganizationFactory.build())

    parent_organization_user = UserFactory(organization=parent_organization)
    child_organization_user = UserFactory(organization=child_organization1)
    staff = UserFactory(is_staff=True)

    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(parent_organization),
        object_id=parent_organization.pk,
        role=Representative.COORDINATOR,
        user=parent_organization_user
    )
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(child_organization1),
        object_id=child_organization1.pk,
        role=Representative.COORDINATOR,
        user=child_organization_user
    )

    task_for_parent_organization = TaskFactory(organization=parent_organization)
    task_for_child_organization1 = TaskFactory(organization=child_organization1)
    task_for_child_organization2 = TaskFactory(organization=child_organization2)
    for task in Task.objects.all():
        task.created = timezone.datetime(2022, 11, 18)
        task.save()

    active_tasks = get_active_tasks(
        parent_organization_user,
        now=timezone.datetime(2022, 11, 28).date()
    )
    assert list(active_tasks) == [
        task_for_parent_organization,
        task_for_child_organization1,
        task_for_child_organization2
    ]

    active_tasks = get_active_tasks(
        child_organization_user,
        now=timezone.datetime(2022, 11, 28).date()
    )
    assert list(active_tasks) == [
        task_for_child_organization1,
        task_for_child_organization2
    ]

    active_tasks = get_active_tasks(
        staff,
        now=timezone.datetime(2022, 11, 28).date()
    )
    assert list(active_tasks) == []


@pytest.mark.django_db
def test_get_active_tasks_with_staff_after_10_work_days():
    parent_organization = OrganizationFactory()
    child_organization1 = parent_organization.add_child(instance=OrganizationFactory.build())
    child_organization2 = child_organization1.add_child(instance=OrganizationFactory.build())

    parent_organization_user = UserFactory(organization=parent_organization)
    child_organization_user = UserFactory(organization=child_organization1)
    staff = UserFactory(is_staff=True)

    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(parent_organization),
        object_id=parent_organization.pk,
        role=Representative.COORDINATOR,
        user=parent_organization_user
    )
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(child_organization1),
        object_id=child_organization1.pk,
        role=Representative.COORDINATOR,
        user=child_organization_user
    )

    task_for_parent_organization = TaskFactory(organization=parent_organization)
    task_for_child_organization1 = TaskFactory(organization=child_organization1)
    task_for_child_organization2 = TaskFactory(organization=child_organization2)
    for task in Task.objects.all():
        task.created = timezone.datetime(2022, 11, 18)
        task.save()

    active_tasks = get_active_tasks(
        parent_organization_user,
        now=timezone.datetime(2022, 12, 2).date()
    )
    assert list(active_tasks) == [
        task_for_parent_organization,
        task_for_child_organization1,
        task_for_child_organization2
    ]

    active_tasks = get_active_tasks(
        child_organization_user,
        now=timezone.datetime(2022, 12, 2).date()
    )
    assert list(active_tasks) == [
        task_for_child_organization1,
        task_for_child_organization2
    ]

    active_tasks = get_active_tasks(
        staff,
        now=timezone.datetime(2022, 12, 2).date()
    )
    assert list(active_tasks) == [
        task_for_parent_organization,
        task_for_child_organization1,
        task_for_child_organization2
    ]

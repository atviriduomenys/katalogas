from vitrina.users.models import User
from vitrina.projects.models import Project
from vitrina.orgs.models import Representative, Organization
from typing import Iterable
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from django.contrib.auth.models import AnonymousUser


def _represented_org_ids(user: User | AnonymousUser) -> Iterable[int]:
    return Representative.objects.filter(
        content_type=ContentType.objects.get_for_model(Organization),
        user=user,
    ).values_list("object_id", flat=True)


def _q_project(user: User | AnonymousUser) -> Q:
    public_approved_or_created = Q(is_public=True) & Q(status__in=[Project.APPROVED, Project.CREATED])

    if not getattr(user, "is_authenticated", False):
        return public_approved_or_created

    if user.is_staff or user.is_superuser:
        return Q()

    represented_org_ids = _represented_org_ids(user)

    q = (
        public_approved_or_created
        | Q(organization__isnull=True, user=user)  # Owner can view personal projects
        | Q(organization_id__in=represented_org_ids)  # All organization representatives can view organization's projects
        | Q(agreements__assigner_id__in=represented_org_ids)  # All assigners' organizations' representatives can view projects their are part of
    )

    return q


def can_view_project(user: User | AnonymousUser, project: Project) -> bool:
    return Project.objects.filter(_q_project(user), pk=project.pk).exists()


def get_projects(user: User | AnonymousUser) -> QuerySet["Project"]:
    queryset = Project.objects.filter(_q_project(user))

    return queryset.distinct().order_by("-created")


def can_update_project(user: User | AnonymousUser, project: Project) -> bool:
    if project.organization:
        return project.organization == user.viisp_organization and user.is_representative_of(project.organization, True)

    if user.is_staff or user.is_superuser:
        return True

    return user == project.user


def get_projects_linkable_to_dataset(user: User | AnonymousUser):
    if not getattr(user, "is_authenticated", False):
        return Project.objects.none()

    queryset = get_projects(user)

    if user.is_staff or user.is_superuser:
        return queryset

    return queryset.filter(Q(organization__isnull=True, user=user) | Q(organization_id__in=_represented_org_ids(user)))

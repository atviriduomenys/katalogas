from vitrina.users.models import User
from vitrina.projects.models import Project
from vitrina.orgs.services import has_perm, is_representative, Action
from vitrina.orgs.models import Representative, Organization
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet


def can_update_project(user: User, project: Project) -> bool:
    if user.is_staff or user.is_superuser:
        return True
    if project.organization:
        return is_representative(user, project.organization)
    return has_perm(user, Action.UPDATE, project)


def can_view_project(user: User, project: Project) -> bool:
    if user.is_staff or user.is_superuser:
        return True
    return can_update_project(user, project) or project.status == Project.APPROVED


def get_projects(user: User, organization: Organization = None) -> QuerySet["Project"]:
    base_queryset = Project.objects.all()

    if organization:
        base_queryset = base_queryset.filter(organization=organization)

    if not getattr(user, "is_authenticated", False):
        return base_queryset.filter(status=Project.APPROVED)

    if user.is_staff or user.is_superuser:
        return base_queryset

    ct = ContentType.objects.get_for_model(Organization)
    representative_org_ids = Representative.objects.filter(
        content_type=ct,
        user=user,
    ).values_list("object_id", flat=True)

    return base_queryset.filter(
        Q(status=Project.APPROVED)
        | Q(organization_id__in=representative_org_ids)
        | Q(organization__isnull=True, user=user)
    ).order_by("-created")

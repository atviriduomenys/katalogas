from vitrina.users.models import User
from vitrina.projects.models import Project
from django.db.models import Q
from django.db.models import QuerySet
from django.contrib.auth.models import AnonymousUser


def visible_projects_filter(user: User | AnonymousUser) -> Q:
    public_approved = Q(is_public=True, status=Project.APPROVED)

    if not getattr(user, "is_authenticated", False):
        return public_approved

    if user.is_staff or user.is_superuser:
        return Q()

    represented_org_ids = user.represented_org_ids

    is_owner = Q(organization__isnull=True, user=user)
    is_org_representative = Q(organization_id__in=represented_org_ids)
    is_dataset_representative = Q(datasets__organization_id__in=represented_org_ids)
    query_filter = public_approved | is_owner | is_org_representative | is_dataset_representative

    return query_filter


def can_view_project(user: User | AnonymousUser, project: Project) -> bool:
    return Project.objects.filter(visible_projects_filter(user), pk=project.pk).exists()


def get_projects(user: User | AnonymousUser) -> QuerySet["Project"]:
    queryset = Project.objects.filter(visible_projects_filter(user))

    return queryset.distinct().order_by("-created")


def can_update_project(user: User | AnonymousUser, project: Project) -> bool:
    if not user.is_authenticated:
        return False
    
    if project.organization:
        return project.organization == user.viisp_organization and user.is_representative_of(project.organization, True)

    if user.is_staff or user.is_superuser:
        return True

    return user == project.user


def get_projects_linkable_to_dataset(user: User | AnonymousUser):
    if not getattr(user, "is_authenticated", False):
        return Project.objects.none()

    queryset = get_projects(user).filter(agreements__isnull=True)

    if user.is_staff or user.is_superuser:
        return queryset

    return queryset.filter(Q(organization__isnull=True, user=user) | Q(organization_id__in=user.represented_org_ids))


def can_manage_datasets(user: User | AnonymousUser, project: Project) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    if project.organization:
        return user.is_representative_of(project.organization)

    return project.user == user


def can_view_clients(user: User | AnonymousUser, project: Project) -> bool:
    if not user.is_authenticated:
        return False
    
    return project.organization and user.is_representative_of(project.organization)


def can_manage_clients(user: User | AnonymousUser, project: Project) -> bool:
    if not user.is_authenticated:
        return False
    
    if project.organization:
        return user.viisp_organization == project.organization and user.is_representative_of(project.organization)
    return False


def can_view_history(user: User | AnonymousUser, project: Project) -> bool:
    if not user.is_authenticated:
        return False
    
    if user.is_staff or user.is_superuser:
        return True

    if project.organization:
        return user.is_representative_of(project.organization)

    return user == project.user

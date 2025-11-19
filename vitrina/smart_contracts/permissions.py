from vitrina.smart_contracts.services import get_agreements
from vitrina.users.models import User
from vitrina.smart_contracts.models import Agreement
from vitrina.projects.models import Project
from django.contrib.auth.models import AnonymousUser


def can_create_agreements(user: User, project: Project) -> bool:
    if project.organization:
        return project.organization == user.viisp_organization and user.is_representative_of(project.organization, True)

    return False


def can_view_agreements(user: User | AnonymousUser, project: Project) -> bool:
    if not user.is_authenticated:
        return False

    represented_org_ids = user.represented_org_ids

    if user.is_staff or user.is_superuser:
        return True

    if project.organization and project.organization.id in represented_org_ids:
        return True

    return project.agreements.filter(assigner_id__in=represented_org_ids).exists()


def can_view_agreement(user: User, agreement: Agreement) -> bool:
    return get_agreements(user).filter(pk=agreement.pk).exists()


def can_upload_agreement_file(user: User, agreement: Agreement) -> bool:
    parties = [agreement.assignee, agreement.assigner]

    return any(user.viisp_organization == party and user.is_representative_of(party, True) for party in parties)

from vitrina.orgs.models import Organization
from vitrina.smart_contracts.services import get_agreements
from vitrina.users.models import User
from vitrina.smart_contracts.models import Agreement
from vitrina.projects.models import Project
from django.contrib.auth.models import AnonymousUser


def _is_viisp_authenticated_and_representative(user: User, organization: Organization | None) -> bool:
    """Helper to find out if a user is VIISP authenticated and a representative of an organization."""
    if not organization:
        return False

    is_viisp_authenticated = organization == user.viisp_organization
    return is_viisp_authenticated and user.is_representative_of(organization, True)


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


def can_create_agreements(user: User, project: Project) -> bool:
    return _is_viisp_authenticated_and_representative(user, project.organization)


def can_submit_agreements(user: User, agreement: Agreement) -> bool:
    return _is_viisp_authenticated_and_representative(user, agreement.assignee)


def can_approve_agreements(user: User, agreement: Agreement) -> bool:
    return _is_viisp_authenticated_and_representative(user, agreement.assigner)


def can_form_agreements(user: User, agreement: Agreement) -> bool:
    is_viisp_authenticated = (
        user.organization in {agreement.assignee, agreement.assigner} and user.organization == user.viisp_organization
    )
    is_representative = user.is_representative_of(agreement.assignee, True) or user.is_representative_of(
        agreement.assigner, True
    )

    return is_viisp_authenticated and is_representative

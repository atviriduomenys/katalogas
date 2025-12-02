from django.contrib.auth.models import AnonymousUser

from vitrina.orgs.models import Organization
from vitrina.users.models import User


def can_view_organization_agreements(user: User | AnonymousUser, organization: Organization) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    user_represented_organization_ids = user.represented_org_ids
    if organization.id in user_represented_organization_ids:
        return True

    return False

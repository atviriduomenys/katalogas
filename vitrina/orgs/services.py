from vitrina.orgs.models import Representative


def has_coordinator_permission(user, organization):
    if user.is_authenticated:
        if user.is_staff:
            return True
        if user.representative_set.filter(organization=organization).exists():
            representative = user.representative_set.filter(organization=organization).first()
            return representative.role == Representative.COORDINATOR
    return False

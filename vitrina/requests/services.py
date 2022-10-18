from vitrina.requests.models import Request
from vitrina.users.models import User


def can_update_request(user: User, request: Request) -> bool:
    if user.is_authenticated:
        if user.is_staff or user.is_superuser:
            return True
        if request.user == user:
            return True
    return False

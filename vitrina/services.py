from typing import Any

from vitrina.datasets.models import Dataset
from vitrina.requests.models import Request
from vitrina.users.models import User


def can_manage_history(obj: Any, user: User) -> bool:
    if user.is_authenticated:
        if user.is_staff or user.is_superuser:
            return True
        if isinstance(obj, (Dataset, Request)) and obj.organization and obj.organization == user.organization:
            return True
    return False

from vitrina.projects.models import Project
from vitrina.users.models import User


def can_update_project(user: User, project: Project) -> bool:
    if user.is_authenticated:
        if user.is_staff or user.is_superuser:
            return True
        if project.user == user:
            return True
    return False

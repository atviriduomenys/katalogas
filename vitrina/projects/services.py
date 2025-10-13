from vitrina.users.models import User
from vitrina.projects.models import Project
from vitrina.orgs.services import has_perm, is_representative, Action


def can_update_project(user: User, project: Project) -> bool:
    if project.organization:
        return is_representative(user, project.organization)
    return has_perm(user, Action.UPDATE, project)


def can_view_project(user: User, project: Project) -> bool:
    return can_update_project(user, project) or project.status == Project.APPROVED

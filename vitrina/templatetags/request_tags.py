from django import template
from vitrina.orgs.services import Action, has_perm

register = template.Library()
assignment_tag = getattr(register, 'assignment_tag', register.simple_tag)


@assignment_tag
def has_organization_remove_perm(request_assignment, user):
    return has_perm(
        user,
        Action.DELETE,
        request_assignment,
        request_assignment.organization
    )

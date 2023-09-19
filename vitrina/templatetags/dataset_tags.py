from django import template
from vitrina.datasets.services import has_remove_from_request_perm as has_perm

register = template.Library()
assignment_tag = getattr(register, 'assignment_tag', register.simple_tag)


@assignment_tag
def has_remove_from_request_perm(dataset, request, user):
    return has_perm(dataset, request, user)

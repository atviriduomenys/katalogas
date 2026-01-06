from django import template

register = template.Library()

@register.simple_tag
def can_update_representative(rep, user):
    return rep.can_be_updated_by(user)

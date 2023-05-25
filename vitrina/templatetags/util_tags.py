from django import template

register = template.Library()
assignment_tag = getattr(register, 'assignment_tag', register.simple_tag)


@assignment_tag
def get_value_by_key(dictionary, key):
    return dictionary.get(key)

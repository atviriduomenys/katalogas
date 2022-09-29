from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from vitrina.likes.models import Like

register = template.Library()


@register.inclusion_tag('component/like.html')
def like(obj, user):
    content_type = ContentType.objects.get_for_model(obj)
    button_text = _("Patinka")
    liked = False
    like_count = Like.objects.filter(content_type=content_type, object_id=obj.pk).count()
    if user.is_authenticated and Like.objects.filter(content_type=content_type, object_id=obj.pk, user=user).exists():
        button_text = _("Nepatinka")
        liked = True
    return {
        'button_text': button_text,
        'liked': liked,
        'like_count': like_count,
        'content_type_id': content_type.pk,
        'obj_id': obj.pk,
        'user': user
    }

from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from vitrina.messages.models import Subscription

register = template.Library()


@register.inclusion_tag('component/subscription.html')
def subscription(obj, user, description=None):
    content_type = ContentType.objects.get_for_model(obj)
    button_text = _("Prenumeruoti")
    subscribed = False
    subscription_count = Subscription.objects.filter(content_type=content_type, object_id=obj.pk).count()
    if user.is_authenticated and \
            Subscription.objects.filter(content_type=content_type, object_id=obj.pk, user=user).exists():
        button_text = _("Atsisakyti prenumeratos")
        subscribed = True
    return {
        'description': description,
        'button_text': button_text,
        'subscribed': subscribed,
        'subscription_count': subscription_count,
        'content_type_id': content_type.pk,
        'obj_id': obj.pk,
        'user': user
    }

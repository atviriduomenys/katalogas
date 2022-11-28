from django import template
from django.contrib.contenttypes.models import ContentType

from vitrina.comments.forms import CommentForm
from vitrina.comments.models import Comment
from vitrina.comments.services import get_comment_form_class

register = template.Library()


@register.inclusion_tag('component/comments.html')
def comments(obj, user):
    content_type = ContentType.objects.get_for_model(obj)
    obj_comments = Comment.public.filter(
        content_type=content_type,
        object_id=obj.pk,
        parent_id__isnull=True
    ).order_by('created')
    comment_form_class = get_comment_form_class(obj, user)
    return {
        'comments': obj_comments,
        'user': user,
        'content_type': content_type,
        'object': obj,
        'comment_form': comment_form_class(obj),
        'reply_form': CommentForm(obj)
    }

from django import template
from django.contrib.contenttypes.models import ContentType

from vitrina.comments.forms import CommentForm
from vitrina.comments.models import Comment
from vitrina.comments.services import get_comment_form_class
from vitrina.orgs.services import has_perm, Action

register = template.Library()


@register.inclusion_tag('component/comments.html')
def comments(obj, user):
    content_type = ContentType.objects.get_for_model(obj)
    obj_comments = Comment.objects.filter(
        content_type=content_type,
        object_id=obj.pk,
        parent_id__isnull=True
    ).order_by('created')
    if not has_perm(user, Action.COMMENT, obj):
        obj_comments = obj_comments.filter(is_public=True)
    comment_form_class = get_comment_form_class(obj, user)
    comments_array = []
    for comment in obj_comments:
        children = comment.descendants(user=user, obj=obj)
        comments_array.append((comment, children))
    return {
        'comments': comments_array,
        'user': user,
        'content_type': content_type,
        'object': obj,
        'comment_form': comment_form_class(),
        'reply_form': CommentForm()
    }

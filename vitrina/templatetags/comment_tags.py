from django import template
from django.contrib.contenttypes.models import ContentType

from vitrina.comments.forms import CommentForm
from vitrina.comments.models import Comment
from vitrina.comments.services import get_comment_form_class
from vitrina.datasets.models import Dataset
from vitrina.orgs.services import has_perm, Action
from vitrina.requests.models import Request
from vitrina.structure.models import Metadata

register = template.Library()


@register.inclusion_tag('component/comments.html')
def comments(obj, user, is_structure=False):
    content_type = ContentType.objects.get_for_model(obj)
    obj_comments = Comment.objects.filter(
        content_type=content_type,
        object_id=obj.pk,
        parent_id__isnull=True
    ).order_by('created')
    perm = has_perm(user, Action.COMMENT, obj)
    if not perm:
        obj_comments = obj_comments.filter(is_public=True)
    if is_structure:
        can_manage_structure = has_perm(
            user,
            Action.STRUCTURE,
            Dataset,
            obj
        )
        if not can_manage_structure:
            obj_comments = obj_comments.exclude(
                type=Comment.STRUCTURE,
                metadata__access__lt=Metadata.PUBLIC
            )
    comment_form_class = get_comment_form_class(obj, user)

    comments_array = []
    for comment in obj_comments:
        descendants = comment.descendants(include_self=True)
        for reply in descendants:
            reply_form = CommentForm(reply)
            is_child = reply.parent is not None
            comments_array.append((reply, reply_form, is_child))

    return {
        'comments': comments_array,
        'user': user,
        'content_type': content_type,
        'object': obj,
        'comment_form': comment_form_class(obj),
        'submit_button_id': "id_submit_button_request" if isinstance(obj, Request) else "id_submit_button"
    }


@register.inclusion_tag('component/comments.html')
def external_comments(content_type, object_id, user, dataset):
    obj_comments = Comment.objects.filter(
        external_content_type=content_type,
        external_object_id=object_id,
        parent_id__isnull=True
    ).order_by('created')
    perm = has_perm(
            user,
            Action.STRUCTURE,
            Dataset,
            dataset.current_structure
        )
    if not perm:
        obj_comments = obj_comments.filter(is_public=True)
    comments_array = []
    for comment in obj_comments:
        children = comment.descendants(permission=perm)
        reply_form = CommentForm(comment, auto_id='id_%s_' + str(comment.id))
        comments_array.append((comment, children, reply_form))
    comment_form_class = get_comment_form_class()
    return {
        'comments': comments_array,
        'user': user,
        'content_type': content_type,
        'object_id': object_id,
        'comment_form': comment_form_class(None),
        'submit_button_id': "id_submit_button",
        'external': True,
        'dataset': dataset,
    }

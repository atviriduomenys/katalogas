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
assignment_tag = getattr(register, 'assignment_tag', register.simple_tag)


@register.inclusion_tag('component/comments.html')
def comments(obj, user, is_structure=False):
    content_type = ContentType.objects.get_for_model(obj)
    obj_comments = Comment.objects.filter(
        content_type=content_type,
        object_id=obj.pk,
        parent_id__isnull=True
    ).order_by('created')
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
    is_opened = obj.is_opened() if hasattr(obj, "is_opened") else None

    comments_array = []
    for comment in obj_comments:
        if has_comment_view_perm(comment, obj, user):
            descendants = comment.descendants(include_self=True, permission=True)
            for reply in descendants:
                if has_comment_view_perm(reply, obj, user):
                    reply_form = CommentForm(reply)
                    is_child = reply.parent is not None
                    comments_array.append((reply, reply_form, is_child))

    return {
        'comments': comments_array,
        'user': user,
        'content_type': content_type,
        'object': obj,
        'comment_form': comment_form_class(obj, is_opened=is_opened),
        'submit_button_id': "id_submit_button_request" if isinstance(obj, Request) else "id_submit_button"
    }


@register.inclusion_tag('component/comments.html')
def external_comments(content_type, object_id, user, dataset):
    obj_comments = Comment.objects.filter(
        external_content_type=content_type,
        external_object_id=object_id,
        parent_id__isnull=True
    ).order_by('created')
    comments_array = []
    for comment in obj_comments:
        if has_comment_view_perm(comment, dataset, user):
            descendants = comment.descendants(include_self=True, permission=True)
            for reply in descendants:
                if has_comment_view_perm(reply, dataset, user):
                    reply_form = CommentForm(comment, auto_id='id_%s_' + str(comment.id))
                    is_child = reply.parent is not None
                    comments_array.append((reply, reply_form, is_child))
    comment_form_class = get_comment_form_class()
    return {
        'comments': comments_array,
        'user': user,
        'content_type': content_type,
        'object_id': object_id,
        'comment_form': comment_form_class(None, is_opened=dataset.is_opened()),
        'submit_button_id': "id_submit_button",
        'external': True,
        'dataset': dataset,
        'object': dataset
    }


def has_comment_view_perm(comment, obj, user):
    parent_comments = comment.ancestors()
    for c in reversed(parent_comments):
        if c.user == user:
            return True
        if (
            not c.is_public and
            not has_perm(user, Action.COMMENT, obj)
        ):
            return False

    if (
        comment.is_public or
        user == comment.user
    ):
        return True
    else:
        return has_perm(user, Action.COMMENT, obj)

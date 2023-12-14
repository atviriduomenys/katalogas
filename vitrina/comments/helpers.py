from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from vitrina.comments.models import Comment
from vitrina.datasets.models import Dataset
from vitrina.messages.helpers import prepare_email_by_identifier_for_sub # this function will be renamed to email
from vitrina.messages.models import Subscription
from vitrina.tasks.models import Task


def get_title_description_by_comment_type(comment_type, content_type, object_id):
    if comment_type == "Reply":
        title = f"Parašytas atsakymas komentarui: {content_type}, id: {object_id}"
        description = f"Atsakyta į komentarą {content_type}, id: {object_id}."
    else:
        title = f"Parašytas komentaras objektui: {content_type}, id: {object_id}"
        description = f"Prie {content_type} {object_id} parašytas naujas komentaras."
    return title, description


def create_task(comment_type, content_type, object_id, user, obj=None, comment_object=None, comment_ct=None):
    organization = obj.organization if hasattr(obj, 'organization') else None

    title, description = get_title_description_by_comment_type(comment_type,
                                                               comment_ct if comment_ct else content_type,
                                                               object_id)
    Task.objects.create(
        title=title,
        organization=organization,
        description=description,
        content_type=content_type if isinstance(content_type, ContentType) else None,
        object_id=obj.pk if obj else object_id if isinstance(object_id, int) else None,
        status=Task.CREATED,
        user=user,
        type=Task.COMMENT,
        comment_object=comment_object
    )


def create_subscription(user, comment):
    return Subscription.objects.create(
        user=user,
        content_type=ContentType.objects.get_for_model(Comment),
        object_id=comment.pk,
        sub_type=Subscription.COMMENT,
        email_subscribed=True,
        comment_replies_sub=True
    )


def send_mail_and_create_tasks_for_subs(comment_type, content_type, object_id, user, obj=None, comment_object=None):
    object_subs = Subscription.objects.exclude(user=user).filter(
        sub_type=content_type.model.upper(),
        content_type=content_type,
        object_id=object_id,
    )
    org_subs = []
    email_list = []
    org_email_list = []
    if obj and isinstance(obj, Dataset) and obj.organization:
        org_subs = Subscription.objects.exclude(user=user).filter(
            sub_type=Subscription.ORGANIZATION,
            content_type=ContentType.objects.get_for_model(obj.organization),
            object_id=obj.organization.pk,
        )

    for sub in object_subs:
        if sub.dataset_comments_sub or sub.request_comments_sub or sub.project_comments_sub:
            create_task(
                comment_type=comment_type,
                content_type=content_type,
                object_id=object_id,
                user=sub.user,
                obj=obj,
                comment_object=comment_object
            )
        if sub.user.email:
            email_list.append(sub.user.email)
    for sub in org_subs:
        if sub.dataset_comments_sub or sub.request_comments_sub or sub.project_comments_sub:
            create_task(
                comment_type=comment_type,
                content_type=content_type,
                object_id=object_id,
                user=sub.user,
                obj=obj,
                comment_object=comment_object
            )
            if sub.user.email and sub.user.email not in email_list:
                org_email_list.append(sub.user.email)
    send_mail_to_object_subscribers(email_list, content_type, object_id)
    if len(org_subs) > 0:
        send_mail_to_object_subscribers(email_list, content_type, object_id, org=obj.organization)


def send_mail_to_object_subscribers(
    email_list,
    content_type,
    object_id,
    org=None,
):
    try:
        obj = content_type.model_class().get(pk=object_id)
    except content_type.model_class().DoesNotExist:
        obj = None
    if isinstance(object, Comment):
        obj = None  # FIXME: Get real comment object
    prepare_email_by_identifier_for_sub(email_list, 'vitrina/comments/emails/sub/created', { # will be renamed to email
        'object': obj,
        'comment': '',  # FIXME: Add comment text
    })


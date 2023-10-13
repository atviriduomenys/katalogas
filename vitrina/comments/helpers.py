from django.contrib.contenttypes.models import ContentType

from vitrina.comments.models import Comment
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
        content_type=content_type,
        object_id=obj.pk,
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


def create_subscriptions_and_tasks(comment_type, content_type, object_id, user, obj=None, comment_object=None):
    object_subs = Subscription.objects.exclude(user=user).filter(
        sub_type=content_type.model.upper(),
        content_type=content_type,
        object_id=object_id,
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

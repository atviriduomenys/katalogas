from typing import Any

from django import template
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.functional import SimpleLazyObject

from vitrina.comments.forms import CommentForm
from vitrina.comments.models import Comment
from vitrina.comments.services import get_comment_form_class
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.projects.models import Project
from vitrina.resources.models import DatasetDistribution
from vitrina.orgs.models import Representative, Organization
from vitrina.orgs.services import has_perm, Action
from vitrina.requests.models import Request, RequestAssignment
from vitrina.structure.models import Metadata, Model, Property


register = template.Library()
assignment_tag = getattr(register, "assignment_tag", register.simple_tag)


@register.inclusion_tag("component/comments.html", takes_context=True)
def comments(context, obj: "Model", user: SimpleLazyObject, is_structure: bool = False) -> dict[str, Any]:
    object_content_type = ContentType.objects.get_for_model(obj)

    query_filters = Q(content_type=object_content_type, object_id=obj.pk)
    if isinstance(obj, Model) and obj.base:
        base_obj = obj.base
        base_content_type = ContentType.objects.get_for_model(base_obj)
        query_filters |= Q(content_type=base_content_type, object_id=base_obj.pk)

    object_comments = Comment.objects.filter(query_filters, parent_id__isnull=True).order_by("-created")

    if is_structure:
        can_manage_structure = has_perm(user, Action.STRUCTURE, Dataset, obj)
        if not can_manage_structure:
            object_comments = object_comments.exclude(type=Comment.STRUCTURE, metadata__access__lt=Metadata.PUBLIC)

    comment_form_class = get_comment_form_class(obj, user)
    is_opened = obj.is_opened() if hasattr(obj, "is_opened") else None

    comments_array = []
    for comment in object_comments:
        if has_comment_view_perm(comment, obj, user):
            descendants = comment.descendants(include_self=True, permission=True)
            for reply in descendants:
                if has_comment_view_perm(reply, obj, user):
                    reply_form = CommentForm(reply)
                    is_child = reply.parent is not None
                    comments_array.append((reply, reply_form, is_child))

    return {
        "comments": comments_array,
        "user": user,
        "content_type": object_content_type,
        "object": obj,
        "comment_form": comment_form_class(obj, is_opened=is_opened),
        "submit_button_id": "id_submit_button_request" if isinstance(obj, Request) else "id_submit_button",
        "request": context["request"],
    }


@register.inclusion_tag("component/comments.html", takes_context=True)
def external_comments(context, content_type, object_id, user, dataset):
    obj_comments = Comment.objects.filter(
        external_content_type=content_type,
        external_object_id=object_id,
        parent_id__isnull=True,
    ).order_by("-created")
    comments_array = []
    for comment in obj_comments:
        if has_comment_view_perm(comment, dataset, user):
            descendants = comment.descendants(include_self=True, permission=True)
            for reply in descendants:
                if has_comment_view_perm(reply, dataset, user):
                    reply_form = CommentForm(comment, auto_id="id_%s_" + str(comment.id))
                    is_child = reply.parent is not None
                    comments_array.append((reply, reply_form, is_child))
    comment_form_class = get_comment_form_class()
    return {
        "comments": comments_array,
        "user": user,
        "content_type": content_type,
        "object_id": object_id,
        "comment_form": comment_form_class(None, is_opened=dataset.is_opened()),
        "submit_button_id": "id_submit_button",
        "external": True,
        "dataset": dataset,
        "object": dataset,
        "request": context["request"],
    }


def has_comment_view_perm(comment, obj, user):
    parent_comments = comment.ancestors()
    for c in reversed(parent_comments):
        if c.user == user:
            return True
        if not c.is_public and not has_perm(user, Action.COMMENT, obj):
            return False

    if comment.is_public or user == comment.user:
        return True
    else:
        return has_perm(user, Action.COMMENT, obj)


@register.simple_tag
def get_author_name(comment, user):
    if isinstance(user, AnonymousUser):
        return "Sistemos naudotojas"

    if user == comment.user or user.is_superuser:
        return f"{comment.user.first_name} {comment.user.last_name}"

    # vitrina_datasets
    if (
        comment.content_type.model == "dataset"
        and Representative.objects.filter(
            user=user,
            role__in=Representative.COORDINATOR_ROLES + Representative.MANAGER_ROLES,
            content_type=comment.content_type,
            object_id=comment.object_id,
        ).exists()
    ):
        return f"{comment.user.first_name} {comment.user.last_name}"

    # vitrina_datasets
    if comment.content_type.model == "datasetstructure":
        dataset_id = DatasetStructure.objects.values_list("dataset_id", flat=True).get(pk=comment.object_id)
        organization_id = Dataset.objects.values_list("organization_id", flat=True).get(pk=dataset_id)
        if Representative.objects.filter(
            user=user,
            role__in=Representative.COORDINATOR_ROLES + Representative.MANAGER_ROLES,
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=organization_id,
        ).exists():
            return f"{comment.user.first_name} {comment.user.last_name}"

    # vitrina_resources
    if comment.content_type.model == "datasetdistribution":
        dataset_id = DatasetDistribution.objects.values_list("dataset_id", flat=True).get(pk=comment.object_id)
        organization_id = Dataset.objects.values_list("organization_id", flat=True).get(pk=dataset_id)
        if Representative.objects.filter(
            user=user,
            role__in=Representative.COORDINATOR_ROLES + Representative.MANAGER_ROLES,
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=organization_id,
        ).exists():
            return f"{comment.user.first_name} {comment.user.last_name}"

    # vitrina_structure
    if comment.content_type.model == "model":
        dataset_id = Model.objects.filter(pk=comment.object_id).values_list("dataset_id", flat=True).first()
        organization_id = Dataset.objects.filter(pk=dataset_id).values_list("organization_id", flat=True).first()
        if Representative.objects.filter(
            user=user,
            role__in=Representative.COORDINATOR_ROLES + Representative.MANAGER_ROLES,
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=organization_id,
        ).exists():
            return f"{comment.user.first_name} {comment.user.last_name}"

    # vitrina_structure
    if comment.content_type.model == "property":
        model_id = Property.objects.values_list("model_id", flat=True).get(pk=comment.object_id)
        dataset_id = Model.objects.values_list("dataset_id", flat=True).get(pk=model_id)
        organization_id = Dataset.objects.values_list("organization_id", flat=True).get(pk=dataset_id)
        if Representative.objects.filter(
            user=user,
            role__in=Representative.COORDINATOR_ROLES + Representative.MANAGER_ROLES,
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=organization_id,
        ).exists():
            return f"{comment.user.first_name} {comment.user.last_name}"

    # vitrina_requests
    if comment.content_type.model == "request":
        organization_ids = RequestAssignment.objects.filter(request=comment.object_id).values_list(
            "organization_id", flat=True
        )
        if user.representative_set.filter(
            object_id__in=organization_ids,
            content_type=ContentType.objects.get_for_model(Organization),
        ).exists():
            return f"{comment.user.first_name} {comment.user.last_name}"

    # vitrina_projects
    if comment.content_type.model == "project":
        organization_id = Project.objects.filter(pk=comment.object_id).first().user.organization
        if user.representative_set.filter(
            object_id=organization_id.pk,
            content_type=ContentType.objects.get_for_model(Organization),
        ).exists():
            return f"{comment.user.first_name} {comment.user.last_name}"

    return "Sistemos naudotojas"

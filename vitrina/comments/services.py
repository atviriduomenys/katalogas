from typing import Type

from django.db.models import Model

from vitrina.comments.forms import DatasetCommentForm, RequestCommentForm, CommentForm
from vitrina.datasets.models import Dataset
from vitrina.orgs.services import has_perm, Action
from vitrina.requests.models import Request
from vitrina.users.models import User


def get_comment_form_class(obj: Model, user: User) -> Type:
    if isinstance(obj, Dataset):
        return DatasetCommentForm
    elif isinstance(obj, Request) and has_perm(user, Action.COMMENT, obj):
        return RequestCommentForm
    return CommentForm

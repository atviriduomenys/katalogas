from typing import Type

from django.db import models

from vitrina.comments.forms import DatasetCommentForm, RequestCommentForm, CommentForm, ProjectCommentForm, \
    RegisterRequestForm
from vitrina.datasets.models import Dataset
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project
from vitrina.requests.models import Request
from vitrina.structure.models import Property, Model
from vitrina.users.models import User


def get_comment_form_class(obj: models.Model = None, user: User = None) -> Type:
    if isinstance(obj, Dataset):
        return DatasetCommentForm
    elif isinstance(obj, Request) and has_perm(user, Action.COMMENT, obj):
        return RequestCommentForm
    elif isinstance(obj, Project) and has_perm(user, Action.COMMENT, obj):
        return ProjectCommentForm
    elif isinstance(obj, (Property, Model)) or obj is None:
        return RegisterRequestForm
    return CommentForm

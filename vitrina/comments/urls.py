from django.urls import path

from vitrina.comments.views import CommentView, ReplyView, delete_comment
from vitrina.comments.views import ExternalCommentView, ExternalReplyView

urlpatterns = [
    path(
        "comments/<int:content_type_id>/<int:object_id>/comment/",
        CommentView.as_view(),
        name="comment",
    ),
    path(
        "comments/<int:dataset_id>/<str:external_content_type>/<str:external_object_id>/comment/",
        ExternalCommentView.as_view(),
        name="external-comment",
    ),
    path(
        "comments/<int:content_type_id>/<int:object_id>/<int:parent_id>/reply/",
        ReplyView.as_view(),
        name="reply",
    ),
    path(
        "comments/<str:external_content_type>/<str:external_object_id>/<int:parent_id>/reply/",
        ExternalReplyView.as_view(),
        name="external-reply",
    ),
    path(
        "comments/<int:pk>/delete/",
        delete_comment,
        name="delete-comment",
    ),
]

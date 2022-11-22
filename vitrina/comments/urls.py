from django.urls import path

from vitrina.comments.views import CommentView, ReplyView

urlpatterns = [
    path('comments/<int:content_type_id>/<int:object_id>/comment/', CommentView.as_view(), name='comment'),
    path('comments/<int:content_type_id>/<int:object_id>/<int:parent_id>/reply/', ReplyView.as_view(), name='reply'),
]

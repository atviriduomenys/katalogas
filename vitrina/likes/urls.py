from django.urls import path

from vitrina.likes.views import LikeView, UnlikeView

urlpatterns = [
    path('like/<int:content_type_id>/<int:obj_id>/<int:user_id>/', LikeView.as_view(), name='like'),
    path('unlike/<int:content_type_id>/<int:obj_id>/<int:user_id>/', UnlikeView.as_view(), name='unlike'),
]

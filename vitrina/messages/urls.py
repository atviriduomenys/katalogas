from django.urls import path

from vitrina.messages.views import SubscribeView, UnsubscribeView

urlpatterns = [
    path('subscribe/<int:content_type_id>/<int:obj_id>/<int:user_id>/', SubscribeView.as_view(), name='subscribe'),
    path('unsubscribe/<int:content_type_id>/<int:obj_id>/<int:user_id>/', UnsubscribeView.as_view(),
         name='unsubscribe'),
    # @PostMapping("/subscribeNewsletter")
    # @GetMapping("/unsubscribe/{hash}")
]

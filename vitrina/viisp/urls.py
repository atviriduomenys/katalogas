from django.urls import path

from vitrina.viisp.views import viisp_login

urlpatterns = [
    path('viisp/login/', viisp_login, name='viisp_login'),
    # @GetMapping("/viisp/login")
]

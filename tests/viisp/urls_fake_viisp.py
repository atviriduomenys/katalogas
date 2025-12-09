from django.http import HttpResponse
from django.urls import path
from vitrina import urls as base_urls
from vitrina.viisp.views import FakeVIISPCompleteLoginView
from django.views.i18n import JavaScriptCatalog, set_language
from django.contrib.auth import views as auth_views

def home_view(request):
    # Paprastas „home“ tik testams
    return HttpResponse("home")

def newsletter_subscribe_view(request):
    # Minimalus stub'as – užtenka, kad egzistuotų vardas 'newsletter-subscribe'
    return HttpResponse("newsletter subscribe")

urlpatterns = [
    # Pagrindinis "home", į kurį redirectina sėkmingas login'as
    path("", home_view, name="home"),

    # JS katalogas, kurio prašo template'ai: {% url 'javascript-catalog' %}
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),

    # Tikras Django login view, su vardu 'login'
    path("login/", auth_views.LoginView.as_view(), name="login"),

    # I18n kalbos keitimo view, kurio prašo template'ai: {% url 'set_language' %}
    path("i18n/setlang/", set_language, name="set_language"),

    # Newsletter prenumeratos stub'as: {% url 'newsletter-subscribe' %}
    path("newsletter/subscribe/", newsletter_subscribe_view, name="newsletter-subscribe"),

    # Fake VIISP kelias, kurį testuojam
    path(
        "fake-viisp/complete-login/",
        FakeVIISPCompleteLoginView.as_view(),
        name="fake-viisp-complete-login",
    ),
]

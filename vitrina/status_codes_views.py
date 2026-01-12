from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def handler404(request: HttpRequest, exception: Exception = None) -> HttpResponse:
    return render(request, "status_codes/404.html", status=404)


def handler500(request: HttpRequest, exception: Exception = None) -> HttpResponse:
    return render(request, "status_codes/500.html", status=500)


def handler403(request: HttpRequest, exception: Exception = None) -> HttpResponse:
    return render(request, "status_codes/403.html", status=403)


def handler400(request: HttpRequest, exception: Exception = None) -> HttpResponse:
    return render(request, "status_codes/400.html", status=400)

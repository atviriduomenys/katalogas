from datetime import datetime

from django.http import HttpRequest
from django.utils import timezone
from django.views.generic import View

from rest_framework.permissions import BasePermission

from vitrina.api.models import ApiKey


class APIKeyPermission(BasePermission):

    def has_permission(self, request: HttpRequest, view: View):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.lower().startswith('apikey '):
            _, api_key = auth.split(None, 1)
            api_key = api_key.strip()
        else:
            return False

        if api_key:
            api_key_obj = (
                ApiKey.objects.
                filter(api_key=api_key).
                first()
            )
        else:
            return False

        return (
            api_key_obj and
            api_key_obj.enabled and (
                not api_key_obj.expires or
                api_key_obj.expires > timezone.make_aware(datetime.now())
            )
        )

from datetime import datetime

from django.utils import timezone
from rest_framework.permissions import BasePermission

from vitrina.api.models import ApiKey


class APIKeyPermission(BasePermission):
    def has_permission(self, request, view):
        api_key = request.META.get('HTTP_AUTHORIZATION')
        if api_key and ApiKey.objects.filter(api_key=api_key).exists():
            api_key_obj = ApiKey.objects.filter(api_key=api_key).first()
            if api_key_obj.enabled and (
                    not api_key_obj.expires or
                    api_key_obj.expires > timezone.make_aware(datetime.now())
            ):
                return True
        return False

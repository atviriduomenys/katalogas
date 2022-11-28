from django.http import HttpRequest
from django.views.generic import View

from rest_framework.permissions import BasePermission

from vitrina.api.services import get_api_key_organization


class APIKeyPermission(BasePermission):

    def has_permission(self, request: HttpRequest, view: View):
        if get_api_key_organization(request):
            return True
        return False

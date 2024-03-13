from django.http import HttpRequest
from django.views.generic import View

from rest_framework.permissions import BasePermission

from vitrina.api.services import get_api_key_organization_and_user


class APIKeyPermission(BasePermission):

    def has_permission(self, request: HttpRequest, view: View):
        organization, user = get_api_key_organization_and_user(request)
        if organization and user:
            view.organization = organization
            view.user = user
            return True
        return False


class HasStatsPostPermission(BasePermission):

    def has_permission(self, request, view):
        organization, user = get_api_key_organization_and_user(request)
        if user:
            if user.is_superuser or user.is_staff:
                return True
        return False

from django.http import HttpRequest
from django.views.generic import View

from rest_framework.permissions import BasePermission

from vitrina.api.services import get_api_key_organization_and_user


class APIKeyPermission(BasePermission):
    def has_permission(self, request: HttpRequest, view: View):
        organization, user, dataset, organization_role, publisher = get_api_key_organization_and_user(request)

        if dataset and (user or publisher) and dataset.id == view.kwargs.get("datasetId"):
            view.organization = organization
            view.user = user
            view.dataset = dataset
            view.publisher = publisher
            view.organization_role = organization_role
            return True

        if organization and (user or publisher) and not dataset:
            view.organization = organization
            view.user = user
            view.publisher = publisher
            view.organization_role = organization_role
            return True
        return False


class HasStatsPostPermission(BasePermission):
    def has_permission(self, request, view):
        organization, user, dataset, organization_role, publisher = get_api_key_organization_and_user(request)
        if user:
            if user.is_superuser or user.is_staff:
                return True
        return False

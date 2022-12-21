from django.http import HttpRequest
from django.views.generic import View
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException

from rest_framework.permissions import BasePermission

from vitrina.api.services import get_api_key_organization_and_user


class APIKeyPermission(BasePermission):

    def has_permission(self, request: HttpRequest, view: View):
        organization, user = get_api_key_organization_and_user(request)
        if organization and user:
            view.organization = organization
            view.user = user
            return True
        raise APIKeyException()


class APIKeyException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("Neteisingas arba negaliojantis raktas. "
                       "Raktą galite atsinaujinti savo organizacijos tvarkytojų sąraše.")
    default_code = 'wrong_api_key'

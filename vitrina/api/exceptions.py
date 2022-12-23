from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class DuplicateAPIKeyException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("Raktas yra pasidubliuojantis, todėl nebegalioja. "
                       "Raktą galite atsinaujinti savo organizacijos tvarkytojų sąraše.")
    default_code = 'duplicate_api_key'
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class DuplicateAPIKeyException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _(
        "Baigėsi Jūsų API rakto galiojimas. "
        "Raktą galite atsinaujinti savo organizacijos tvarkytojų sąraše: {url}"
    )
    default_code = 'duplicate_api_key'

    def __init__(self, detail=None, code=None, url=None):
        if url:
            detail = self.default_detail.format(url=url)
        super().__init__(detail, code)

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured

from vitrina import settings


class ApiConfig(AppConfig):
    name = "vitrina.api"
    label = "vitrina_api"

    def ready(self):
        if settings.OAUTH_SERVER_PUBLIC_JWK_JSON and settings.OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_PATH:
            raise ImproperlyConfigured(
                "OAUTH_SERVER_PUBLIC_JWK_JSON and OAUTH_SERVER_PUBLIC_JWK_DOWNLOAD_PATH "
                "cannot be used at the same time. Define only one."
            )

import uuid

import pytest
from django.urls import URLPattern
from django_webtest import DjangoTestApp
from rest_framework import status

from vitrina.uapi.enums import UdtsCatalogEnum
from vitrina.uapi.urls import urlpatterns


def get_catalog_paths() -> list:
    """Return all URL routes that include the <catalog:catalog> path converter."""
    paths = []
    for pattern in urlpatterns:
        if not isinstance(pattern, URLPattern):
            continue
        if "<catalog:catalog>" in pattern.pattern._route:
            paths.append(pattern.pattern._route)
    return paths


class TestUapiUrls:
    @staticmethod
    def _build_url(current_url: str, placeholders: dict) -> str:
        built_url = current_url
        for key, value in placeholders.items():
            built_url = built_url.replace(
                f"<uuid:{key}>", str(value)
            ).replace(
                f"<str:{key}>", str(value)
            ).replace(
                f"<catalog:{key}>", str(value)
            )

        if not built_url.startswith("/"):
            built_url = "/" + built_url

        return built_url


    @pytest.mark.parametrize("catalog", [catalog.value for catalog in UdtsCatalogEnum])
    @pytest.mark.parametrize("route", get_catalog_paths())
    def test_success_custom_url_converter_for_catalog(
        self,
        app: DjangoTestApp,
        catalog: UdtsCatalogEnum,
        route: str,
        valid_token: str,
    ):
        placeholders = {
            "organization_id": 1,
            "agreement_id": uuid.uuid4(),
            "catalog": catalog,
        }
        url = self._build_url(route, placeholders)

        response = app.options(
            url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"}
        )

        assert status.is_success(response.status_code), f"{url=} not reachable"

    @pytest.mark.parametrize("route", get_catalog_paths())
    def test_failure_custom_url_converter_for_catalog_unsupported_catalog_name(
        self,
        app: DjangoTestApp,
        route: str,
        valid_token: str
    ):
        non_existent_catalog_name = "UNSUPPORTED_CATALOG_NAME"
        placeholders = {
            "organization_id": 1,
            "agreement_id": uuid.uuid4(),
            "catalog": non_existent_catalog_name,
        }

        url = self._build_url(route, placeholders)

        response = app.options(
            url,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True
        )

        assert status.is_client_error(response.status_code), f"{url=} is not supported, but was called successfully"

from typing import Iterable
from unittest.mock import ANY

import pytest
from authlib.jose import RSAKey
from django.conf import settings
from django_webtest import DjangoTestApp
from rest_framework import status

from tests.uapi.conftest import _generate_test_token
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.structure.factories import VersionFactory


class TestList:
    def test_success(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_version: str,
        domain: str,
        valid_token: str,
    ):
        version = dataset.metadata.first().metadata_version
        response = app.get(url_version, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "@context": "",
                    "_created": ANY,
                    "_updated": "",
                    "_txn": "",
                    "_revision": "",
                    "_id": str(version.pk),
                    "_type": "datasets/gov/vssa/ror/dcat/Version",
                    "major": version.major,
                    "minor": version.minor,
                    "patch": version.patch,
                    "external_version": version.external_version,
                    "version_type": version.version_type,
                    "status": version.status,
                    "deployed": version.deployed,
                    "description": version.description,
                    "released": version.released,
                    "version": version.version,
                    "dataset_id": version.dataset_id,
                }
            ]
        }

    def test_success_specific_scope_given(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_version: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        version = dataset.metadata.first().metadata_version
        token = _generate_test_token(
            test_jwk,
            organization=organization,
            scopes=["uapi:/datasets/gov/vssa/dcat/Version/:getall"],
        )

        response = app.get(url_version, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "@context": "",
                    "_created": ANY,
                    "_updated": "",
                    "_txn": "",
                    "_revision": "",
                    "_id": str(version.pk),
                    "_type": "datasets/gov/vssa/ror/dcat/Version",
                    "major": version.major,
                    "minor": version.minor,
                    "patch": version.patch,
                    "external_version": version.external_version,
                    "version_type": version.version_type,
                    "status": version.status,
                    "deployed": version.deployed,
                    "description": version.description,
                    "released": version.released,
                    "version": version.version,
                    "dataset_id": version.dataset_id,
                }
            ]
        }

    def test_success_call_with_query_parameters(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_version: str,
        domain: str,
        valid_token: str,
    ):
        another_dataset = DatasetFactory()
        version = dataset.metadata.first().metadata_version
        another_dataset.metadata.first().metadata_version  # Would be returned as well, if not for the specific query parameters.

        response = app.get(
            url_version,
            params={"dataset_id": version.dataset.pk},
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json) == 1
        assert response.json == {
            "_data": [
                {
                    "@context": "",
                    "_created": ANY,
                    "_updated": "",
                    "_txn": "",
                    "_revision": "",
                    "_id": str(version.pk),
                    "_type": "datasets/gov/vssa/ror/dcat/Version",
                    "major": version.major,
                    "minor": version.minor,
                    "patch": version.patch,
                    "external_version": version.external_version,
                    "version_type": version.version_type,
                    "status": version.status,
                    "deployed": version.deployed,
                    "description": version.description,
                    "released": version.released,
                    "version": version.version,
                    "dataset_id": version.dataset_id,
                }
            ]
        }

    @pytest.mark.parametrize("invalid_scopes", [["invalid_scope"], [], [""]])
    def test_necessary_scope_missing_from_token(
        self,
        invalid_scopes: Iterable[str],
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_version: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        VersionFactory(dataset=dataset)
        token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)

        response = app.get(url_version, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }


    def test_organization_id_missing_from_token(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_version: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        VersionFactory(dataset=dataset)
        token = _generate_test_token(test_jwk, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)

        response = app.get(url_version, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }

    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_version: str,
        domain: str,
        valid_token_disabled_agent: str,
    ):
        response = app.get(
            url_version,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token_disabled_agent}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "The agent is disabled. Enable the agent in the Data catalog to access this API.",
            "additionalProperties": None,
        }

    def test_no_versions_found(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_version: str,
        domain: str,
        valid_token: str,
    ):
        response = app.get(
            url_version,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {"_data": []}

    def test_no_datasets_belonging_to_organization_found(
        self,
        app: DjangoTestApp,
        url_version: str,
        domain: str,
        valid_token: str,
    ):
        another_organization = OrganizationFactory()
        dataset = DatasetFactory(organization=another_organization)
        VersionFactory(dataset=dataset)

        response = app.get(
            url_version,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {"_data": []}

from typing import Iterable
from unittest.mock import patch, PropertyMock

import pytest
import pytz
from authlib.jose import RSAKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from reversion.models import Version

from tests.uapi.conftest import _generate_test_token
from vitrina import settings
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.factories import MetadataFactory
from vitrina.uapi.serializers.uapi_serializers import TYPE_PREFIX_TO_REMOVE


pytestmark = pytest.mark.django_db
timezone = pytz.timezone(settings.TIME_ZONE)


class TestCreate:
    def test_success(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_distribution: str,
        domain: str,
        valid_token: str,
    ):
        file_content = b"Sample CSV content"
        data = {
            "dataset": str(dataset.id),
            "title": "Title",
        }

        response = app.post(
            url_distribution,
            data,
            upload_files=[("file", "test.csv", file_content)],
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        distribution = DatasetDistribution.objects.filter(
            metadata__name=dataset.datasetdistribution_set.first().metadata.name,
            dataset__organization__kind=organization.kind,
            dataset__organization__name=organization.name,
        ).first()
        assert distribution
        assert response.json == {
            "@context": "",
            "_type": url_distribution.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
            "_id": str(distribution.id),
            "_revision": "",
            "_txn": "",
            "_created": distribution.created.astimezone(timezone).isoformat(),
            "_updated": distribution.modified.astimezone(timezone).isoformat(),
            "description": distribution.description,
            "file": distribution.file.label,
            "id": distribution.id,
            "issued": distribution.issued,
            "periodEnd": distribution.period_end,
            "periodStart": distribution.period_start,
            "geo_location": distribution.geo_location,
            "title": data["title"],
            "type": distribution.type,
            "url": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
            "version": None,
            "upload_to_storage": distribution.upload_to_storage,
            "data_last_updated": None,
        }

    def test_specific_scope(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_distribution: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(
            test_jwk,
            organization=organization,
            scopes=["uapi:/datasets/gov/vssa/dcat/Distribution/:create"],
        )
        file_content = b"Sample CSV content"
        data = {
            "dataset": str(dataset.id),
            "title": "Title",
        }

        response = app.post(
            url_distribution,
            data,
            upload_files=[("file", "test.csv", file_content)],
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        distribution = DatasetDistribution.objects.filter(
            metadata__name=dataset.datasetdistribution_set.first().metadata.name,
            dataset__organization__kind=organization.kind,
            dataset__organization__name=organization.name,
        ).first()
        assert distribution
        assert response.json == {
            "@context": "",
            "_type": url_distribution.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
            "_id": str(distribution.id),
            "_revision": "",
            "_txn": "",
            "_created": distribution.created.astimezone(timezone).isoformat(),
            "_updated": distribution.modified.astimezone(timezone).isoformat(),
            "description": distribution.description,
            "file": distribution.file.label,
            "id": distribution.id,
            "issued": distribution.issued,
            "periodEnd": distribution.period_end,
            "periodStart": distribution.period_start,
            "geo_location": distribution.geo_location,
            "title": data["title"],
            "type": distribution.type,
            "url": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
            "version": None,
            "upload_to_storage": distribution.upload_to_storage,
            "data_last_updated": None,
        }

    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_distribution: str,
        domain: str,
        valid_token_disabled_agent: str,
    ):
        file_content = b"Sample CSV content"
        data = {
            "dataset": str(dataset.id),
            "title": "Title",
        }

        response = app.post(
            url_distribution,
            data,
            upload_files=[("file", "test.csv", file_content)],
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

    @pytest.mark.parametrize("invalid_scopes", [["invalid_scope"], [], [""]])
    def test_token_does_not_have_necessary_scopes(
        self,
        invalid_scopes: Iterable[str],
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_distribution: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)
        response = app.post(
            url_distribution,
            {},
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_json = response.json
        assert response_json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }

    def test_no_organization_id_inside_token_payload(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_distribution: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(
            test_jwk,
            organization=None,
            scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES,
        )
        response = app.post(
            url_distribution,
            {},
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_json = response.json
        assert response_json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }

    def test_serializer_is_invalid(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_distribution: str,
        valid_token: str,
    ):
        response = app.post(
            url_distribution,
            {"dataset": str(dataset.id)},
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert DatasetDistribution.objects.count() == 0
        assert response.json == {
            "code": "validation_error",
            "type": "ValidationError",
            "template": "Request validation failed.",
            "message": str({"title": [ErrorDetail(string="Šis laukas yra privalomas.", code="required")]}),
            "context": {"errors": {"title": ["Šis laukas yra privalomas."]}},
            "additionalProperties": None,
        }

    def test_unexpected_exception_raised(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_distribution: str,
        valid_token: str,
    ):
        file_content = b"Sample CSV content"
        data = {
            "dataset": str(dataset.id),
            "title": "Title of the Distribution",
        }

        with patch(
            "vitrina.uapi.views.views.UAPIDistributionSerializer.data",
            new_callable=PropertyMock,
            side_effect=Exception("Unexpected error"),
        ):
            response = app.post(
                url_distribution,
                data,
                upload_files=[("file", "test.csv", file_content)],
                extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
                expect_errors=True,
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert DatasetDistribution.objects.count() == 0
        response_json = response.json
        response_json.pop("context")
        assert response_json == {
            "code": "server_error",
            "type": "Exception",
            "template": "An unexpected server error occurred.",
            "message": "Unexpected error",
            "additionalProperties": None,
        }


class TestList:
    def test_success(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        distribution: DatasetDistribution,
        url_distribution: str,
        domain: str,
        valid_token: str,
    ):
        response = app.get(url_distribution, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "@context": "",
                    "_type": url_distribution.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
                    "_id": str(distribution.id),
                    "_revision": str(Version.objects.get_for_object(distribution).first().revision_id),
                    "_txn": "",
                    "_created": distribution.created.astimezone(timezone).isoformat(),
                    "_updated": distribution.modified.astimezone(timezone).isoformat(),
                    "description": distribution.description,
                    "file": distribution.file.label,
                    "id": distribution.id,
                    "issued": distribution.issued,
                    "periodEnd": distribution.period_end.isoformat(),
                    "periodStart": distribution.period_start.isoformat(),
                    "geo_location": distribution.geo_location,
                    "title": distribution.title,
                    "type": distribution.type,
                    "url": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
                    "version": None,
                    "upload_to_storage": distribution.upload_to_storage,
                    "data_last_updated": None,
                }
            ]
        }

    def test_specific_scope(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        distribution: DatasetDistribution,
        url_distribution: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(
            test_jwk,
            organization=organization,
            scopes=["uapi:/datasets/gov/vssa/dcat/Distribution/:getall"],
        )
        response = app.get(url_distribution, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json == {
            "_data": [
                {
                    "@context": "",
                    "_type": url_distribution.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
                    "_id": str(distribution.id),
                    "_revision": str(Version.objects.get_for_object(distribution).first().revision_id),
                    "_txn": "",
                    "_created": distribution.created.astimezone(timezone).isoformat(),
                    "_updated": distribution.modified.astimezone(timezone).isoformat(),
                    "description": distribution.description,
                    "file": distribution.file.label,
                    "id": distribution.id,
                    "issued": distribution.issued,
                    "periodEnd": distribution.period_end.isoformat(),
                    "periodStart": distribution.period_start.isoformat(),
                    "geo_location": distribution.geo_location,
                    "title": distribution.title,
                    "type": distribution.type,
                    "url": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
                    "version": None,
                    "upload_to_storage": distribution.upload_to_storage,
                    "data_last_updated": None,
                }
            ]
        }

    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_distribution: str,
        domain: str,
        valid_token_disabled_agent: str,
    ):
        response = app.get(
            url_distribution,
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

    @pytest.mark.parametrize("invalid_scopes", [["invalid_scope"], [], [""]])
    def test_token_does_not_have_necessary_scopes(
        self,
        invalid_scopes: Iterable[str],
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        distribution: DatasetDistribution,
        url_distribution: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(
            test_jwk,
            organization=organization,
            scopes=invalid_scopes,
        )
        response = app.get(
            url_distribution, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_json = response.json
        assert response_json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }

    def test_no_organization_id_inside_token_payload(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        distribution: DatasetDistribution,
        url_distribution: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(
            test_jwk,
            organization=None,
            scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES,
        )
        response = app.get(
            url_distribution, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_json = response.json
        assert response_json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }

    def test_call_with_query_parameters(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        distribution: DatasetDistribution,
        url_distribution: str,
        domain: str,
        valid_token: str,
    ):
        distribution_2 = DatasetDistributionFactory(
            dataset=dataset, title="Title of the Distribution 2", description="Description of the Distribution 2."
        )
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(DatasetDistribution),
            object_id=distribution_2.pk,
            name="test/dataset/TestModel/TestDistribution2",
        )

        response = app.get(
            url_distribution,
            params={"dataset._id": dataset.id, "name": distribution.metadata.first().name},
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )  # w/ Query parameters, we should only get one.

        assert response.status_code == status.HTTP_200_OK
        assert DatasetDistribution.objects.count() == 2
        assert response.json == {
            "_data": [
                {
                    "@context": "",
                    "_type": url_distribution.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
                    "_id": str(distribution.id),
                    "_revision": str(Version.objects.get_for_object(distribution).first().revision_id),
                    "_txn": "",
                    "_created": distribution.created.astimezone(timezone).isoformat(),
                    "_updated": distribution.modified.astimezone(timezone).isoformat(),
                    "description": distribution.description,
                    "file": distribution.file.label,
                    "id": distribution.id,
                    "issued": distribution.issued,
                    "periodEnd": distribution.period_end.isoformat(),
                    "periodStart": distribution.period_start.isoformat(),
                    "geo_location": distribution.geo_location,
                    "title": distribution.title,
                    "type": distribution.type,
                    "url": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
                    "version": None,
                    "upload_to_storage": distribution.upload_to_storage,
                    "data_last_updated": None,
                }
            ]
        }

    def test_call_with_query_parameters_dataset_does_not_exist(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_distribution: str,
        valid_token: str,
    ):
        response = app.get(
            url_distribution,
            params={"dataset._id": 1, "name": "not_existing_distribution"},
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json == {
            "code": "distributions_not_found",
            "type": "DistributionsNotFound",
            "template": "The requested Distributions could not be found.",
            "message": "No distributions matched the provided query.",
            "additionalProperties": None,
        }

    def test_call_with_query_parameters_no_given_distribution(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_distribution: str,
        valid_token: str,
    ):
        response = app.get(
            url_distribution,
            params={"dataset._id": dataset.id, "name": "not_existing_distribution"},
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json == {
            "code": "distributions_not_found",
            "type": "DistributionsNotFound",
            "template": "The requested Distributions could not be found.",
            "message": "No distributions matched the provided query.",
            "additionalProperties": None,
        }

    def test_distributions_dataset_is_deleted(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        distribution: DatasetDistribution,
        url_distribution: str,
        valid_token: str,
    ):
        dataset.deleted = True
        dataset.save(update_fields=["deleted"])

        response = app.get(
            url_distribution,
            params={
                "dataset._id": dataset.id,
                "name": distribution.metadata.first().name,
            },
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert DatasetDistribution.objects.filter(dataset__deleted=True).count() == 1
        assert response.json == {
            "code": "distributions_not_found",
            "type": "DistributionsNotFound",
            "template": "The requested Distributions could not be found.",
            "message": "No distributions matched the provided query.",
            "additionalProperties": None,
        }

    def test_distributions_do_not_exist(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        distribution: DatasetDistribution,
        url_distribution: str,
        valid_token: str,
    ):
        distribution.deleted = True
        distribution.save(update_fields=["deleted"])

        response = app.get(
            url_distribution,
            params={
                "dataset._id": dataset.id,
                "name": distribution.metadata.first().name,
            },
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert DatasetDistribution.objects.filter(deleted=True).count() == 1
        assert response.json == {
            "code": "distributions_not_found",
            "type": "DistributionsNotFound",
            "template": "The requested Distributions could not be found.",
            "message": "No distributions matched the provided query.",
            "additionalProperties": None,
        }

    def test_unexpected_exception_raised(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        distribution: DatasetDistribution,
        url_distribution: str,
        valid_token: str,
    ):
        with patch(
            "vitrina.uapi.views.views.BaseObjectListSerializer.data",
            new_callable=PropertyMock,
            side_effect=Exception("Unexpected error"),
        ):
            response = app.get(
                url_distribution,
                params={
                    "dataset._id": dataset.id,
                    "name": distribution.metadata.first().name,
                },
                extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
                expect_errors=True,
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_json = response.json
        response_json.pop("context")
        assert response_json == {
            "code": "server_error",
            "type": "Exception",
            "template": "An unexpected server error occurred.",
            "message": "Unexpected error",
            "additionalProperties": None,
        }

from typing import Iterable
from unittest.mock import patch, PropertyMock
from urllib.parse import quote

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
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.models import Organization
from vitrina.structure.factories import MetadataFactory
from vitrina.structure.models import Metadata


pytestmark = pytest.mark.django_db
timezone = pytz.timezone(settings.TIME_ZONE)


def test_create(
    app: DjangoTestApp,
    organization: Organization,
    url_dataset: str,
    domain: str,
    valid_token: str,
):
    data = {
        "name": "/datasets/gov/vssa/isris/dcat/uapi/Model",
        "title": "DataSet 1",
        "description": "DataSet 1 description",
    }
    response = app.post(
        url_dataset,
        data,
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert Metadata.objects.count() == 1
    dataset = Dataset.objects.filter(
        metadata__name=data["name"],
        access_rights=Dataset.NON_PUBLIC,
        organization=organization,
    ).first()
    assert dataset
    assert response.json == {
        "@context": "",
        "_type": url_dataset.rstrip("/"),
        "_id": str(dataset.id),
        "_revision": str(Version.objects.get_for_object(dataset).first().revision_id),
        "_txn": "",
        "_created": dataset.created.astimezone(timezone).isoformat(),
        "_updated": dataset.modified.astimezone(timezone).isoformat(),
        "created": dataset.created.astimezone(timezone).isoformat(),
        "modified": dataset.modified.astimezone(timezone).isoformat(),
        "id": str(dataset.id),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": data["title"],
        "description": data["description"],
        "temporalCoverage": dataset.temporal_coverage,
        "language": [],
        "publisher": dataset.publisher,
        "spatial": dataset.spatial_coverage,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
        "theme": [],
        "organization_id": organization.id,
        "organization_title": organization.title,
    }


def test_create_specific_scope(
    app: DjangoTestApp,
    organization: Organization,
    url_dataset: str,
    domain: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(
        test_jwk,
        organization=organization,
        scopes=["spinta_datasets_gov_vssa_dataset_insert"],
    )
    data = {
        "name": "/datasets/gov/vssa/isris/dcat/uapi/Model",
        "title": "DataSet 1",
        "description": "DataSet 1 description",
    }
    response = app.post(
        url_dataset,
        data,
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert Metadata.objects.count() == 1
    dataset = Dataset.objects.filter(
        metadata__name=data["name"],
        access_rights=Dataset.NON_PUBLIC,
        organization=organization,
    ).first()
    assert dataset
    assert response.json == {
        "@context": "",
        "_type": url_dataset.rstrip("/"),
        "_id": str(dataset.id),
        "_revision": str(Version.objects.get_for_object(dataset).first().revision_id),
        "_txn": "",
        "_created": dataset.created.astimezone(timezone).isoformat(),
        "_updated": dataset.modified.astimezone(timezone).isoformat(),
        "created": dataset.created.astimezone(timezone).isoformat(),
        "modified": dataset.modified.astimezone(timezone).isoformat(),
        "id": str(dataset.id),
        "internalId": dataset.internal_id,
        "origin": dataset.origin,
        "title": data["title"],
        "description": data["description"],
        "temporalCoverage": dataset.temporal_coverage,
        "language": [],
        "publisher": dataset.publisher,
        "spatial": dataset.spatial_coverage,
        "keyword": dataset.tag_name_array,
        "landingPage": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
        "theme": [],
        "organization_id": organization.id,
        "organization_title": organization.title,
    }


@pytest.mark.parametrize("invalid_scopes", [["invalid_scope"], [], [""]])
def test_create_token_does_not_have_necessary_scopes(
    invalid_scopes: Iterable[str],
    app: DjangoTestApp,
    organization: Organization,
    url_dataset: str,
    domain: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)
    response = app.post(
        url_dataset,
        {},  # Empty data, since it should not get to the part where it is used.
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_json = response.json
    response_json.pop("context")  # Full error traceback is removed.
    assert response_json == {
        "code": "server_error",
        "type": "PermissionDenied",
        "template": "An unexpected server error occurred.",
        "message": "You do not have permission to perform this action.",
        "additionalProperties": None,
    }


def test_create_no_organization_id_inside_token_payload(
    app: DjangoTestApp,
    organization: Organization,
    url_dataset: str,
    domain: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(test_jwk, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)
    response = app.post(
        url_dataset,
        {},  # Empty data, since it should not get to the part where it is used.
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_json = response.json
    response_json.pop("context")  # Full error traceback is removed.
    assert response_json == {
        "code": "server_error",
        "type": "PermissionDenied",
        "template": "An unexpected server error occurred.",
        "message": "You do not have permission to perform this action.",
        "additionalProperties": None,
    }


def test_create_serialization_validation_error(
    app: DjangoTestApp,
    organization: Organization,
    url_dataset: str,
    valid_token: str,
):
    response = app.post(
        url_dataset,
        {},
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Dataset.objects.filter(organization=organization).count() == 0
    assert Metadata.objects.count() == 0
    assert response.json == {
        "code": "validation_error",
        "type": "ValidationError",
        "template": "Request validation failed.",
        "message": str(
            {
                "title": [ErrorDetail(string="Šis laukas yra privalomas.", code="required")],
                "description": [ErrorDetail(string="Šis laukas yra privalomas.", code="required")]
            }
        ),
        "context": {
            "errors": {
                "title": ["Šis laukas yra privalomas."],
                "description": ["Šis laukas yra privalomas."]

            }
        },
        "additionalProperties": None
    }


def test_create_unexpected_exception_raised_and_rollback_executed(
    app: DjangoTestApp,
    organization: Organization,
    url_dataset: str,
    valid_token: str,
):
    """Check that unexpected errors still return a standard UAPI formatted response."""
    data = {
        "name": "/datasets/gov/vssa/isris/dcat/uapi/Model",
        "title": "Dataset 1",
        "description": "Dataset 1 description",
    }

    # Mocking a property at the end of the file, to also check that rollback happened, and no new objects were created.
    with patch(
            "vitrina.uapi.views.views.UAPIDatasetSerializer.data",
            new_callable=PropertyMock,
            side_effect=Exception("Unexpected error")
    ):
        response = app.post(
            url_dataset,
            data,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert Dataset.objects.filter(organization=organization).count() == 0
    assert Metadata.objects.count() == 0
    response_json = response.json
    response_json.pop("context")  # Context stores the full traceback, we skip this check in tests.
    assert response_json == {
        "code": "server_error",
        "type": "Exception",
        "template": "An unexpected server error occurred.",
        "message": "Unexpected error",
        "additionalProperties": None
    }


def test_list(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    url_dataset: str,
    domain: str,
    valid_token: str,
):
    response = app.get(url_dataset, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"})

    assert response.status_code == status.HTTP_200_OK
    assert Dataset.objects.filter(organization=organization).count() == 1
    assert response.json == {
        "_type": url_dataset.rstrip("/"),
        "_data": [
            {
                "@context": "",
                "_type": url_dataset.rstrip("/"),
                "_id": str(dataset.id),
                "_revision": "",
                "_txn": "",
                "_created": dataset.created.astimezone(timezone).isoformat(),
                "_updated": dataset.modified.astimezone(timezone).isoformat(),
                "created": dataset.created.astimezone(timezone).isoformat(),
                "internalId": dataset.internal_id,
                "origin": dataset.origin,
                "title": dataset.title,
                "description": dataset.description,
                "modified": dataset.modified.astimezone(timezone).isoformat(),
                "temporalCoverage": dataset.temporal_coverage,
                "language": [],
                "publisher": dataset.publisher,
                "spatial": dataset.spatial_coverage,
                "periodicity": dataset.frequency.title,
                "keyword": dataset.tag_name_array,
                "landingPage": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
                "theme": [],
                "organization_id": organization.id,
                "organization_title": organization.title,
                "id": str(dataset.id),
            }
        ]
    }


def test_list_specific_scope(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    url_dataset: str,
    domain: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(
        test_jwk,
        organization=organization,
        scopes=["spinta_datasets_gov_vssa_dataset_getall"],
    )

    response = app.get(url_dataset, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"})

    assert response.status_code == status.HTTP_200_OK
    assert Dataset.objects.filter(organization=organization).count() == 1
    assert response.json == {
        "_type": url_dataset.rstrip("/"),
        "_data": [
            {
                "@context": "",
                "_type": url_dataset.rstrip("/"),
                "_id": str(dataset.id),
                "_revision": "",
                "_txn": "",
                "_created": dataset.created.astimezone(timezone).isoformat(),
                "_updated": dataset.modified.astimezone(timezone).isoformat(),
                "created": dataset.created.astimezone(timezone).isoformat(),
                "internalId": dataset.internal_id,
                "origin": dataset.origin,
                "title": dataset.title,
                "description": dataset.description,
                "modified": dataset.modified.astimezone(timezone).isoformat(),
                "temporalCoverage": dataset.temporal_coverage,
                "language": [],
                "publisher": dataset.publisher,
                "spatial": dataset.spatial_coverage,
                "periodicity": dataset.frequency.title,
                "keyword": dataset.tag_name_array,
                "landingPage": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
                "theme": [],
                "organization_id": organization.id,
                "organization_title": organization.title,
                "id": str(dataset.id),
            }
        ]
    }


@pytest.mark.parametrize("invalid_scopes", [["invalid_scope"], [], [""]])
def test_list_token_does_not_have_necessary_scopes(
    invalid_scopes: Iterable[str],
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    url_dataset: str,
    domain: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)

    response = app.get(url_dataset, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_json = response.json
    response_json.pop("context")  # Full error traceback is removed.
    assert response_json == {
        "code": "server_error",
        "type": "PermissionDenied",
        "template": "An unexpected server error occurred.",
        "message": "You do not have permission to perform this action.",
        "additionalProperties": None,
    }


def test_list_no_organization_id_inside_token_payload(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    url_dataset: str,
    domain: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(test_jwk, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)

    response = app.get(url_dataset, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_json = response.json
    response_json.pop("context")  # Full error traceback is removed.
    assert response_json == {
        "code": "server_error",
        "type": "PermissionDenied",
        "template": "An unexpected server error occurred.",
        "message": "You do not have permission to perform this action.",
        "additionalProperties": None,
    }


def test_list_with_query_parameters(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    url_dataset: str,
    domain: str,
    valid_token: str,
):
    dataset_2 = DatasetFactory(
        organization=organization,
        title="Title of the Dataset 2",
        description="Description of the Dataset 2."
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=dataset_2.pk,
        dataset=dataset_2,
        name="test/dataset/TestModel2",
    )

    response = app.get(
        url_dataset,
        params={"name": dataset.metadata.first().name},
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
    )  # w/ Query parameters, we should only get one.

    assert response.status_code == status.HTTP_200_OK
    assert Dataset.objects.filter(organization=organization).count() == 2
    assert response.json == {
        "_type": url_dataset.rstrip("/"),
        "_data": [
            {
                "@context": "",
                "_type": url_dataset.rstrip("/"),
                "_id": str(dataset.id),
                "_revision": "",
                "_txn": "",
                "_created": dataset.created.astimezone(timezone).isoformat(),
                "_updated": dataset.modified.astimezone(timezone).isoformat(),
                "created": dataset.created.astimezone(timezone).isoformat(),
                "internalId": dataset.internal_id,
                "origin": dataset.origin,
                "title": dataset.title,
                "description": dataset.description,
                "modified": dataset.modified.astimezone(timezone).isoformat(),
                "temporalCoverage": dataset.temporal_coverage,
                "language": [],
                "publisher": dataset.publisher,
                "spatial": dataset.spatial_coverage,
                "periodicity": dataset.frequency.title,
                "keyword": dataset.tag_name_array,
                "landingPage": f"http://{domain}{reverse('dataset-detail', args=[dataset.id])}",
                "theme": [],
                "organization_id": organization.id,
                "organization_title": organization.title,
                "id": str(dataset.id),
            }
        ]
    }


def test_list_no_datasets_exist(
    app: DjangoTestApp,
    organization: Organization,
    url_dataset: str,
    valid_token: str,
):
    response = app.get(url_dataset, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"}, expect_errors=True)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json == {
        "code": "dataset_not_found",
        "type": "DatasetNotFound",
        "template": "The requested Dataset could not be found.",
        "message": (
            f"No dataset matched the provided query — http://testserver/uapi/datasets/org/vssa/isris/dcat/Dataset/."
        ),
        "additionalProperties": None
    }


def test_list_only_archived_datasets(
    app: DjangoTestApp,
    organization: Organization,
    url_dataset: str,
    valid_token: str,
):
    dataset = DatasetFactory(
        organization=organization,
        title="Title of the Dataset",
        description="Description of the Dataset.",
        deleted=True,
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )

    response = app.get(url_dataset, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"}, expect_errors=True)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Dataset.objects.filter(organization=organization).count() == 1
    assert response.json == {
        "code": "dataset_not_found",
        "type": "DatasetNotFound",
        "template": "The requested Dataset could not be found.",
        "message": (
            f"No dataset matched the provided query — http://testserver/uapi/datasets/org/vssa/isris/dcat/Dataset/."
        ),
        "additionalProperties": None
    }


def test_list_with_query_parameters_archived_dataset(
    app: DjangoTestApp,
    organization: Organization,
    url_dataset: str,
    valid_token: str,
):
    dataset = DatasetFactory(
        organization=organization,
        title="Title of the Dataset",
        description="Description of the Dataset.",
        deleted=True,
    )
    metadata = MetadataFactory(
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )

    response = app.get(
        url_dataset,
        params={"name": dataset.metadata.first().name},
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        expect_errors=True
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Dataset.objects.filter(organization=organization).count() == 1
    assert response.json == {
        "code": "dataset_not_found",
        "type": "DatasetNotFound",
        "template": "The requested Dataset could not be found.",
        "message": (
            f"No dataset matched the provided query — "
            f"http://testserver/uapi/datasets/org/vssa/isris/dcat/Dataset/?name={quote(metadata.name, safe='')}."
        ),
        "additionalProperties": None
    }


def test_list_no_datasets_for_the_organization_passed_in_path_parameters(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    url_dataset: str,
    valid_token: str,
):
    response = app.get(
        url_dataset,
        params={"name": "dataset/that/does/not/exist"},
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Dataset.objects.filter(metadata__name="dataset/that/does/not/exist").count() == 0
    assert response.json == {
        "code": "dataset_not_found",
        "type": "DatasetNotFound",
        "template": "The requested Dataset could not be found.",
        "message": (
            f"No dataset matched the provided query — "
            f"http://testserver/uapi/datasets/"
            f"org/vssa/isris/dcat/Dataset/?name={quote('dataset/that/does/not/exist', safe='')}."
        ),
        "additionalProperties": None
    }


def test_action_upload_dataset_structure(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    dsa: str,
    url_dataset_structure: str,
    valid_token: str,
):
    response = app.post(
        url_dataset_structure,
        dsa,
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        content_type="text/csv",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.body
    # Dataset is saved and stored in DatasetStructure.
    assert dataset.datasetstructure_set.count() == 1
    file = dataset.datasetstructure_set.first().file
    assert file is not None
    assert file.label == f"dataset_{dataset.id}_structure.csv"


def test_action_upload_dataset_structure_specific_scope(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    dsa: str,
    url_dataset_structure: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(
        test_jwk,
        organization=organization,
        scopes=["spinta_datasets_gov_vssa_dataset_dsa_insert"],
    )
    response = app.post(
        url_dataset_structure,
        dsa,
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        content_type="text/csv",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.body
    # Dataset is saved and stored in DatasetStructure.
    assert dataset.datasetstructure_set.count() == 1
    file = dataset.datasetstructure_set.first().file
    assert file is not None
    assert file.label == f"dataset_{dataset.id}_structure.csv"


@pytest.mark.parametrize("invalid_scopes", [["invalid_scope"], [], [""]])
def test_action_upload_dataset_structure_token_does_not_have_necessary_scopes(
    invalid_scopes: Iterable[str],
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    dsa: str,
    url_dataset_structure: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)

    response = app.post(
        url_dataset_structure,
        dsa,
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        content_type="text/csv",
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_json = response.json
    response_json.pop("context")  # Full error traceback is removed.
    assert response_json == {
        "code": "server_error",
        "type": "PermissionDenied",
        "template": "An unexpected server error occurred.",
        "message": "You do not have permission to perform this action.",
        "additionalProperties": None,
    }


def test_action_upload_dataset_structure_no_organization_id_inside_token_payload(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    dsa: str,
    url_dataset_structure: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(test_jwk, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)

    response = app.post(
        url_dataset_structure,
        dsa,
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        content_type="text/csv",
        expect_errors=True
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_json = response.json
    response_json.pop("context")  # Full error traceback is removed.
    assert response_json == {
        "code": "server_error",
        "type": "PermissionDenied",
        "template": "An unexpected server error occurred.",
        "message": "You do not have permission to perform this action.",
        "additionalProperties": None,
    }


def test_action_upload_dataset_structure_no_object(
    app: DjangoTestApp,
    organization: Organization,
    dsa: str,
    valid_token: str,
):
    url = reverse("uapi-dataset-structure", kwargs={"dataset_id": 1})

    response = app.post(
        url,
        dsa,
        content_type="text/csv",
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Dataset.objects.filter(organization=organization).count() == 0
    assert DatasetStructure.objects.count() == 0
    assert response.json == {
        "code": "not_found",
        "type": "NotFound",
        "template": "The requested resource was not found.",
        "message": "No Dataset matches the given query.",
        "additionalProperties": None,
    }


def test_action_upload_dataset_structure_empty_csv(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    url_dataset_structure: str,
    valid_token: str,
):
    response = app.post(
        url_dataset_structure,
        "",
        content_type="text/csv",
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json == {
        "code": "empty_csv",
        "type": "EmptyCSVContent",
        "template": "The uploaded file is empty or contains only whitespace.",
        "message": "CSV content is missing or invalid.",
        "additionalProperties": None,
    }


def test_action_upload_dataset_structure_file_only_contains_special_characters(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    url_dataset_structure: str,
    valid_token: str,
):
    response = app.post(
        url_dataset_structure,
        "\r\n\t ",
        content_type="text/csv",
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json == {
        "code": "empty_csv",
        "type": "EmptyCSVContent",
        "template": "The uploaded file is empty or contains only whitespace.",
        "message": "CSV content is missing or invalid.",
        "additionalProperties": None,
    }

def test_action_upload_dataset_structure_transaction_rollback_on_failure(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    dsa: str,
    url_dataset_structure: str,
    valid_token: str,
):

    with patch("vitrina.uapi.views.views.Dataset.save", side_effect=Exception("Unexpected error")):
        response = app.post(
            url_dataset_structure,
            dsa,
            content_type="text/csv",
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert DatasetStructure.objects.count() == 0
    response_json = response.json
    response_json.pop("context")  # Context stores the full traceback, we skip this check in tests.
    assert response_json == {
        "code": "server_error",
        "type": "Exception",
        "template": "An unexpected server error occurred.",
        "message": "Unexpected error",
        "additionalProperties": None,
    }


def test_action_update_dataset_structure(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    dsa: str,
    url_dataset_structure: str,
    valid_token: str,
):
    """This test currently proves that the endpoint returns 501 NOT IMPLEMENTED."""
    response = app.put(
        url_dataset_structure,
        dsa,
        content_type="text/csv",
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


def test_action_update_dataset_structure_specific_scope(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    dsa: str,
    url_dataset_structure: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(
        test_jwk,
        organization=organization,
        scopes=["spinta_datasets_gov_vssa_dataset_dsa_update"],
    )

    response = app.put(
        url_dataset_structure,
        dsa,
        content_type="text/csv",
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


@pytest.mark.parametrize("invalid_scopes", [["invalid_scope"], [], [""]])
def test_action_update_dataset_structure_token_does_not_have_necessary_scopes(
    invalid_scopes: Iterable[str],
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    dsa: str,
    url_dataset_structure: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)

    response = app.put(
        url_dataset_structure,
        dsa,
        content_type="text/csv",
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_json = response.json
    response_json.pop("context")  # Full error traceback is removed.
    assert response_json == {
        "code": "server_error",
        "type": "PermissionDenied",
        "template": "An unexpected server error occurred.",
        "message": "You do not have permission to perform this action.",
        "additionalProperties": None,
    }


def test_action_update_dataset_structure_no_organization_id_inside_token_payload(
    app: DjangoTestApp,
    organization: Organization,
    dataset: Dataset,
    dsa: str,
    url_dataset_structure: str,
    test_jwk: RSAKey,
):
    token = _generate_test_token(test_jwk, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)

    response = app.put(
        url_dataset_structure,
        dsa,
        content_type="text/csv",
        extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        expect_errors=True,
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_json = response.json
    response_json.pop("context")  # Full error traceback is removed.
    assert response_json == {
        "code": "server_error",
        "type": "PermissionDenied",
        "template": "An unexpected server error occurred.",
        "message": "You do not have permission to perform this action.",
        "additionalProperties": None,
    }

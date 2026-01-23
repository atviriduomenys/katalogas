from typing import Iterable, Any
from unittest.mock import patch, PropertyMock
from urllib.parse import quote

import pytest
import pytz
from authlib.jose import RSAKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from factory.django import FileField
from rest_framework import status
from rest_framework.exceptions import ErrorDetail

from tests.conftest import _normalize_csv
from tests.uapi.conftest import _generate_test_token, _build_reverse_uapi_url
from vitrina import settings
from vitrina.cms.factories import FilerFileFactory
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset, DatasetStructure, DCATResourceSubclass
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.structure.factories import MetadataFactory
from vitrina.structure.models import Metadata
from vitrina.structure.services import create_structure_objects
from vitrina.uapi.serializers.uapi_serializers import TYPE_PREFIX_TO_REMOVE


pytestmark = pytest.mark.django_db
timezone = pytz.timezone(settings.TIME_ZONE)


class TestCreate:
    def test_success(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_dataset: str,
        domain: str,
        valid_token: str,
    ):
        dataset_parent = DatasetFactory()
        data = {
            "name": "/datasets/gov/vssa/ror/dcat/uapi/Model",
            "title": "DataSet 1",
            "description": "DataSet 1 description",
            "service": True,
            "subclass": DCATResourceSubclass.SERVICE,
            "parent_id": dataset_parent.pk,
        }

        response = app.post(
            url_dataset,
            data,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED

        dataset = Dataset.objects.filter(
            metadata__name=data["name"],
            access_rights=Dataset.NON_PUBLIC,
            organization=organization,
        ).first()
        assert Metadata.objects.filter(dataset=dataset).count() == 1
        assert dataset
        assert dataset.path is not None
        assert dataset.is_child_of(dataset_parent) is True  # Parent is set.

        assert response.json == {
            "@context": "",
            "_type": url_dataset.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
            "_id": str(dataset.id),
            "_revision": "",
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
            "service": True,
            "series": False,
            "subclass": DCATResourceSubclass.SERVICE,
        }


    @pytest.mark.parametrize(
        "subclass, subclass_additional_data, is_service, is_series",
        [
            (
                DCATResourceSubclass.DATASET,
                {"subclass": DCATResourceSubclass.DATASET},
                False,
                False,
            ),
            (
                DCATResourceSubclass.INFORMATION_SYSTEM,
                {"subclass": DCATResourceSubclass.INFORMATION_SYSTEM},
                False,
                False,
            ),
            (
                DCATResourceSubclass.CATALOG,
                {"subclass": DCATResourceSubclass.CATALOG},
                False,
                False,
            ),
            (
                DCATResourceSubclass.SERIES,
                {
                    "subclass": DCATResourceSubclass.SERIES,
                    "series": True,
                },
                False,
                True,
            ),
            (
                DCATResourceSubclass.SERVICE,
                {
                    "subclass": DCATResourceSubclass.SERVICE,
                    "service": True,
                },
                True,
                False,
            ),
            # Defaults to Dataset when value is not given.
            (
                DCATResourceSubclass.DATASET,
                {},
                False,
                False,
            ),
        ],
    )
    def test_specific_resource(
        self,
        subclass: str,
        subclass_additional_data: dict[str, Any],
        is_service: bool,
        is_series: bool,
        app: DjangoTestApp,
        organization: Organization,
        url_dataset: str,
        domain: str,
        valid_token: str,
        create_dcat_resource_subclasses: None,
    ):
        """Test that a specific resource is created on API call.

        Following DCAT, the Dataset model serves 5 resources: Dataset, Data Service, Catalog, IS & Data Series.
        We need this API to be able to create any one of these resources.
        """
        data = {
            "name": "/datasets/gov/vssa/ror/dcat/uapi/Model",
            "title": "Example",
            "description": "Example description",
            **subclass_additional_data,
        }
        response = app.post(
            url_dataset,
            data,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json["subclass"] == subclass
        assert response.json["series"] == is_series
        assert response.json["service"] == is_service


    def test_specific_scope(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_dataset: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(
            test_jwk,
            organization=organization,
            scopes=["uapi:/datasets/gov/vssa/dcat/Dataset/:create"],
        )
        data = {
            "name": "/datasets/gov/vssa/ror/dcat/uapi/Model",
            "title": "DataSet 1",
            "description": "DataSet 1 description",
        }
        response = app.post(
            url_dataset,
            data,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED

        dataset = Dataset.objects.filter(
            metadata__name=data["name"],
            access_rights=Dataset.NON_PUBLIC,
            organization=organization,
        ).first()
        assert Metadata.objects.filter(dataset=dataset).count() == 1
        assert dataset
        assert response.json == {
            "@context": "",
            "_type": url_dataset.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
            "_id": str(dataset.id),
            "_revision": "",
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
            "service": False,
            "series": False,
            "subclass": DCATResourceSubclass.DATASET,
        }


    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_dataset: str,
        domain: str,
        valid_token_disabled_agent: str,
    ):
        dataset_parent = DatasetFactory()
        data = {
            "name": "/datasets/gov/vssa/ror/dcat/uapi/Model",
            "title": "DataSet 1",
            "description": "DataSet 1 description",
            "service": True,
            "subclass": DCATResourceSubclass.SERVICE,
            "parent_id": dataset_parent.pk,
        }
        response = app.post(
            url_dataset,
            data,
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

        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_json = response.json
        assert response_json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }


    def test_serialization_validation_error(
        self,
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
        assert Metadata.objects.filter(dataset=organization.dataset_set.first()).count() == 0
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


    def test_unexpected_exception_raised_and_rollback_executed(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_dataset: str,
        valid_token: str,
    ):
        """Check that unexpected errors still return a standard UAPI formatted response."""
        data = {
            "name": "/datasets/gov/vssa/ror/dcat/uapi/Model",
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
        assert Metadata.objects.filter(dataset=organization.dataset_set.first()).count() == 0
        response_json = response.json
        response_json.pop("context")  # Context stores the full traceback, we skip this check in tests.
        assert response_json == {
            "code": "server_error",
            "type": "Exception",
            "template": "An unexpected server error occurred.",
            "message": "Unexpected error",
            "additionalProperties": None
        }


class TestList:
    def test_success(
        self,
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
            "_data": [
                {
                    "@context": "",
                    "_type": url_dataset.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
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
                    "service": False,
                    "series": False,
                    "subclass": DCATResourceSubclass.DATASET,
                }
            ]
        }


    def test_specific_scope(
        self,
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
            scopes=["uapi:/datasets/gov/vssa/dcat/Dataset/:getall"],
        )

        response = app.get(url_dataset, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"})

        assert response.status_code == status.HTTP_200_OK
        assert Dataset.objects.filter(organization=organization).count() == 1
        assert response.json == {
            "_data": [
                {
                    "@context": "",
                    "_type": url_dataset.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
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
                    "service": False,
                    "series": False,
                    "subclass": DCATResourceSubclass.DATASET,
                }
            ]
        }


    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_dataset: str,
        domain: str,
        valid_token_disabled_agent: str,
    ):
        response = app.get(
            url_dataset,
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
        url_dataset: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(test_jwk, organization=organization, scopes=invalid_scopes)

        response = app.get(url_dataset, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True)

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
        url_dataset: str,
        domain: str,
        test_jwk: RSAKey,
    ):
        token = _generate_test_token(test_jwk, scopes=settings.OAUTH_AGENT_DEFAULT_SCOPES)

        response = app.get(url_dataset, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"}, expect_errors=True)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_json = response.json
        assert response_json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }


    def test_call_with_name_query_parameter(
        self,
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
            "_data": [
                {
                    "@context": "",
                    "_type": url_dataset.rstrip("/").removeprefix(TYPE_PREFIX_TO_REMOVE),
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
                    "service": False,
                    "series": False,
                    "subclass": DCATResourceSubclass.DATASET,
                }
            ]
        }


    def test_call_with_parent_id_query_parameter(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        url_dataset: str,
        domain: str,
        valid_token: str,
    ):
        dataset_2 = DatasetFactory(organization=organization)
        dataset_3 = DatasetFactory(organization=organization)
        dataset_orphan = DatasetFactory(organization=organization)
        dataset_other_organization = DatasetFactory(organization=OrganizationFactory())

        # Attach children to the Data Service (saved instances).
        dataset_2.move(dataset, pos='sorted-child')
        dataset_3.move(dataset, pos='sorted-child')

        response = app.get(
            url_dataset,
            params={"parent_id": dataset.pk},
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        child_dataset_ids = {dataset["_id"] for dataset in response.json["_data"]}
        assert str(dataset_2.pk) in child_dataset_ids
        assert str(dataset_3.pk) in child_dataset_ids
        assert str(dataset_orphan.pk) not in child_dataset_ids
        assert str(dataset_other_organization.pk) not in child_dataset_ids


    def test_no_datasets_exist(
        self,
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
                f"No dataset matched the provided query — http://testserver/uapi/datasets/gov/vssa/ror/dcat/Dataset/."
            ),
            "additionalProperties": None
        }


    def test_no_unarchived_datasets_exist(
        self,
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
                f"No dataset matched the provided query — http://testserver/uapi/datasets/gov/vssa/ror/dcat/Dataset/."
            ),
            "additionalProperties": None
        }


    def test_list_with_query_parameters_archived_dataset(
        self,
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
            metadata="test/dataset/TestModel",
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
                f"http://testserver/uapi/datasets/gov/vssa/ror/dcat/Dataset/?name={quote(dataset.metadata.first().name, safe='')}."
            ),
            "additionalProperties": None
        }


    def test_no_datasets_for_the_organization_passed_in_path_parameters(
        self,
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
                f"gov/vssa/ror/dcat/Dataset/?name={quote('dataset/that/does/not/exist', safe='')}."
            ),
            "additionalProperties": None
        }


class TestActionUploadDatasetStructure:
    def test_success(
        self,
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


    def test_dataset_structure_specific_scope(
        self,
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
            scopes=["uapi:/datasets/gov/vssa/dcat/Dsa/:create"],
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


    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        dsa: str,
        url_dataset_structure: str,
        test_jwk: RSAKey,
        valid_token_disabled_agent: str,
    ):
        response = app.post(
            url_dataset_structure,
            dsa,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token_disabled_agent}"},
            content_type="text/csv",
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

        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_json = response.json
        assert response_json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }


    def test_no_object(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dsa: str,
        valid_token: str,
    ):
        url = reverse("uapi-dataset-structure", kwargs={"pk": 1})

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


    def test_empty_csv(
        self,
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


    def test_file_only_contains_special_characters(
        self,
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

    def test_transaction_rollback_on_failure(
        self,
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


class TestActionGetDatasetStructure:
    def test_success(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        dsa: str,
        url_dataset_structure: str,
        valid_token: str,
    ):
        structure = DatasetStructureFactory(
            dataset=dataset,
            file=FilerFileFactory(
                file=FileField(filename=f"dataset_{dataset.id}_structure.csv", data=dsa)
            )
        )
        dataset.current_structure = structure
        dataset.save()
        create_structure_objects(structure, structure.dataset.metadata.first().metadata_version)

        response = app.get(
            url_dataset_structure,
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["Content-Type"] == "text/csv"

        metadata_to_id_map = dict(Metadata.objects.all().values_list("name", "uuid"))
        expected_csv = f"""id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description
{metadata_to_id_map["example70"]},example70,,,,,,,,,,,,,,,,,,Title of the Dataset,Description of the Dataset.
{metadata_to_id_map["users"]},,users,,,,dask/json,,/path,,,,,,,,,,,users,
{metadata_to_id_map["example70/User"]},,,,User,,,id,users,,,,,4,completed,package,open,,,Pavadinimas,
{metadata_to_id_map["id"]},,,,,id,integer,,id,,,,,,develop,,,,,,
{metadata_to_id_map["full_name"]},,,,,full_name,string,,name,,,,,,develop,,,,,,
{metadata_to_id_map["email_address"]},,,,,email_address,string,,email,,,,,,develop,,,,,,
{metadata_to_id_map["active"]},,,,,active,boolean,,isActive,,,,,,develop,,,,,,
"""
        actual_rows = _normalize_csv(response.content.decode("utf-8"))
        expected_rows = _normalize_csv(expected_csv)
        assert actual_rows == expected_rows


    def test_no_dataset(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_dataset_structure: str,
        valid_token: str
    ):
        response = app.get(
            _build_reverse_uapi_url(
                "uapi-dataset-structure",
                pk=1_000_000
            ),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json == {
            "code": "not_found",
            "type": "NotFound",
            "template": "The requested resource was not found.",
            "message": "No Dataset matches the given query.",
            "additionalProperties": None,
        }


    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        dsa: str,
        url_dataset_structure: str,
        valid_token_disabled_agent: str,
    ):
        structure = DatasetStructureFactory(
            dataset=dataset,
            file=FilerFileFactory(
                file=FileField(filename=f"dataset_{dataset.id}_structure.csv", data=dsa)
            )
        )
        dataset.current_structure = structure
        dataset.save()
        create_structure_objects(structure)

        response = app.get(
            url_dataset_structure,
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


    def test_invalid_token(
        self,
        app: DjangoTestApp,
        organization: Organization,
        url_dataset_structure: str,
        valid_token: str
    ):
        token_parts = valid_token.split(".")
        invalid_token = f"{token_parts[0]}.{token_parts[1]}"
        response = app.get(
            _build_reverse_uapi_url(
                "uapi-dataset-structure",
                pk=1_000_000
            ),
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {invalid_token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json == {
            "additionalProperties": None,
            "code": "authentication_failed",
            "message": "Invalid input segments length",
            "template": "Invalid input segments length",
            "type": "system",
        }


    def test_no_dataset_structure(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        dsa: str,
        url_dataset_structure: str,
        valid_token: str,
    ):
        response = app.get(
            url_dataset_structure, extra_environ={"HTTP_AUTHORIZATION": f"Bearer {valid_token}"}, expect_errors=True,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json == {"detail": "Dataset structure not found."}


class TestActionUpdateDatasetStructure:
    def test_success(
        self,
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


    def test_specific_scope(
        self,
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
            scopes=["uapi:/datasets/gov/vssa/dcat/Dsa/:patch"],
        )

        response = app.put(
            url_dataset_structure,
            dsa,
            content_type="text/csv",
            extra_environ={"HTTP_AUTHORIZATION": f"Bearer {token}"},
            expect_errors=True,
        )

        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


    def test_agent_is_disabled(
        self,
        app: DjangoTestApp,
        organization: Organization,
        dataset: Dataset,
        dsa: str,
        url_dataset_structure: str,
        valid_token_disabled_agent: str,
    ):
        response = app.put(
            url_dataset_structure,
            dsa,
            content_type="text/csv",
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

        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_json = response.json
        assert response_json == {
            "code": "Forbidden",
            "type": "system",
            "template": "Access is forbidden.",
            "message": "You do not have permission to perform this action.",
            "additionalProperties": None,
        }

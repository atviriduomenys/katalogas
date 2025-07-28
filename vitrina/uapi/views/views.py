import uuid
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import QuerySet, Q
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from filer.models import File
from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from rest_framework.response import Response
from reversion import create_revision

from vitrina import settings
from vitrina.api.oauth import (
    OAuth2AuthenticationWithLocalJWK,
    IsOAuthTokenValid,
    OAuthTokenHasScopes,
    OAuthTokenHasValidOrganizationClaim,
)
from vitrina.api.serializers import PostDatasetDistributionSerializer
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.exceptions import UAPIException
from vitrina.orgs.models import Organization
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.models import Metadata
from vitrina.structure.services import create_structure_objects
from vitrina.uapi.serializers.uapi_serializers import BaseObjectListSerializer
from vitrina.uapi.serializers.serializers import (
    UAPIDatasetSerializer,
    DatasetQueryParameterSerializer,
    DistributionQueryParameterSerializer,
    UAPIDistributionSerializer, UAPIDatasetCreateSerializer
)
from vitrina.uapi.utils.utils import extract_type_from_url
from vitrina.uapi.utils.views import UAPIExceptionHandlerMixin


class DatasetViewSet(UAPIExceptionHandlerMixin, viewsets.ModelViewSet):
    authentication_classes = [OAuth2AuthenticationWithLocalJWK]
    permission_classes = [IsOAuthTokenValid, OAuthTokenHasScopes, OAuthTokenHasValidOrganizationClaim]
    required_scopes = settings.OAUTH_AGENT_DEFAULT_SCOPES  # TODO: Update scopes to be specific per action.

    @cached_property
    def dataset_metadata_id(self) -> int:
        return ContentType.objects.get_for_model(Dataset).id

    def get_queryset(self) -> QuerySet[Dataset]:
        queryset = Dataset.objects.prefetch_related(
            "category",
            "part_of",
            "type"
        ).select_related(
            "catalog",
            "organization",
            "frequency",
            "publisher",
            "endpoint_type",
            "endpoint_description_type",
            "current_structure"
        ).filter(
            ~Q(deleted=True),
            metadata__content_type_id=self.dataset_metadata_id,
            organization__kind=self.kwargs["form"],
            organization__name=self.kwargs["org"],
        )

        if request_params := self.request.query_params:
            query_parameter_serializer = DatasetQueryParameterSerializer(data=request_params)
            query_parameter_serializer.is_valid(raise_exception=True)

            if name := query_parameter_serializer.validated_data.get("name"):
                queryset = queryset.filter(metadata__name=name)

        return queryset

    def get_serializer_class(self) -> Serializer:
        action_to_serializer_mapper = {
            "create": UAPIDatasetCreateSerializer,
            "list": BaseObjectListSerializer,
        }
        return action_to_serializer_mapper.get(getattr(self, "action", None), UAPIDatasetSerializer)

    @transaction.atomic
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        organization = get_object_or_404(Organization, kind=self.kwargs["form"], name=self.kwargs["org"])

        serializer_context = self.get_serializer_context()
        serializer = self.get_serializer(
            data=request.data,
            context={
                **serializer_context,
                "organization": organization,
            }
        )
        serializer.is_valid(raise_exception=True)
        with create_revision():
            instance = serializer.save(access_rights=Dataset.NON_PUBLIC)

        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=instance,
            content_type=ContentType.objects.get_for_model(serializer.Meta.model),
            object_id=instance.pk,
            name=self.request.data.get("name", ""),
            title=serializer.validated_data["title"],
            description=serializer.validated_data["description"],
            prepare_ast={},
            version=1,
        )

        response_serializer = UAPIDatasetSerializer(
            instance,
            context={
                **serializer_context,
                "_type": extract_type_from_url(self.request.build_absolute_uri()),
            },
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if not (datasets := self.get_queryset()):
            raise UAPIException(
                code="dataset_not_found",
                type="DatasetNotFound",
                template="The requested Dataset could not be found.",
                message=f"No dataset matched the provided query — {request.build_absolute_uri()}.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = BaseObjectListSerializer(
            instance=datasets,
            context=self.get_serializer_context(),
            data_serializer_class=UAPIDatasetSerializer,
            _type=extract_type_from_url(self.request.build_absolute_uri()),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="dsa")
    def upload_dataset_structure(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        dataset = get_object_or_404(
            Dataset,
            ~Q(deleted=True),
            id=self.kwargs["dataset_id"],
            organization__kind=self.kwargs["form"],
            organization__name=self.kwargs["org"],
        )

        if not request.body or not request.body.strip(b"\r\n\t "):
            # Strip common special characters to find-out if the file is empty.
            raise UAPIException(
                code="empty_csv",
                type="EmptyCSVContent",
                template="The uploaded file is empty or contains only whitespace.",
                message="CSV content is missing or invalid.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Mimics file upload done via DatasetStructureImportView.
        file_name = f"dataset_{dataset.id}_structure.csv"
        content_file = ContentFile(request.body.decode(), name=file_name)
        filer_file = File.objects.create(
            original_filename=file_name,
            file=content_file,
        )
        structure = DatasetStructure.objects.create(
            dataset=dataset,
            file=filer_file,
            filename=file_name,
            mime_type="text/csv",
            size=content_file.size,
        )
        dataset.current_structure = structure
        create_structure_objects(structure)
        dataset.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(detail=False, methods=["put"], url_path="dsa")
    def update_dataset_structure(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # TODO: This will be implemented with the upcoming functionalities. Not in the scope of the MVP.
        # - https://github.com/atviriduomenys/katalogas/issues/1598
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class DistributionViewSet(UAPIExceptionHandlerMixin, viewsets.ModelViewSet):
    authentication_classes = [OAuth2AuthenticationWithLocalJWK]
    permission_classes = [IsOAuthTokenValid, OAuthTokenHasScopes, OAuthTokenHasValidOrganizationClaim]
    required_scopes = settings.OAUTH_AGENT_DEFAULT_SCOPES  # TODO: Update scopes to be specific per action.

    @cached_property
    def distribution_metadata_id(self) -> int:
        return ContentType.objects.get_for_model(DatasetDistribution).id

    def get_queryset(self) -> QuerySet[DatasetDistribution]:
        queryset = DatasetDistribution.objects.select_related(
            "dataset__organization",
            "data_service",
            "format",
            "compression_format",
            "packaging_format",
        ).filter(
            ~Q(deleted=True),
            ~Q(dataset__deleted=True),
            metadata__content_type_id=self.distribution_metadata_id,
            dataset__organization__kind=self.kwargs["form"],
            dataset__organization__name=self.kwargs["org"]
        )

        if request_params := self.request.query_params:
            query_parameter_serializer = DistributionQueryParameterSerializer(data=request_params)
            query_parameter_serializer.is_valid(raise_exception=True)
            validated_data = query_parameter_serializer.validated_data
            if name := validated_data.get("name"):
                queryset = queryset.filter(metadata__name=name)
            if dataset_id := validated_data.get("dataset_id"):
                queryset = queryset.filter(dataset_id=dataset_id)

        return queryset

    def get_serializer_class(self) -> Serializer:
        action_to_serializer_mapper = {
            "create": PostDatasetDistributionSerializer,
            "list": BaseObjectListSerializer,
        }
        return action_to_serializer_mapper.get(getattr(self, "action", None), UAPIDistributionSerializer)

    @transaction.atomic
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer_context = self.get_serializer_context()
        serializer = self.get_serializer(
            data=request.data,
            context={
                **serializer_context,
                "dataset": Dataset.objects.get(pk=request.data.get("dataset")),
            }
        )
        serializer.is_valid(raise_exception=True)
        with create_revision():
            instance = serializer.save()

        response_serializer = UAPIDistributionSerializer(
            instance,
            context={
                **serializer_context,
                "_type": extract_type_from_url(self.request.build_absolute_uri()),
            },
        )

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if not (distributions := self.get_queryset()):
            raise UAPIException(
                code="distributions_not_found",
                type="DistributionsNotFound",
                template="The requested Distributions could not be found.",
                message="No distributions matched the provided query.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = BaseObjectListSerializer(
            instance=distributions,
            context=self.get_serializer_context(),
            data_serializer_class=UAPIDistributionSerializer,
            _type=extract_type_from_url(self.request.build_absolute_uri()),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

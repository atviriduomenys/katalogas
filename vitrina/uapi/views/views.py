import uuid
from http import HTTPStatus
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import QuerySet, Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.functional import cached_property
from filer.models import File
from rest_framework import status
from rest_framework.request import Request
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from vitrina.api.serializers import PostDatasetDistributionSerializer
from vitrina.datasets.models import Dataset, DatasetStructure, DCATResourceSubclass
from vitrina.exceptions import UAPIException
from vitrina.resources.models import DatasetDistribution
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.models import Agreement
from vitrina.structure.models import Metadata, Version
from vitrina.structure.services import create_structure_objects, export_dataset_structure
from vitrina.uapi import HTTPMethods, PossibleResults
from vitrina.uapi.models import AgentEnv, RequestHistory
from vitrina.uapi.serializers.uapi_serializers import BaseObjectListSerializer
from vitrina.uapi.serializers.serializers import (
    UAPIDatasetSerializer,
    DatasetQueryParameterSerializer,
    DistributionQueryParameterSerializer,
    UAPIDistributionSerializer,
    UAPIDatasetCreateSerializer,
    UAPIVersionSerializer,
    VersionQueryParameterSerializer,
    UAPIAgentSerializer,
    ConnectionCheckSerializer,
)
from vitrina.uapi.utils.utils import extract_type_from_url
from vitrina.uapi.views.mixins import AgentAuthViewSetMixin, UAPIExceptionHandlerMixin


class ConnectionViewSet(UAPIExceptionHandlerMixin, AgentAuthViewSetMixin, ViewSet):
    @action(detail=False, methods=["post"])
    def check(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = ConnectionCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        agent_env = get_object_or_404(
            AgentEnv,
            agent__organization=self.request.organization,
            oauth_client_id=self.request.auth["sub"],
        )
        # TODO: Currently hard-coding the logging;
        #   Implement a better solution in the future: https://github.com/atviriduomenys/katalogas/issues/1896.
        RequestHistory.objects.create(
            agent_env=agent_env,
            endpoint=request.build_absolute_uri(),
            method=HTTPMethods(self.request.method.upper()),
            http_result=HTTPStatus.NO_CONTENT,
            result=PossibleResults.STATUS_ALIVE,
            details=f"Spinta: {serializer.validated_data['spinta_version']}",
            error=None,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class DatasetViewSet(UAPIExceptionHandlerMixin, AgentAuthViewSetMixin, ModelViewSet):
    required_scopes = {
        "create": ["uapi:/datasets/gov/vssa/dcat/Dataset/:create"],
        "list": ["uapi:/datasets/gov/vssa/dcat/Dataset/:getall"],
        "upload_dataset_structure": ["uapi:/datasets/gov/vssa/dcat/Dsa/:create"],
        "update_dataset_structure": ["uapi:/datasets/gov/vssa/dcat/Dsa/:patch"],
    }

    @cached_property
    def dataset_metadata_id(self) -> int:
        return ContentType.objects.get_for_model(Dataset).id

    @cached_property
    def dcat_resource_subclass(self) -> DCATResourceSubclass:
        subclass_name = self.request.data.get("subclass", DCATResourceSubclass.DATASET)
        return get_object_or_404(DCATResourceSubclass, name=subclass_name)

    def get_queryset(self) -> QuerySet[Dataset]:
        queryset = (
            Dataset.objects.prefetch_related("category", "part_of", "type")
            .select_related(
                "catalog",
                "organization",
                "frequency",
                "publisher",
                "endpoint_type",
                "endpoint_description_type",
                "current_structure",
            )
            .filter(
                ~Q(deleted=True),
                metadata__content_type_id=self.dataset_metadata_id,
                organization=self.request.organization,
            )
        )

        if request_params := self.request.query_params:
            query_parameter_serializer = DatasetQueryParameterSerializer(data=request_params)
            query_parameter_serializer.is_valid(raise_exception=True)

            if name := query_parameter_serializer.validated_data.get("name"):
                queryset = queryset.filter(metadata__name=name)

            if parent_id := query_parameter_serializer.validated_data.get("parent_id"):
                queryset = queryset.filter(id=parent_id).first().get_children()

        return queryset

    def get_serializer_class(self) -> Serializer:
        action_to_serializer_mapper = {
            "create": UAPIDatasetCreateSerializer,
            "list": BaseObjectListSerializer,
        }
        return action_to_serializer_mapper.get(getattr(self, "action", None), UAPIDatasetSerializer)

    @transaction.atomic
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        organization = self.request.organization

        serializer_context = self.get_serializer_context()
        serializer = self.get_serializer(
            data=request.data,
            context={
                **serializer_context,
                "organization": organization,
            },
        )
        serializer.is_valid(raise_exception=True)

        dataset_data = serializer.validated_data | {
            "subclass": self.dcat_resource_subclass,
            "access_rights": Dataset.NON_PUBLIC,
            "organization_id": organization.id,
        }

        title = dataset_data.get("title", None)
        description = dataset_data.get("description", None)
        parent_id = dataset_data.pop("parent_id", None)

        instance = Dataset(**dataset_data)

        if parent_id and (parent := Dataset.objects.filter(id=parent_id).first()):
            parent.add_child(instance=instance)
        else:
            Dataset.add_root(instance=instance)

        language = getattr(request, "LANGUAGE_CODE", "lt")
        instance.set_current_language(language)
        instance.title = title or instance.title
        instance.description = description or instance.description
        instance.save()

        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=instance,
            content_type=ContentType.objects.get_for_model(serializer.Meta.model),
            object_id=instance.pk,
            name=self.request.data.get("name", ""),
            title=title,
            description=description,
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
            id=self.kwargs["pk"],
            organization=self.request.organization,
        )

        if not request.body or not request.body.strip(b"\r\n\t "):
            # Strip common special characters to find-out if the file is empty.
            raise UAPIException(
                code="empty_csv",
                type="EmptyCSVContent",
                template="The uploaded file is empty or contains only whitespace.",
                message="CSV content is missing or invalid.",
                status_code=status.HTTP_400_BAD_REQUEST,
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

    @action(detail=False, methods=["get"], url_path="dsa")
    def get_dataset_structure(self, request: Request, *args: Any, **kwargs: Any) -> Response | StreamingHttpResponse:
        dataset = get_object_or_404(
            Dataset,
            ~Q(deleted=True),
            id=self.kwargs["pk"],
            organization=self.request.organization,
        )

        if not dataset.current_structure or not dataset.current_structure.file:
            return Response(
                {"detail": "Dataset structure not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        stream = export_dataset_structure(dataset)
        response = StreamingHttpResponse(stream, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=manifest.csv"
        return response

    @transaction.atomic
    @action(detail=False, methods=["put"], url_path="dsa")
    def update_dataset_structure(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # TODO: This will be implemented with the upcoming functionalities. Not in the scope of the MVP.
        # - https://github.com/atviriduomenys/katalogas/issues/1598
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class DistributionViewSet(UAPIExceptionHandlerMixin, AgentAuthViewSetMixin, ModelViewSet):
    required_scopes = {
        "create": ["uapi:/datasets/gov/vssa/dcat/Distribution/:create"],
        "list": ["uapi:/datasets/gov/vssa/dcat/Distribution/:getall"],
    }

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
            dataset__organization=self.request.organization,
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
            },
        )
        serializer.is_valid(raise_exception=True)
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


class AgentSyncDoneViewSet(UAPIExceptionHandlerMixin, AgentAuthViewSetMixin, ModelViewSet):
    required_scopes = {"update": ["uapi:/datasets/gov/vssa/dcat/Agreement/:patch"]}

    lookup_url_kwarg = "agreement_id"

    def get_queryset(self) -> QuerySet:
        queryset = Agreement.objects.filter(
            is_agent_sync_enabled=True,
            assignee=self.request.organization,
        )

        return queryset

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        agreement = self.get_object()
        agreement.last_sync_date = timezone.now()
        agreement.status = AgreementStatuses.ACTIVE

        # Agent Sync changes are determined by time between Agreement.updated_at
        # and Agreement.last_sync_date. This endpoint should not update
        # Agreement.updated_at in case changes were made since the start of sync that
        # haven't been synced.
        agreement.save(update_fields=["last_sync_date", "status"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class VersionViewSet(UAPIExceptionHandlerMixin, AgentAuthViewSetMixin, ModelViewSet):
    required_scopes = {"list": ["uapi:/datasets/gov/vssa/dcat/Version/:getall"]}

    def get_queryset(self) -> QuerySet:
        queryset = Version.objects.select_related("dataset__organization").filter(
            dataset__organization=self.request.organization,
        )

        if request_parameters := self.request.query_params:
            query_parameter_serializer = VersionQueryParameterSerializer(data=request_parameters)
            query_parameter_serializer.is_valid(raise_exception=True)

            if dataset_id := query_parameter_serializer.validated_data.get("dataset_id"):
                queryset = queryset.filter(dataset_id=dataset_id)

        return queryset

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = BaseObjectListSerializer(
            instance=self.get_queryset(),
            context=self.get_serializer_context(),
            data_serializer_class=UAPIVersionSerializer,
            _type=extract_type_from_url(self.request.build_absolute_uri()),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class AgentViewSet(UAPIExceptionHandlerMixin, AgentAuthViewSetMixin, ModelViewSet):
    required_scopes = {"list": ["uapi:/datasets/gov/vssa/dcat/Agent/:getall"]}

    def get_queryset(self) -> QuerySet:
        jwt_subject = self.request.auth["sub"]
        queryset = AgentEnv.not_archived.filter(
            agent__organization=self.request.organization,
            oauth_client_id=jwt_subject,
        )
        return queryset

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = BaseObjectListSerializer(
            instance=self.get_queryset(),
            context=self.get_serializer_context(),
            data_serializer_class=UAPIAgentSerializer,
            _type=extract_type_from_url(self.request.build_absolute_uri()),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

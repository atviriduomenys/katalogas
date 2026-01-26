from functools import cached_property
from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from django.urls import reverse
from rest_framework import viewsets, status, serializers
from rest_framework.request import Request
from rest_framework.response import Response

from scripts.extract_elements_from_adoc import SCOPES_REGEX
from vitrina.api.oauth import (
    OAuthClientAuthenticator,
)
from vitrina.exceptions import UAPIException
from vitrina.projects.models import UseCaseClient
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.models import Agreement
from vitrina.smart_contracts.services import extract_elements_from_adoc
from vitrina.uapi.models import Agent
from vitrina.uapi.pagination import UAPIPagination
from vitrina.uapi.serializers.uapi_serializers import BaseObjectListSerializer, BaseUUIDObjectMixin
from vitrina.uapi.utils.utils import extract_type_from_url
from vitrina.uapi.views.mixins import AgentAuthViewSetMixin, UAPIExceptionHandlerMixin


class AgreementQueryParameterSerializer(serializers.Serializer):
    datasets = serializers.ListField(child=serializers.UUIDField(), required=False)

    def to_internal_value(self, data: dict) -> dict:
        data = data.copy()
        if "datasets._id" in data:
            data.setlist("datasets", data.getlist("datasets._id"))
        return super().to_internal_value(data)

    def validate_datasets(self, dataset_uuids: list[UUID]) -> list[UUID]:
        if not dataset_uuids:
            return dataset_uuids

        if non_agent_dataset_uuids := (set(dataset_uuids) - self.context["agent_dataset_uuids"]):
            raise UAPIException(
                code="invalid_agreement_query_filter",
                type="InvalidAgreementQueryFilter",
                template="Given query filter is invalid.",
                message=f"datasets._id values: {', '.join(map(str, non_agent_dataset_uuids))} are invalid.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return dataset_uuids


class UAPIClientListSerializer(BaseUUIDObjectMixin, serializers.ModelSerializer):
    class Meta:
        model = UseCaseClient
        fields = BaseUUIDObjectMixin.Meta.fields


class UAPIAgreementListSerializer(BaseUUIDObjectMixin, serializers.ModelSerializer):
    clients = serializers.SerializerMethodField()
    agreement_file_url = serializers.SerializerMethodField()
    agreement_scopes = serializers.SerializerMethodField()

    def get_clients(self, obj: Agreement) -> list[dict]:
        return UAPIClientListSerializer(obj.project.client_set.all(), many=True).data

    def get_agreement_file_url(self, obj: Agreement) -> str:
        if not (agreement_adoc := obj.latest_agreement_adoc):
            raise UAPIException(
                code="agreement_file_does_not_exist",
                type="AgreementFileDoesNotExist",
                template="Agreement file does not exist.",
                message=f"Agreement adoc file does not exist for agreement (_id={obj.uuid})",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return reverse("uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_adoc.uuid})

    def get_agreement_scopes(self, obj: Agreement) -> list[str]:
        if not (agreement_adoc := obj.latest_agreement_adoc):
            raise UAPIException(
                code="agreement_file_does_not_exist",
                type="AgreementFileDoesNotExist",
                template="Agreement file does not exist.",
                message=f"Agreement adoc file does not exist for agreement (_id={obj.uuid})",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            scopes = extract_elements_from_adoc(agreement_adoc.file.path, SCOPES_REGEX)
        except InvalidAdocError as error:
            raise UAPIException(
                code="scope_extraction_error",
                type="CannotExtractAgreementScopes",
                template="Agreement scopes cannot be extracted from.",
                message=f"Scopes cannot be extracted from Agreement file (_id={agreement_adoc.uuid}). Error: {error}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return scopes

    class Meta:
        model = Agreement
        fields = (
            "clients",
            "agreement_file_url",
            "agreement_scopes",
        ) + BaseUUIDObjectMixin.Meta.fields


class AgreementViewSet(UAPIExceptionHandlerMixin, AgentAuthViewSetMixin, viewsets.ModelViewSet):
    pagination_class = UAPIPagination
    required_scopes = {
        "list": ["uapi:/datasets/gov/vssa/dcat/Agreement/:getall"],
    }

    @cached_property
    def get_agent_dataset_uuids(self) -> set[str]:
        agent = Agent.objects.select_related("service").get(
            oauth_client_id=OAuthClientAuthenticator.resolve_client_id_from_token(self.request.auth)
        )
        agent_datasets_uuids = {agent.service.uuid}
        agent_datasets_uuids.update(list(agent.service.get_descendants().values_list("uuid", flat=True)))

        return agent_datasets_uuids

    def get_queryset(self) -> QuerySet:
        organization = getattr(self.request, "organization")

        dataset_uuids = self.get_agent_dataset_uuids
        if request_params := self.request.query_params:
            query_parameter_serializer = AgreementQueryParameterSerializer(
                data=request_params, context={"agent_dataset_uuids": self.get_agent_dataset_uuids}
            )
            query_parameter_serializer.is_valid(raise_exception=True)
            if validated_dataset_uuids := query_parameter_serializer.validated_data.get("datasets"):
                dataset_uuids = validated_dataset_uuids

        queryset = (
            Agreement.objects.filter(
                assigner=organization,
                status__in=(AgreementStatuses.SIGNED, AgreementStatuses.ACTIVE),
                project__datasets__uuid__in=dataset_uuids,
            )
            .prefetch_related("project__client_set")
            .order_by("-created_at")
            .distinct()
        )

        return queryset

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = BaseObjectListSerializer(
            instance=self.paginate_queryset(self.get_queryset()),
            context=self.get_serializer_context(),
            data_serializer_class=UAPIAgreementListSerializer,
            _type=extract_type_from_url(self.request.build_absolute_uri()),
        )
        return self.get_paginated_response(serializer.data)

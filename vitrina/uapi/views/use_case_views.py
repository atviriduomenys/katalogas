from typing import Any
from uuid import UUID

from django.db.models import QuerySet, Prefetch
from django.urls import reverse
from rest_framework import viewsets, status, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from scripts.extract_elements_from_adoc import SCOPES_REGEX
from vitrina.api.oauth import (
    OAuth2Authentication,
    IsOAuthTokenValid,
    OAuthTokenHasScopes,
    OAuthTokenHasValidOrganizationClaim,
)
from vitrina.exceptions import UAPIException
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.models import AgreementFile, Agreement
from vitrina.smart_contracts.services import extract_elements_from_adoc
from vitrina.uapi.serializers.uapi_serializers import BaseObjectListSerializer, BaseObjectMixin
from vitrina.uapi.utils.utils import extract_type_from_url
from vitrina.uapi.utils.views import UAPIExceptionHandlerMixin


class ScopeExtractionError(Exception):
    msg: str
    agreement: Agreement
    agreement_file: AgreementFile

    def __init__(self, msg: str, agreement: Agreement, agreement_file: AgreementFile) -> None:
        self.msg = msg
        self.agreement = agreement
        self.agreement_file = agreement_file


class UseCaseQueryParameterSerializer(serializers.Serializer):
    dataset = serializers.ListField(child=serializers.UUIDField(), required=False)


class UAPIUseCaseListSerializer(BaseObjectMixin, serializers.ModelSerializer):
    uuid = serializers.UUIDField()

    class Meta:
        model = Project
        fields = ("uuid",) + BaseObjectMixin.Meta.fields


class UAPIUseCaseSerializer(BaseObjectMixin, serializers.ModelSerializer):
    _latest_adoc_cache: dict[UUID, AgreementFile | None]
    uuid = serializers.UUIDField()
    agreements = serializers.SerializerMethodField()
    contract_scopes = serializers.SerializerMethodField()
    clients = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._latest_adoc_cache = {}

    def _get_latest_agreement_adoc(self, agreement: Agreement) -> AgreementFile | None:
        if agreement.uuid in self._latest_adoc_cache:
            return self._latest_adoc_cache[agreement.uuid]

        agreement_adocs = [
            agreement_file
            for agreement_file in agreement.files.all()
            if agreement_file.file_extension == AgreementFile.AllowedFileTypes.ADOC
        ]
        agreement_adocs = sorted(agreement_adocs, key=lambda file: file.created_at, reverse=True)

        self._latest_adoc_cache[agreement.uuid] = agreement_adocs[0] if agreement_adocs else None
        return self._latest_adoc_cache[agreement.uuid]

    def _is_ready_for_sync(self, agreement: Agreement) -> bool:
        organization = self.context.get("organization")
        if agreement.assigner != organization:
            return False

        if agreement.status not in (AgreementStatuses.SIGNED, AgreementStatuses.ACTIVE):
            return False

        if not self._get_latest_agreement_adoc(agreement):
            return False

        return True

    def get_agreements(self, obj: Project) -> dict:
        agreements = {}
        for agreement in obj.agreements.all():
            if not self._is_ready_for_sync(agreement):
                continue

            agreement_adoc = self._get_latest_agreement_adoc(agreement)
            file_url = self.context.get("request").build_absolute_uri(
                reverse("uapi-agreement-file-download", kwargs={"agreement_file_uuid": agreement_adoc.uuid})
            )
            agreements[str(agreement.uuid)] = {"file_url": file_url}

        return agreements

    def get_contract_scopes(self, obj: Project) -> dict:
        agreement_contract_scopes = {}

        for agreement in obj.agreements.all():
            if not self._is_ready_for_sync(agreement):
                continue

            agreement_adoc = self._get_latest_agreement_adoc(agreement)
            try:
                scopes = extract_elements_from_adoc(agreement_adoc.file.path, SCOPES_REGEX)
            except InvalidAdocError as error:
                raise ScopeExtractionError(agreement=agreement, agreement_file=agreement_adoc, msg=str(error))
            agreement_contract_scopes[str(agreement.uuid)] = scopes

        return agreement_contract_scopes

    def get_clients(self, obj: Project) -> list:
        return [str(client.uuid) for client in obj.client_set.all()]

    class Meta:
        model = Project
        fields = (
            "uuid",
            "agreements",
            "contract_scopes",
            "clients",
        ) + BaseObjectMixin.Meta.fields


class UseCaseViewSet(UAPIExceptionHandlerMixin, viewsets.ModelViewSet):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [
        IsOAuthTokenValid,
        OAuthTokenHasScopes,
        OAuthTokenHasValidOrganizationClaim,
    ]
    required_scopes = {
        "list": ["uapi:/datasets/gov/vssa/dcat/UseCase/:getall"],
        "retrieve": ["uapi:/datasets/gov/vssa/dcat/UseCase/:getone"],
    }

    lookup_field = "uuid"
    lookup_url_kwarg = "use_case_uuid"

    def get_queryset(self) -> QuerySet:
        organization = getattr(self.request, "organization")

        agreements_prefetch = Prefetch("agreements", queryset=Agreement.objects.all().prefetch_related("files"))
        queryset = (
            Project.objects.filter(
                agreements__assigner=organization,
                agreements__status__in=(AgreementStatuses.SIGNED, AgreementStatuses.ACTIVE),
            )
            .prefetch_related(agreements_prefetch, "client_set")
            .order_by("-id")
        )

        if request_params := self.request.query_params:
            # TODO: query_params does not comply with UAPI URL specifications.
            #  "_or.dataset" and "_and.dataset" are not supported
            query_parameter_serializer = UseCaseQueryParameterSerializer(data=request_params)
            query_parameter_serializer.is_valid(raise_exception=True)
            validated_data = query_parameter_serializer.validated_data

            if datasets := validated_data.get("dataset"):
                queryset = queryset.filter(datasets__uuid__in=datasets)

        return queryset.distinct()

    def get_serializer_class(self) -> Serializer:
        action_to_serializer_mapper = {
            "list": BaseObjectListSerializer,
            "retrieve": UAPIUseCaseSerializer,
        }
        return action_to_serializer_mapper.get(getattr(self, "action", None))

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        context["organization"] = getattr(self.request, "organization")

        return context

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if not (use_cases := self.get_queryset()):
            raise UAPIException(
                code="use_case_not_found",
                type="UseCaseNotFound",
                template="The requested UseCase could not be found.",
                message="No use case matched the provided query.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = BaseObjectListSerializer(
            instance=use_cases,
            context=self.get_serializer_context(),
            data_serializer_class=UAPIUseCaseListSerializer,
            _type=extract_type_from_url(self.request.build_absolute_uri()),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        try:
            response_data = serializer.data
        except ScopeExtractionError as error:
            raise UAPIException(
                code="smart_contract_parse_error",
                type="SmartContractParseError",
                template="One of smart contract files cannot be parsed.",
                message=(
                    f"Agreement (uuid={error.agreement.uuid}) file (uuid={error.agreement_file.uuid}) cannot "
                    f"be parsed. Reason: {error.msg}"
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(response_data)

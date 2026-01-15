from typing import Any

from django.db.models import Q
from django.http import FileResponse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView

from vitrina.exceptions import UAPIException
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.models import AgreementFile
from vitrina.uapi.views.mixins import AgentAuthViewSetMixin, UAPIExceptionHandlerMixin


class AgreementFileDownloadUAPIView(UAPIExceptionHandlerMixin, AgentAuthViewSetMixin, APIView):
    action = "get"
    required_scopes = {
        "get": ["uapi:/datasets/gov/vssa/dcat/AgreementFile/:getone"],
    }

    def get(self, request: Request, *args: Any, **kwargs: Any) -> FileResponse:
        organization = getattr(request, "organization")

        try:
            agreement_file = AgreementFile.objects.get(
                Q(agreement__assignee=organization) | Q(agreement__assigner=organization),
                agreement__status__in=(AgreementStatuses.SIGNED, AgreementStatuses.ACTIVE),
                file_extension=AgreementFile.AllowedFileTypes.ADOC,
                uuid=self.kwargs.get("agreement_file_uuid"),
            )
        except AgreementFile.DoesNotExist:
            raise UAPIException(
                code="agreement_file_not_found",
                type="AgreementFileNotFound",
                template="The requested AgreementFile could not be found.",
                message="No agreement file matched the provided query.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            agreement_file.file.open("rb"),
            as_attachment=True,
            filename=f"{agreement_file.uuid}.{agreement_file.file_extension}",
        )

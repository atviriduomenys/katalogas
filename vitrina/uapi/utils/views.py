from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied as RestPermissionDenied
from rest_framework.response import Response

from vitrina.exceptions import UAPIException
from vitrina.uapi.serializers.uapi_serializers import BaseErrorSerializer


class UAPIExceptionHandlerMixin:
    """This mixin is used to format every unexpected/error response from an API that is based on UAPI.

    Every response is described in the following URL:
    - https://ivpk.github.io/uapi/
    """
    def handle_exception(self, exc: Exception) -> Response:
        if isinstance(exc, UAPIException):
            serializer = BaseErrorSerializer(data=exc.detail)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=exc.status_code)

        if isinstance(exc, ValidationError):
            serializer = BaseErrorSerializer(data={
                "code": "validation_error",
                "type": "ValidationError",
                "template": "Request validation failed.",
                "message": str(exc.detail),
                "context": {"errors": exc.detail},
                "additional_properties": None,
            })
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(exc, (Http404, NotFound)):
            serializer = BaseErrorSerializer(data={
                "code": "not_found",
                "type": "NotFound",
                "template": "The requested resource was not found.",
                "message": str(exc),
                "additional_properties": None,
            })
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_404_NOT_FOUND)

        if isinstance(exc, (RestPermissionDenied, PermissionDenied)):
            serializer = BaseErrorSerializer(data={
                "code": "Forbidden",
                "type": "system",
                "template": "Access is forbidden.",
                "message": str(exc),
                "additional_properties": None,
            })
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_403_FORBIDDEN)

        error_data = BaseErrorSerializer.from_exception(exc)
        serializer = BaseErrorSerializer(data=error_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

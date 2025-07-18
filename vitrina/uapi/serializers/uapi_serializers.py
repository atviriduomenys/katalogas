"""
uapi_serializers.py

Base and helper serializers for formatting API payloads according to the Universal API (UAPI) specification.

Reference:
- UAPI Specification: https://ivpk.github.io/uapi/
"""
import traceback
from typing import Any

from django.db.models import Model
from rest_framework import serializers
from reversion.models import Version


class BaseObjectMixin(serializers.Serializer):
    _context = serializers.CharField(default="")
    _type = serializers.SerializerMethodField()
    _id = serializers.CharField(source="id")
    _revision = serializers.SerializerMethodField()
    _txn = serializers.CharField(default="")
    _created = serializers.DateTimeField(source="created")
    _updated = serializers.DateTimeField(source="modified")

    def to_representation(self, instance: Model) -> dict:
        representation = super().to_representation(instance)
        representation["@context"] = representation.pop("_context", "") or ""
        return representation

    def get__type(self, obj: Model) -> str:
        return self.context.get("_type", "")

    def get__revision(self, obj: Model) -> str:
        latest_version = Version.objects.get_for_object(obj).first()
        return str(latest_version.revision_id) if latest_version else ""


class BaseObjectListSerializer(serializers.Serializer):
    _type = serializers.CharField()
    _data = serializers.ListField(child=serializers.DictField())

    def __init__(self, *args: Any, **kwargs: Any):
        self.data_serializer_class = kwargs.pop("data_serializer_class", None)
        self._type_value = kwargs.pop("_type", "")
        super().__init__(*args, **kwargs)

    def to_representation(self, instance: Model) -> dict:
        if not self.data_serializer_class:
            raise ValueError("You must provide `data_serializer_class` when initializing BaseObjectListSerializer")

        context = {
            **self.context,
            "_type": self._type_value,
        }
        data_serializer = self.data_serializer_class(instance, many=True, context=context)

        return {
            "_type": self._type_value,
            "_data": data_serializer.data,
        }


class BaseErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    type = serializers.CharField()
    template = serializers.CharField()
    message = serializers.CharField()
    context = serializers.DictField(required=False, allow_null=True)
    additional_properties = serializers.SerializerMethodField()

    def get_additional_properties(self, obj: Model) -> None:
        return None

    def to_representation(self, instance: Model) -> dict:
        representation = super().to_representation(instance)
        representation["additionalProperties"] = representation.pop("additional_properties", None)

        if not representation.get("context"):
            representation.pop("context", None)

        return representation

    @classmethod
    def from_exception(cls, exc: Exception) -> dict:
        return {
            "code": "server_error",
            "type": exc.__class__.__name__,
            "template": "An unexpected server error occurred.",
            "message": str(exc),
            "context": {"exception": traceback.format_exc()},
            "additional_properties": None,
        }

"""
uapi_serializers.py

Base and helper serializers for formatting API payloads according to the Universal API (UAPI) specification.

Reference:
- UAPI Specification: https://ivpk.github.io/uapi/
"""

import traceback
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Model
from rest_framework import serializers
from reversion.models import Version


TYPE_PREFIX_TO_REMOVE = "/uapi/"
timezone = ZoneInfo(settings.TIME_ZONE)


class BaseObjectMixin(serializers.Serializer):
    _context = serializers.CharField(default="")
    _type = serializers.SerializerMethodField()
    _id = serializers.CharField(source="id")
    _revision = serializers.SerializerMethodField()
    _txn = serializers.CharField(default="")
    _created = serializers.SerializerMethodField()
    _updated = serializers.SerializerMethodField()

    class Meta:
        fields = ("_context", "_type", "_id", "_revision", "_txn", "_created", "_updated")

    def to_representation(self, instance: Model) -> dict:
        representation = super().to_representation(instance)
        representation["@context"] = representation.pop("_context", "") or ""
        return representation

    def get__type(self, obj: Model) -> str:
        return (self.context.get("_type", "") or "").removeprefix(TYPE_PREFIX_TO_REMOVE)

    def get__revision(self, obj: Model) -> str:
        # TODO: Logic needs to be updated. https://github.com/atviriduomenys/katalogas/issues/2177
        latest_version = Version.objects.get_for_object(obj).first()
        return str(latest_version.revision_id) if latest_version else ""

    def get__created(self, obj: Model) -> str:
        if hasattr(obj, "created"):
            return obj.created.astimezone(timezone).isoformat()
        elif hasattr(obj, "created_at"):
            return obj.created_at.astimezone(timezone).isoformat()
        return ""

    def get__updated(self, obj: Model) -> str:
        if hasattr(obj, "modified"):
            return obj.modified.astimezone(timezone).isoformat()
        elif hasattr(obj, "updated_at"):
            return obj.updated_at.astimezone(timezone).isoformat()
        return ""


class BaseUUIDObjectMixin(BaseObjectMixin):
    _id = serializers.CharField(source="uuid")


class BaseObjectListSerializer(serializers.Serializer):
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

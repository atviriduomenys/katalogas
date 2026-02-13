from rest_framework import serializers

from vitrina.api.serializers import DatasetSerializer, DatasetDistributionSerializer, PostDatasetSerializer
from vitrina.datasets.models import DCATResourceSubclass
from vitrina.structure.models import Version
from vitrina.uapi.models import Agent
from vitrina.uapi.serializers.uapi_serializers import BaseObjectMixin, BaseUUIDObjectMixin


class ConnectionCheckSerializer(serializers.Serializer):
    spinta_version = serializers.CharField(required=False, max_length=50)


class UAPIAgentSerializer(BaseUUIDObjectMixin, serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = (
            "synchronized_at",
            "is_last_sync_successful",
            "title",
            "codename",
            "object_type",
            "is_open_data_published",
            "open_data_publish_url",
            "is_enabled",
            "service",
            "organization",
            "oauth_client_id",
            "environment",
            "auth_server_url",
            "api_gate_server_url",
            "agent_address",
        ) + BaseObjectMixin.Meta.fields


class UAPIVersionSerializer(BaseObjectMixin, serializers.ModelSerializer):
    dataset_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Version
        fields = (
            "dataset_id",
            "version",
            "released",
            "description",
            "deployed",
            "status",
            "version_type",
            "external_version",
            "major",
            "minor",
            "patch",
        ) + BaseObjectMixin.Meta.fields


class UAPIDatasetSerializer(BaseObjectMixin, DatasetSerializer):
    subclass = serializers.SlugRelatedField(
        slug_field="name",
        queryset=DCATResourceSubclass.objects.all(),
    )

    class Meta(DatasetSerializer.Meta):
        fields = (
            DatasetSerializer.Meta.fields
            + BaseObjectMixin.Meta.fields
            + (
                "subclass",
                "service",
                "series",
            )
        )


class UAPIDatasetCreateSerializer(PostDatasetSerializer):
    subclass = serializers.SlugRelatedField(
        slug_field="name",
        queryset=DCATResourceSubclass.objects.all(),
        default=DCATResourceSubclass.DATASET,
    )
    service = serializers.BooleanField(default=False)
    series = serializers.BooleanField(default=False)
    parent_id = serializers.CharField(required=False, allow_null=True)

    class Meta(PostDatasetSerializer.Meta):
        fields = PostDatasetSerializer.Meta.fields + (
            "name",
            "subclass",
            "parent_id",
            "service",
            "series",
        )


class UAPIDistributionSerializer(BaseObjectMixin, DatasetDistributionSerializer):
    class Meta(DatasetDistributionSerializer.Meta):
        fields = DatasetDistributionSerializer.Meta.fields + BaseObjectMixin.Meta.fields


class DatasetQueryParameterSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=255)
    parent_id = serializers.CharField(required=False, max_length=255)


class DistributionQueryParameterSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=255)
    dataset_id = serializers.CharField(required=False, max_length=255)

    def to_internal_value(self, data: dict) -> dict:
        data = data.copy()
        if "dataset._id" in data:
            data["dataset_id"] = data.get("dataset._id")
        return super().to_internal_value(data)


class VersionQueryParameterSerializer(serializers.Serializer):
    dataset_id = serializers.IntegerField(required=False)

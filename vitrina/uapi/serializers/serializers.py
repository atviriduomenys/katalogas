from rest_framework import serializers

from vitrina.api.serializers import DatasetSerializer, DatasetDistributionSerializer, PostDatasetSerializer
from vitrina.uapi.serializers.uapi_serializers import BaseObjectMixin


class UAPIDatasetSerializer(BaseObjectMixin, DatasetSerializer):
    class Meta(DatasetSerializer.Meta):
        fields = DatasetSerializer.Meta.fields + [
            "_context", "_type", "_id", "_revision", "_txn", "_created", "_updated"
        ]


class UAPIDatasetCreateSerializer(PostDatasetSerializer):
    class Meta(PostDatasetSerializer.Meta):
        fields = PostDatasetSerializer.Meta.fields + ["name"]


class UAPIDistributionSerializer(BaseObjectMixin, DatasetDistributionSerializer):
    class Meta(DatasetDistributionSerializer.Meta):
        fields = DatasetDistributionSerializer.Meta.fields + [
            "_context", "_type", "_id", "_revision", "_txn", "_created", "_updated"
        ]


class DatasetQueryParameterSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=255)


class DistributionQueryParameterSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=255)
    dataset_id = serializers.CharField(required=False, max_length=255)

    def to_internal_value(self, data: dict) -> dict:
        data = data.copy()
        if "dataset._id" in data:
            data["dataset_id"] = data.get("dataset._id")
        return super().to_internal_value(data)

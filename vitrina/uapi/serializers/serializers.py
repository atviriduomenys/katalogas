from rest_framework import serializers

from vitrina.api.serializers import DatasetSerializer, DatasetDistributionSerializer, PostDatasetSerializer
from vitrina.datasets.models import DCATResourceSubclass
from vitrina.uapi.serializers.uapi_serializers import BaseObjectMixin


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
        fields = (
            PostDatasetSerializer.Meta.fields
            + (
                "name",
                "subclass",
                "parent_id",
                "service",
                "series",
            )
        )


class UAPIDistributionSerializer(BaseObjectMixin, DatasetDistributionSerializer):
    class Meta(DatasetDistributionSerializer.Meta):
        fields = DatasetDistributionSerializer.Meta.fields + BaseObjectMixin.Meta.fields


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

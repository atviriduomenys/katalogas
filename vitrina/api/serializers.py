from rest_framework import serializers

from vitrina.catalogs.models import Catalog
from vitrina.classifiers.models import Licence, Category


class LicenceSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True, label="")
    id = serializers.CharField(required=False, allow_blank=True, label="")
    title = serializers.CharField(required=False, allow_blank=True, label="")

    class Meta:
        model = Licence
        fields = ['description', 'id', 'title']


class CatalogSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True, label="")
    id = serializers.CharField(required=False, allow_blank=True, label="")
    licence = LicenceSerializer(read_only=True, label="")
    title = serializers.CharField(required=False, allow_blank=True, label="")

    class Meta:
        model = Catalog
        fields = ['description', 'id', 'licence', 'title']


class CategorySerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True, label="")
    id = serializers.CharField(required=False, allow_blank=True, label="")
    title = serializers.CharField(required=False, allow_blank=True, label="")

    class Meta:
        model = Category
        fields = ['description', 'id', 'title']

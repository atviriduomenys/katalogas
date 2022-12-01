from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from vitrina.api.permissions import APIKeyPermission
from vitrina.api.serializers import CatalogSerializer, CategorySerializer, LicenceSerializer
from vitrina.api.services import CATALOG_TAG, CATEGORY_TAG, LICENCE_TAG
from vitrina.catalogs.models import Catalog
from vitrina.classifiers.models import Category, Licence


header_param = openapi.Parameter(
    'Authorization',
    in_=openapi.IN_HEADER,
    required=True,
    default="ApiKey MY_KEY",
    type=openapi.TYPE_STRING
)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_summary="Retrieve a list of available catalogs",
    operation_description="List of catalogs",
    manual_parameters=[header_param],
    tags=[CATALOG_TAG]
))
class CatalogViewSet(ListModelMixin, GenericViewSet):
    serializer_class = CatalogSerializer
    queryset = Catalog.objects.all()
    permission_classes = (APIKeyPermission,)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_summary="Retrieve all available categories",
    operation_description="All the categories",
    manual_parameters=[header_param],
    tags=[CATEGORY_TAG]
))
class CategoryViewSet(ListModelMixin, GenericViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    permission_classes = (APIKeyPermission,)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_summary="Retrieve a list of available licences",
    operation_description="All the licences",
    manual_parameters=[header_param],
    tags=[LICENCE_TAG]
))
class LicenceViewSet(ListModelMixin, GenericViewSet):
    serializer_class = LicenceSerializer
    queryset = Licence.objects.all()
    permission_classes = (APIKeyPermission,)

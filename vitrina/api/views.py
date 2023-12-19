from django.db.utils import IntegrityError
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.renderers import _SpecRenderer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.views import get_schema_view
from rest_framework import status, permissions, exceptions
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, DestroyModelMixin, CreateModelMixin, UpdateModelMixin
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from reversion import set_comment, set_user
from reversion.views import RevisionMixin

from vitrina.api.models import ApiDescription
from vitrina.api.permissions import APIKeyPermission, HasStatsPostPermission
from vitrina.api.serializers import CatalogSerializer, DatasetSerializer, CategorySerializer, LicenceSerializer, \
    DatasetDistributionSerializer, DatasetStructureSerializer, PostDatasetSerializer, PatchDatasetSerializer, \
    PostDatasetDistributionSerializer, PostDatasetStructureSerializer, PutDatasetDistributionSerializer, \
    PatchDatasetDistributionSerializer, ModelDownloadStatsSerializer
from vitrina.catalogs.models import Catalog
from vitrina.classifiers.models import Category, Licence
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.resources.models import DatasetDistribution
from vitrina.statistics.models import ModelDownloadStats
from vitrina.api.helpers import get_datasets_for_rdf

CATALOG_TAG = 'Catalogs'
CATEGORY_TAG = 'Categories'
LICENCE_TAG = 'Licences'
API_V1_TAG = 'api-v-1-datasets'
RETRIEVING_DATA_TAG = '1. Retrieving data'
ADDING_DATA_TAG = '2. Adding data'
REMOVING_DATA_TAG = '3. Removing data'
UPDATING_DATA_TAG = '4. Updating data'


class PartnerOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema['info']['x-logo'] = {
            'url': static('img/apix.png')
        }
        schema['tags'] = [{
            'name': CATALOG_TAG,
            'description': "Retrieving available catalogs"
        }, {
            'name': CATEGORY_TAG,
            'description': "Retrieving available categories"
        }, {
            'name': LICENCE_TAG,
            'description': "Retrieving available licences"
        }, {
            'name': API_V1_TAG,
            'description': "Operations pertaining to datasets and their distributions"
        }, {
            'name': RETRIEVING_DATA_TAG
        }, {
            'name': ADDING_DATA_TAG
        }, {
            'name': REMOVING_DATA_TAG
        }, {
            'name': UPDATING_DATA_TAG
        }]
        return schema


SchemaView = get_schema_view(
    info=openapi.Info(
        title="",
        default_version="",
    )
)


class PartnerApiView(SchemaView):
    url = None
    patterns = None
    urlconf = None
    public = True
    generator_class = PartnerOpenAPISchemaGenerator
    permission_classes = [permissions.AllowAny]

    def get(self, request, version='', format=None):
        version = request.version or version or ''

        title = description = default_version = ""
        if ApiDescription.objects.filter(identifier="partner"):
            api_description = ApiDescription.objects.filter(identifier="partner").first()
            title = api_description.title
            description = api_description.desription_html
            default_version = api_description.api_version

        info = openapi.Info(
            title=title,
            default_version=default_version,
            description=description
        )

        if isinstance(request.accepted_renderer, _SpecRenderer):
            generator = self.generator_class(info, version, self.url, self.patterns, self.urlconf)
        else:
            generator = self.generator_class(info, version, self.url, patterns=[])

        schema = generator.get_schema(request, self.public)
        if schema is None:
            raise exceptions.PermissionDenied()
        return Response(schema)


HEADER_PARAM = openapi.Parameter(
    'Authorization',
    in_=openapi.IN_HEADER,
    required=True,
    default="ApiKey MY_KEY",
    type=openapi.TYPE_STRING
)
INTERNAL_ID = openapi.Parameter('internalId', in_=openapi.IN_PATH, type=openapi.TYPE_STRING)
DATASET_ID = openapi.Parameter('datasetId', in_=openapi.IN_PATH, type=openapi.TYPE_INTEGER)
DISTRIBUTION_ID = openapi.Parameter('distributionId', in_=openapi.IN_PATH, type=openapi.TYPE_INTEGER)
STRUCTURE_ID = openapi.Parameter('structureId', in_=openapi.IN_PATH, type=openapi.TYPE_INTEGER)


class CatalogViewSet(ListModelMixin, GenericViewSet):
    serializer_class = CatalogSerializer
    queryset = Catalog.objects.all()
    permission_classes = (APIKeyPermission,)

    @swagger_auto_schema(
        operation_summary="Retrieve a list of available catalogs",
        operation_description="List of catalogs",
        manual_parameters=[HEADER_PARAM],
        tags=[CATALOG_TAG]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CategoryViewSet(ListModelMixin, GenericViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    permission_classes = (APIKeyPermission,)

    @swagger_auto_schema(
        operation_summary="Retrieve all available categories",
        operation_description="All the categories",
        manual_parameters=[HEADER_PARAM],
        tags=[CATEGORY_TAG]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class LicenceViewSet(ListModelMixin, GenericViewSet):
    serializer_class = LicenceSerializer
    queryset = Licence.objects.all()
    permission_classes = (APIKeyPermission,)

    @swagger_auto_schema(
        operation_summary="Retrieve a list of available licences",
        operation_description="All the licences",
        manual_parameters=[HEADER_PARAM],
        tags=[LICENCE_TAG]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class DatasetViewSet(RevisionMixin, ModelViewSet):
    serializer_class = DatasetSerializer
    permission_classes = (APIKeyPermission,)
    lookup_url_kwarg = 'datasetId'
    organization = None
    user = None

    def get_queryset(self):
        if self.organization:
            return Dataset.objects.filter(
                organization=self.organization,
                deleted__isnull=True
            )
        return Dataset.objects.none()

    @swagger_auto_schema(
        operation_summary="List all datasets",
        manual_parameters=[HEADER_PARAM],
        tags=[RETRIEVING_DATA_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Get a single dataset",
        manual_parameters=[HEADER_PARAM, DATASET_ID],
        tags=[RETRIEVING_DATA_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a dataset",
        manual_parameters=[HEADER_PARAM],
        tags=[ADDING_DATA_TAG],
        request_body=PostDatasetSerializer,
        responses={status.HTTP_200_OK: DatasetSerializer()}
    )
    def create(self, request, *args, **kwargs):
        serializer = PostDatasetSerializer(
            data=request.data,
            context={
                'organization': self.organization,
                'user': self.user
            }
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        serializer = DatasetSerializer(
            instance,
            context={'request': request}
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @swagger_auto_schema(
        operation_summary="Update dataset by ID",
        manual_parameters=[HEADER_PARAM, DATASET_ID],
        tags=[UPDATING_DATA_TAG],
        request_body=PatchDatasetSerializer,
        responses={status.HTTP_200_OK: DatasetSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = PatchDatasetSerializer(
            instance,
            data=request.data,
            context={'user': self.user},
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        serializer = DatasetSerializer(updated_instance, context={
            'request': request
        })
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Remove a dataset",
        manual_parameters=[HEADER_PARAM, DATASET_ID],
        tags=[REMOVING_DATA_TAG]
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.deleted_on = timezone.now()

        # free up internal_id and slug
        instance.internal_id = None
        instance.slug = None

        instance.save()
        set_comment(Dataset.DELETED)
        set_user(self.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InternalDatasetViewSet(DatasetViewSet):

    def get_object(self):
        internal_id = self.kwargs.get('internalId')
        obj = get_object_or_404(
            Dataset,
            organization=self.organization,
            internal_id=internal_id
        )
        return obj

    @swagger_auto_schema(
        operation_summary="Get a single dataset",
        operation_id="datasets_read_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID],
        tags=[RETRIEVING_DATA_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update dataset by ID",
        operation_id="datasets_partial_update_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID],
        tags=[UPDATING_DATA_TAG],
        request_body=PatchDatasetSerializer,
        responses={status.HTTP_200_OK: DatasetSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Remove a dataset",
        operation_id="datasets_delete_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID],
        tags=[REMOVING_DATA_TAG]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class DatasetDistributionViewSet(ModelViewSet):
    serializer_class = DatasetDistributionSerializer
    permission_classes = (APIKeyPermission,)
    parser_classes = [MultiPartParser, JSONParser]
    lookup_url_kwarg = "distributionId"

    def get_queryset(self):
        dataset = self.get_dataset()
        queryset = DatasetDistribution.objects.filter(dataset=dataset)
        return queryset

    def get_dataset(self):
        return get_object_or_404(Dataset, pk=self.kwargs.get("datasetId"))

    @swagger_auto_schema(
        operation_summary="Get all dataset distributions",
        manual_parameters=[HEADER_PARAM, DATASET_ID],
        tags=[RETRIEVING_DATA_TAG]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Get a single dataset distribution",
        manual_parameters=[HEADER_PARAM, DATASET_ID, DISTRIBUTION_ID],
        tags=[RETRIEVING_DATA_TAG]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update dataset distribution by ID",
        manual_parameters=[HEADER_PARAM, DATASET_ID, DISTRIBUTION_ID],
        tags=[UPDATING_DATA_TAG],
        request_body=PatchDatasetDistributionSerializer,
        responses={status.HTTP_200_OK: DatasetDistributionSerializer()},
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = PatchDatasetDistributionSerializer(
            instance,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        serializer = DatasetDistributionSerializer(updated_instance, context={
            'request': request
        })
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Add a new dataset distribution",
        manual_parameters=[HEADER_PARAM, DATASET_ID],
        tags=[ADDING_DATA_TAG],
        request_body=PostDatasetDistributionSerializer,
        responses={status.HTTP_200_OK: DatasetDistributionSerializer()},
    )
    def create(self, request, *args, **kwargs):
        serializer = PostDatasetDistributionSerializer(
            data=request.data,
            context={'dataset': self.get_dataset()}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        serializer = DatasetDistributionSerializer(
            instance,
            context={'request': request}
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @swagger_auto_schema(
        operation_summary="Add a new dataset distribution",
        manual_parameters=[HEADER_PARAM, DATASET_ID],
        tags=[ADDING_DATA_TAG],
        request_body=PutDatasetDistributionSerializer,
        responses={status.HTTP_200_OK: DatasetDistributionSerializer()},
    )
    def create_with_put(self, request, *args, **kwargs):
        serializer = PutDatasetDistributionSerializer(
            data=request.data,
            context={'dataset': self.get_dataset()}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        serializer = DatasetDistributionSerializer(
            instance,
            context={'request': request}
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @swagger_auto_schema(
        operation_summary="Remove a dataset distribution",
        manual_parameters=[HEADER_PARAM, DATASET_ID, DISTRIBUTION_ID],
        tags=[REMOVING_DATA_TAG]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class InternalDatasetDistributionViewSet(DatasetDistributionViewSet):
    organization = None

    def get_dataset(self):
        internal_id = self.kwargs.get('internalId')
        dataset = get_object_or_404(
            Dataset,
            organization=self.organization,
            internal_id=internal_id
        )
        return dataset

    @swagger_auto_schema(
        operation_summary="Get all dataset distributions",
        operation_id="datasets_distributions_list_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID],
        tags=[RETRIEVING_DATA_TAG]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Get a single dataset distribution",
        operation_id="datasets_distributions_read_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID, DISTRIBUTION_ID],
        tags=[RETRIEVING_DATA_TAG]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Add a new dataset distribution",
        operation_id="datasets_distributions_create_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID],
        tags=[ADDING_DATA_TAG],
        request_body=PostDatasetDistributionSerializer,
        responses={status.HTTP_200_OK: DatasetDistributionSerializer()},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Add a new dataset distribution",
        operation_id="datasets_distributions_create_put_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID],
        tags=[ADDING_DATA_TAG],
        request_body=PutDatasetDistributionSerializer,
        responses={status.HTTP_200_OK: DatasetDistributionSerializer()},
    )
    def create_with_put(self, request, *args, **kwargs):
        return super().create_with_put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update dataset distribution by ID",
        operation_id="datasets_distributions_partial_update_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID, DISTRIBUTION_ID],
        tags=[UPDATING_DATA_TAG],
        request_body=PatchDatasetDistributionSerializer,
        responses={status.HTTP_200_OK: DatasetDistributionSerializer()},
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Remove a dataset distribution",
        operation_id="datasets_distributions_delete_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID, DISTRIBUTION_ID],
        tags=[REMOVING_DATA_TAG]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class DatasetStructureViewSet(

    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    GenericViewSet
):
    serializer_class = DatasetStructureSerializer
    permission_classes = (APIKeyPermission,)
    parser_classes = [MultiPartParser]
    lookup_url_kwarg = "structureId"

    def get_queryset(self):
        dataset = self.get_dataset()
        queryset = DatasetStructure.objects.filter(dataset=dataset)
        return queryset

    def get_dataset(self):
        return get_object_or_404(Dataset, pk=self.kwargs.get('datasetId'))

    @swagger_auto_schema(
        operation_summary="Get all dataset structure entries",
        manual_parameters=[HEADER_PARAM, DATASET_ID],
        tags=[RETRIEVING_DATA_TAG]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Add a new dataset structure",
        manual_parameters=[HEADER_PARAM, DATASET_ID],
        tags=[ADDING_DATA_TAG],
        request_body=PostDatasetStructureSerializer,
        responses={status.HTTP_200_OK: DatasetStructureSerializer()},
    )
    def create(self, request, *args, **kwargs):
        serializer = PostDatasetStructureSerializer(
            data=request.data,
            context={'dataset': self.get_dataset()}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        serializer = DatasetStructureSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @swagger_auto_schema(
        operation_summary="Delete dataset structure description",
        manual_parameters=[HEADER_PARAM, DATASET_ID, STRUCTURE_ID],
        tags=[REMOVING_DATA_TAG]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class InternalDatasetStructureViewSet(DatasetStructureViewSet):
    organization = None

    def get_dataset(self):
        internal_id = self.kwargs.get('internalId')
        dataset = get_object_or_404(
            Dataset,
            organization=self.organization,
            internal_id=internal_id
        )
        return dataset

    @swagger_auto_schema(
        operation_summary="Get all dataset structure entries",
        operation_id="datasets_structure_list_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID],
        tags=[RETRIEVING_DATA_TAG]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Add a new dataset structure",
        operation_id="datasets_structure_create_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID],
        tags=[ADDING_DATA_TAG],
        request_body=PostDatasetStructureSerializer,
        responses={status.HTTP_200_OK: DatasetStructureSerializer()},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete dataset structure description",
        operation_id="datasets_structure_delete_internal",
        manual_parameters=[HEADER_PARAM, INTERNAL_ID, STRUCTURE_ID],
        tags=[REMOVING_DATA_TAG]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class DatasetModelDownloadViewSet(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (HasStatsPostPermission,)

    @swagger_auto_schema(
        operation_summary="Add model statistics",
        request_body=ModelDownloadStatsSerializer,
        responses={status.HTTP_200_OK: ModelDownloadStatsSerializer()},
    )
    def create(self, request, *args, **kwargs):
        serializer = ModelDownloadStatsSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        instance = ModelDownloadStats(**serializer.validated_data)
        if instance.model_requests != 0:
            try:
                ModelDownloadStats.objects.create(
                    source=instance.source,
                    model=instance.model,
                    model_format=instance.model_format,
                    model_requests=instance.model_requests,
                    model_objects=instance.model_objects,
                    created=instance.created
                )
            except IntegrityError:
                ModelDownloadStats.objects.update_or_create(
                    source=instance.source,
                    model=instance.model,
                    model_format=instance.model_format,
                    created=instance.created,
                    defaults={
                        "model_requests": instance.model_requests,
                        "model_objects": instance.model_objects
                    }
                )
        serializer = ModelDownloadStatsSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


def edp_dcat_ap_rdf(request: HttpRequest) -> HttpResponse:
    return render(request, 'vitrina/api/edp/dcat_ap_rdf.html', {
        'datasets': get_datasets_for_rdf(Dataset.public.all()),
    }, content_type='application/rdf+xml')

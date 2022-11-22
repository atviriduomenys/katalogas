from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.templatetags.static import static
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from vitrina.api.models import ApiDescription, ApiKey
from vitrina.orgs.models import Organization

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
        swagger = super().get_schema(request, public)
        swagger['info']['x-logo'] = {
            'url': static('img/apix.png')
        }
        swagger['tags'] = [{
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
        return swagger


def get_partner_schema_view():
    title = description = version = ""
    if ApiDescription.objects.filter(identifier="partner"):
        api_description = ApiDescription.objects.filter(identifier="partner").first()
        title = api_description.title
        description = api_description.desription_html
        version = api_description.api_version

    return get_schema_view(
        openapi.Info(
            title=title,
            default_version=version,
            description=description,
        ),
        public=True,
        generator_class=PartnerOpenAPISchemaGenerator,
        permission_classes=[permissions.AllowAny],
    ).with_ui('redoc')


def get_api_key_organization(request: WSGIRequest) -> Organization:
    organization = None
    ct = ContentType.objects.get_for_model(Organization)
    api_key = request.META.get('HTTP_AUTHORIZATION')
    if api_key and api_key.startswith("ApiKey "):
        api_key = api_key.replace("ApiKey ", "").strip()
        if api_key and ApiKey.objects.filter(
                api_key=api_key,
                representative__content_type=ct,
                representative__object_id__isnull=False
        ).exists():
            api_key_obj = ApiKey.objects.filter(
                api_key=api_key,
                representative__content_type=ct,
                representative__object_id__isnull=False
            ).first()
            organization = api_key_obj.representative.content_object
    return organization

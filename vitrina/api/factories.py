from factory.django import DjangoModelFactory

from vitrina.api.models import ApiKey
from vitrina.orgs.services import hash_api_key


class APIKeyFactory(DjangoModelFactory):
    class Meta:
        model = ApiKey
        django_get_or_create = ('api_key', 'enabled')

    api_key = hash_api_key("test")
    enabled = True

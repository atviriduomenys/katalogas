import uuid

from factory.django import DjangoModelFactory

from vitrina.api.models import ApiKey


class APIKeyFactory(DjangoModelFactory):
    class Meta:
        model = ApiKey
        django_get_or_create = ('api_key', 'enabled')

    api_key = str(uuid.uuid4())
    enabled = True

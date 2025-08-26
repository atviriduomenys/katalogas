import factory
from factory.django import DjangoModelFactory

from vitrina.identifiers.models import Agency, Identifier
from vitrina.datasets.factories import DatasetFactory


class AgencyFactory(DjangoModelFactory):
    code = "risr"
    name = "Registrų ir valstybės informacinių sistemų registras"
    uri = "http://registrai.lt"

    class Meta:
        model = Agency


class IdentifierFactory(DjangoModelFactory):
    notation = "test-identifier"
    resource = factory.SubFactory(DatasetFactory)
    scheme_agency = factory.SubFactory(AgencyFactory)

    class Meta:
        model = Identifier

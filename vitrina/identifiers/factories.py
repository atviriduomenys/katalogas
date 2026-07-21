import factory
from factory.django import DjangoModelFactory

from vitrina.identifiers.models import Agency, Identifier
from vitrina.datasets.factories import DatasetFactory


class AgencyFactory(DjangoModelFactory):
    code = Agency.RISR_CODE
    name = "Registrų ir valstybės informacinių sistemų registras"
    uri = "http://registrai.lt"
    identifier_validation_type = "REGEXP"
    identifier_validation_options = r"^\d{4}$"
    identifier_validation_error_message = "Žymėjimas turi būti sudarytas iš keturių skaitmenų."

    class Meta:
        model = Agency


class IdentifierFactory(DjangoModelFactory):
    notation = "1234"
    identifier_type = "OTHER"
    resource = factory.SubFactory(DatasetFactory)
    scheme_agency = factory.SubFactory(AgencyFactory)

    class Meta:
        model = Identifier

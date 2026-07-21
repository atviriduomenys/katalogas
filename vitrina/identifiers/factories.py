import factory
from django.conf import settings
from factory.django import DjangoModelFactory

from vitrina.identifiers.models import Agency, Identifier
from vitrina.datasets.factories import DatasetFactory


class AgencyFactory(DjangoModelFactory):
    code = Agency.RISR_CODE
    name = "Registrų ir valstybės informacinių sistemų registras"
    uri = "http://registrai.lt"
    identifier_validation_type = "REGEXP"
    identifier_validation_options = r"^\d{4}$"

    class Meta:
        model = Agency

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        error_message = kwargs.pop(
            "identifier_validation_error_message",
            "Žymėjimas turi būti sudarytas iš keturių skaitmenų.",
        )
        agency = model_class(*args, **kwargs)
        for lang in settings.LANGUAGES:
            agency.set_current_language(lang[0])
            agency.identifier_validation_error_message = error_message
        agency.save()
        return agency


class IdentifierFactory(DjangoModelFactory):
    notation = "1234"
    identifier_type = "OTHER"
    resource = factory.SubFactory(DatasetFactory)
    scheme_agency = factory.SubFactory(AgencyFactory)

    class Meta:
        model = Identifier

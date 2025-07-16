from factory.django import DjangoModelFactory

from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.models import Agreement


class AgreementFactory(DjangoModelFactory):
    class Meta:
        model = Agreement
        django_get_or_create = ("project", "assigner_organization")

    status = AgreementStatuses.CREATED

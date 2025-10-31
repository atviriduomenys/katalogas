from factory import SubFactory
from factory.django import DjangoModelFactory

from vitrina.orgs.factories import OrganizationFactory
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.models import Agreement
from vitrina.users.factories import UserFactory


class AgreementFactory(DjangoModelFactory):
    class Meta:
        model = Agreement
        django_get_or_create = ("project", "assigner", "assignee", "created_by")

    status = AgreementStatuses.CREATED
    assignee = SubFactory(OrganizationFactory)
    assigner = SubFactory(OrganizationFactory)
    created_by = SubFactory(UserFactory)

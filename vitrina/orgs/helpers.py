from typing import Union

from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from vitrina.classifiers.models import AreaOfManagement
from vitrina.orgs.models import Organization


def is_org_dataset_list(request: HttpRequest):
    return request.resolver_match.url_name == 'organization-datasets'


def get_or_create_parent_org(obj: Union[AreaOfManagement, int]) -> Organization:
    if isinstance(obj, int):
        jurisdiction = AreaOfManagement.objects.get(pk=obj)
    elif isinstance(obj, AreaOfManagement):
        jurisdiction = obj
    else:
        raise ValueError(_("Neteisingas objekto tipas. Turi būti AreaOfManagement arba int"))

    parent_org: Organization = Organization.objects.filter(title=jurisdiction.name_lt).first()
    if not parent_org:
        parent_org = Organization.add_root(
            title=jurisdiction.name_lt,
            name=jurisdiction.name_lt.lower(),
            publisher=True,
            is_public=True,
            jurisdiction=jurisdiction,
        )
        parent_org.save()
    return parent_org

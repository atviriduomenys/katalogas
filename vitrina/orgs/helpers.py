from typing import Union
from slugify import slugify
from functools import partial

from django.utils.translation import gettext_lazy as _
from rest_framework.request import Request

from vitrina.classifiers.models import AreaOfManagement
from vitrina.orgs.models import Organization
from vitrina.users.models import User


def generate_dataset_prefix(organization_name: str, organization_kind: Organization.ORGANIZATION_KINDS) -> str:
    """
    Generates the dataset prefix based on the organization's kind and name.
    Returns a string like:
        - "datasets/gov/vssa/"
        - "datasets/org/test_org/"
    """
    slugify_ascii_lower = partial(slugify, lowercase=True, allow_unicode=False)
    organization_part = slugify_ascii_lower(organization_name)

    prefix = "datasets/gov" if organization_kind == "GOV" else "datasets/org"
    return f"{prefix}/{organization_part}/"


def is_org_dataset_list(request: Request):
    return request.resolver_match.url_name == "organization-datasets"


def get_or_create_parent_org(obj: Union[AreaOfManagement, int]) -> Organization:
    if isinstance(obj, int):
        jurisdiction = AreaOfManagement.objects.get(pk=obj)
    elif isinstance(obj, AreaOfManagement):
        jurisdiction = obj
    else:
        raise ValueError(_("Neteisingas objekto tipas. Turi būti AreaOfManagement arba int"))

    parent_org: Organization = Organization.objects.filter(title=jurisdiction.name_lt).first()
    if not parent_org:
        name = generate_dataset_prefix(jurisdiction.name_lt, jurisdiction.name_lt)
        parent_org = Organization.add_root(
            title=jurisdiction.name_lt,
            name=name,
            publisher=False,
            is_public=True,
            jurisdiction=jurisdiction,
        )
        parent_org.save()
    return parent_org


def get_kind_choices(user: User, organization: Organization | None = None) -> tuple[tuple[str, str]]:
    if user.is_staff or user.is_superuser:
        return Organization.ORGANIZATION_KINDS

    if organization and organization.kind == Organization.GOV:
        return tuple(kind for kind in Organization.ORGANIZATION_KINDS if kind[0] == Organization.GOV)

    return tuple(kind for kind in Organization.ORGANIZATION_KINDS if kind[0] != Organization.GOV)

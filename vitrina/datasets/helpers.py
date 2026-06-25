import re
from django.contrib.contenttypes.models import ContentType
from functools import partial

from crawleruseragents import is_crawler
from django.db.models import Q
from django.http import HttpRequest
from slugify import slugify

from vitrina.orgs.models import Organization, Representative
from vitrina.datasets.models import Dataset, Metadata


def is_child_resources_list(request: HttpRequest) -> bool:
    return request.resolver_match.url_name == "dataset-child-resources"


def is_manager_dataset_list(request: HttpRequest):
    return request.resolver_match.url_name == "manager-dataset-list"


def is_prefetch_request(request: HttpRequest) -> bool:
    sec_purpose = request.headers.get("Sec-Purpose", "").lower()
    if any(value in sec_purpose for value in ("prefetch", "prerender")):
        return True
    if request.headers.get("Purpose", "").lower() == "prefetch":
        return True
    return request.headers.get("X-Moz", "").lower() == "prefetch"


def should_count_download(request: HttpRequest) -> bool:
    if is_prefetch_request(request):
        return False
    return not is_crawler(request.headers.get("User-Agent", ""))


def generate_dataset_name(organization: Organization, dataset_title: str) -> str:
    """
    Generates a dataset name by combining a slugified organization identifier and a slugified dataset title.
    The organization identifier is determined by attempting to slugify the organization's name,
    then slug, then title (in that order), using ASCII characters and lowercase formatting.
    The dataset title is also slugified in the same manner.

    Returns:
        str: A string in the format "organization_part/dataset_part", where both parts are slugified.
    """
    slugify_ascii_lower = partial(slugify, lowercase=True, allow_unicode=False)
    dataset_part = slugify_ascii_lower(dataset_title)
    if organization.name:
        return f"{organization.name}{dataset_part}"
    organization_part = slugify_ascii_lower(organization.slug or organization.title)
    organization_kind = "gov" if organization.kind == Organization.GOV else "org"
    return f"datasets/{organization_kind}/{organization_part}/{dataset_part}"


def generate_unique_dataset_name(organization: Organization, dataset: Dataset) -> str:
    """
    Generates a unique dataset name for the given organization and dataset.
    The function creates a base name using the organization's information and the dataset's title.
    It then checks for existing dataset names in the Metadata model that start with the base name.
    If the base name is not already used, it returns the base name.
    If the base name exists, it appends an incremented numeric suffix to ensure uniqueness.
    Args:
        organization (Organization): The organization to which the dataset belongs.
        dataset (Dataset): The dataset for which the unique name is to be generated.
    Returns:
        str: A unique dataset name in format "organization_part/dataset_part"
            or "organization_part/dataset_part_index".
    """
    base_name = generate_dataset_name(organization, dataset.title)

    existing_names = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset), name__startswith=base_name
    ).values_list("name", flat=True)

    if base_name not in existing_names:
        return base_name

    pattern = re.compile(rf"^{re.escape(base_name)}_(\d+)$")

    max_index = 1
    for name in existing_names:
        match = pattern.match(name)
        if match:
            index = int(match.group(1))
            if index >= max_index:
                max_index = index + 1

    return f"{base_name}_{max_index}"


def get_name_prefixes(
    organization: Organization | None,
    dataset_instance: Dataset | None = None,
) -> tuple[str, list[str]]:
    resolved_organization = organization or (dataset_instance.organization if dataset_instance else None)
    whitelisted = getattr(resolved_organization, "whitelisted_names", [])
    main_prefix = getattr(resolved_organization, "name", "")

    if resolved_organization:
        representatives = Representative.objects.filter(
            (Q(organization=resolved_organization) | Q(user__organization=resolved_organization))
            & Q(role=Representative.OPEN_DATA_PUBLISHER)
        )
        dataset_ct = ContentType.objects.get_for_model(Dataset)
        organization_ct = ContentType.objects.get_for_model(resolved_organization)
        for rep in representatives:
            if (
                rep.content_type == dataset_ct
                and rep.content_object.organization
                and rep.content_object.organization.name
                and rep.content_object.organization.name not in whitelisted
            ):
                whitelisted.append(rep.content_object.organization.name)
            elif (
                rep.content_type == organization_ct
                and rep.content_object.name
                and rep.content_object.name not in whitelisted
            ):
                whitelisted.append(rep.content_object.name)

    return main_prefix, whitelisted


def match_name_prefix(name: str | None, all_prefixes: list[str]) -> str | None:
    if not name:
        return None
    return next((prefix for prefix in all_prefixes if prefix and name.startswith(prefix)), None)

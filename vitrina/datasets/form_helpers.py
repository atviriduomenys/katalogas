import re

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.helpers import validate_name_prefix
from vitrina.datasets.models import Dataset
from vitrina.identifiers.models import Agency
from vitrina.orgs.models import Organization, Representative
from vitrina.structure.models import Metadata


def validate_dataset_name(name: str | None, dataset: Dataset | None, organization: Organization) -> None:
    existing_metadata = dataset.metadata.first() if dataset and dataset.pk else None

    if name:
        if not name.isascii():
            raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))

        if any(ch.isupper() for ch in name):
            raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik mažosios raidės."))

        _matched, main_prefix, whitelisted = validate_name_prefix(name, organization, dataset)
        allowed_prefixes = [main_prefix] + list(whitelisted)

        representatives = Representative.objects.filter(
            (Q(organization=organization) | Q(user__organization=organization))
            & Q(role=Representative.OPEN_DATA_PUBLISHER)
        )
        dataset_ct = ContentType.objects.get_for_model(Dataset)
        organization_ct = ContentType.objects.get_for_model(organization)
        for rep in representatives:
            if (
                rep.content_type == dataset_ct
                and rep.content_object.organization
                and rep.content_object.organization.name
                and rep.content_object.organization.name not in allowed_prefixes
            ):
                allowed_prefixes.append(rep.content_object.organization.name)
                whitelisted.append(rep.content_object.organization.name)
            elif (
                rep.content_type == organization_ct
                and rep.content_object.name
                and rep.content_object.name not in allowed_prefixes
            ):
                allowed_prefixes.append(rep.content_object.name)
                whitelisted.append(rep.content_object.name)

        matched_prefix = next((prefix for prefix in allowed_prefixes if name.startswith(prefix)), None)
        if not matched_prefix:
            if whitelisted:
                message = _(
                    "Kodinis pavadinimas turi prasidėti nuo „%(expected)s“ arba vieno iš leidžiamų "
                    "kodinio pavadinimo pradžių: „%(whitelisted)s“."
                ) % {"expected": main_prefix, "whitelisted": ", ".join(whitelisted)}
            else:
                message = _("Kodinis pavadinimas turi prasidėti nuo „%(expected)s“.") % {"expected": main_prefix}

            raise ValidationError(message)
        suffix = name[len(matched_prefix) :]

        if not suffix:
            raise ValidationError(_("Po „%(prefix)s“ turi būti bent vienas simbolis.") % {"prefix": matched_prefix})

        metadata_qs = Metadata.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            name=name,
        )
        if existing_metadata:
            metadata_qs = metadata_qs.exclude(pk=existing_metadata.pk)

        if metadata_qs.exists():
            raise ValidationError(_("Duomenų rinkinys su šiuo kodiniu pavadinimu jau egzistuoja."))

    else:
        if existing_metadata and existing_metadata.name:
            raise ValidationError(
                _("Kodinis pavadinimas yra privalomas, jei duomenų rinkinys jau turi kodinį pavadinimą.")
            )

    return name


def validate_applicable_legislation(urls: list[str]) -> list[str | None]:
    validator = URLValidator()
    item_errors = []

    for url in urls:
        if not url:
            item_errors.append(None)
            continue

        try:
            validator(url)
            item_errors.append(None)
        except ValidationError as e:
            item_errors.append(f"{url}: {e.message}")

    return item_errors


def validate_identifier(identifier: str | None) -> None:
    if not identifier:
        return

    agency = get_object_or_404(Agency, code=Agency.RISR_CODE)
    is_regexp = agency.identifier_validation_type == Agency.IdentifierValidationType.REGEXP

    if is_regexp and (pattern := agency.identifier_validation_options):
        if not re.fullmatch(pattern, identifier):
            raise ValidationError(
                _("Žymėjimas turi atitikti šabloną: %(pattern)s"),
                params={"pattern": pattern},
                code="invalid_format",
            )

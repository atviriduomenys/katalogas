import re
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from vitrina.classifiers.models import Concept
from vitrina.datasets.helpers import get_name_prefixes, match_name_prefix
from vitrina.datasets.models import Dataset, Contact
from vitrina.identifiers.models import Agency
from vitrina.orgs.models import Organization
from vitrina.resources.models import Format
from vitrina.structure.models import Metadata
from vitrina.uapi.models import Agent
from vitrina.users.models import User


DATA_SERVICE_STANDARD_URI = "https://data.gov.lt/id/non-standard/DataServiceStandard"
DATASET_STANDARD_URI = "https://data.gov.lt/id/non-standard/DatasetStandard"

UAPI_CONCEPT_CODE = "UAPI"
JSON_FORMAT = "JSON"


def validate_dataset_name(name: str | None, dataset: Dataset | None, organization: Organization) -> None:
    existing_metadata = dataset.metadata.first() if dataset and dataset.pk else None

    if name:
        if not name.isascii():
            raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))

        if any(ch.isupper() for ch in name):
            raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik mažosios raidės."))

        main_prefix, whitelisted = get_name_prefixes(organization, dataset)
        matched_prefix = match_name_prefix(name, [main_prefix] + whitelisted)
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


def validate_urls(urls: list[str]) -> list[str | None]:
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

    if is_regexp and (pattern := agency.identifier_validation_options) and not re.fullmatch(pattern, identifier):
        raise ValidationError(agency.identifier_validation_error_message, code="invalid_format")


def set_default_agent_endpoint_fields(cleaned_data: dict[str, Any]) -> dict[str, Any]:
    if not cleaned_data.get("agent"):
        return cleaned_data

    error_template = _("Nepavyko rasti `{0}` pasirinkimų sąraše. Susisiekite su administracija.")

    if not cleaned_data.get("endpoint_type"):
        if not (json_format := Format.objects.filter(title=JSON_FORMAT).first()):
            raise ValidationError(error_template.format(JSON_FORMAT))
        cleaned_data["endpoint_type"] = json_format

    if not cleaned_data.get("conforms_to"):
        if not (uapi_concept := Concept.objects.filter(code=UAPI_CONCEPT_CODE).first()):
            raise ValidationError(error_template.format(UAPI_CONCEPT_CODE))
        cleaned_data["conforms_to"] = uapi_concept

    return cleaned_data


def validate_agent_endpoint_fields(
    agent: Agent | None,
    conforms_to: Concept | None,
    endpoint_url: str | None,
    endpoint_type: str | None,
    endpoint_description: str | None,
) -> list[tuple[str, str]]:
    errors = []
    if agent:
        if endpoint_url:
            errors.append(("endpoint_url", _("Pasirinkus agentą, šis laukas negali būti užpildytas.")))

        if endpoint_description:
            errors.append(("endpoint_description", _("Pasirinkus agentą, šis laukas negali būti užpildytas.")))

        if endpoint_type and endpoint_type.title != JSON_FORMAT:
            errors.append(
                ("endpoint_type", _("Pasirinkus agentą, API formatas privalo būti '{0}'").format(JSON_FORMAT))
            )

        if conforms_to and conforms_to.code != UAPI_CONCEPT_CODE:
            errors.append(("conforms_to", _("Su agentu susietos paslaugos privalo atitikti UDTS standartą.")))

    else:
        if not endpoint_url:
            errors.append(("agent", _("Pasirinkite agentą, arba nurodykite API adresą.")))
            errors.append(("endpoint_url", _("Pasirinkite agentą, arba nurodykite API adresą.")))

        if conforms_to and conforms_to.code == UAPI_CONCEPT_CODE:
            error_message = _(
                "UDTS standartą atitinkančios paslaugos privalo būti susietos su agentu. "
                "Pasirinkite agentą arba pasirinkite kitą 'Atitinka' lauko reikšmę."
            )
            errors.append(("agent", error_message))

    return errors


def get_contact_form_choices(organization: Organization) -> list[tuple[int, str]]:
    contact_choices = []
    content_type_user = ContentType.objects.get_for_model(User)
    content_type_organization = ContentType.objects.get_for_model(Organization)

    contacts = Contact.objects.filter(organization=organization, deleted__isnull=True).select_related("content_type")

    organization_contacts = []
    user_contacts = []
    other_contacts = []

    for contact in contacts:
        if contact.content_type_id == content_type_organization.id:
            organization_contacts.append(contact)
        elif contact.content_type_id == content_type_user.id:
            user_contacts.append(contact)
        else:
            other_contacts.append(contact)

    organization_ids = [c.object_id for c in organization_contacts if c.object_id]
    user_ids = [c.object_id for c in user_contacts if c.object_id]

    organizations = {
        organization.id: organization for organization in Organization.objects.filter(id__in=organization_ids)
    }
    users = {user.id: user for user in User.objects.filter(id__in=user_ids)}

    for contact in organization_contacts:
        if organization := organizations.get(contact.object_id):
            contact_choices.append((contact.id, organization.title))

    for contact in user_contacts:
        if user := users.get(contact.object_id):
            contact_choices.append((contact.id, user.get_full_name()))

    for contact in other_contacts:
        display_name = contact.contact_name or f"Contact #{contact.id}"
        contact_choices.append((contact.id, display_name))

    return contact_choices

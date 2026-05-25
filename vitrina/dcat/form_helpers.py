from django import forms

from vitrina.classifiers.models import FormFieldHelpText
from vitrina.datasets.helpers import get_name_prefixes
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization


def apply_dynamic_help_texts(form: forms.BaseForm, form_name: str) -> None:
    for entry in FormFieldHelpText.objects.filter(form_name=form_name).prefetch_related("translations"):
        if entry.field_name in form.fields and (help_text := entry.safe_translation_getter("help_text")):
            form.fields[entry.field_name].help_text = help_text


def get_available_dcat_name_prefixes(parent_dataset: Dataset | None, organization: Organization) -> list[str]:
    """
    If dataset has parent - available prefix is only parent prefix
    If dataset has no parent - available prefixes are organization prefix and all whitelisted organization prefixes
    """
    if parent_dataset and (parent_dataset_name := parent_dataset.name):
        return [parent_dataset_name]

    main_prefix, whitelisted_prefixes = get_name_prefixes(organization)

    if main_prefix:
        return [main_prefix] + whitelisted_prefixes
    return whitelisted_prefixes

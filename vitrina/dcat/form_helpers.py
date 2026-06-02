from django import forms
from django.utils.html import conditional_escape, escape
from django.utils.safestring import mark_safe

from vitrina.classifiers.models import FormFieldHelpText
from vitrina.datasets.helpers import get_name_prefixes
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization


def apply_dynamic_help_texts(form: forms.BaseForm, form_name: str) -> None:
    for entry in FormFieldHelpText.objects.filter(form_name=form_name).prefetch_related("translations"):
        if entry.field_name not in form.fields:
            continue

        field = form.fields[entry.field_name]
        help_text = entry.safe_translation_getter("help_text") or ""
        extended = entry.safe_translation_getter("extended_help_text") or ""

        if help_text:
            field.help_text = help_text

        if extended and field.help_text:
            popup_html = (
                f' <span class="wizard-help-popup" x-data="{{open:false}}" @click.outside="open=false">'
                f'<button type="button" class="wizard-help-popup-btn" @click.stop="open=!open">'
                f'<i class="fas fa-question-circle"></i></button>'
                f'<span class="wizard-help-popup-content" x-show="open" x-cloak>'
                f'{escape(extended)}</span></span>'
            )
            field.help_text = mark_safe(f"{conditional_escape(field.help_text)}{popup_html}")


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

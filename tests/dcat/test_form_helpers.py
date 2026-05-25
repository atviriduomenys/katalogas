import pytest
from django.utils.translation import override as translation_override

from vitrina.classifiers.factories import FormFieldHelpTextFactory
from vitrina.classifiers.models import FormFieldHelpText
from vitrina.datasets.factories import DatasetFactory
from vitrina.dcat.form_helpers import get_available_dcat_name_prefixes
from vitrina.dcat.forms.dataset_forms import (
    DatasetResourceForm,
    DatasetUpdateForm,
    InformationSystemResourceForm,
    InformationSystemUpdateForm,
    ServiceResourceForm,
    ServiceUpdateForm,
)
from vitrina.dcat.forms.distribution_forms import DatasetDistributionForm
from vitrina.orgs.factories import OrganizationFactory

pytestmark = pytest.mark.django_db


class TestGetAvailableDcatNamePrefixes:
    def test_returns_parent_name_when_parent_has_name(self):
        organization = OrganizationFactory()
        parent = DatasetFactory(metadata="some/parent")

        result = get_available_dcat_name_prefixes(parent, organization)

        assert result == ["some/parent"]

    def test_returns_org_prefix_and_whitelist_when_parent_has_no_name(self):
        organization = OrganizationFactory()
        parent = DatasetFactory(metadata=False)

        result = get_available_dcat_name_prefixes(parent, organization)

        assert result == [organization.name, "datasets/gov/ivpk/"]

    def test_returns_org_prefix_and_whitelist_when_no_parent(self):
        organization = OrganizationFactory()

        result = get_available_dcat_name_prefixes(None, organization)

        assert result == [organization.name, "datasets/gov/ivpk/"]

    def test_returns_whitelist_only_when_org_has_no_name(self):
        organization = OrganizationFactory(name="")

        result = get_available_dcat_name_prefixes(None, organization)

        assert result == ["datasets/gov/ivpk/"]

    def test_returns_empty_when_org_has_no_name_nor_whitelist(self):
        organization = OrganizationFactory(name="")
        organization.whitelisted_code_names.all().delete()

        result = get_available_dcat_name_prefixes(None, organization)

        assert result == []


class TestApplyDynamicHelpTexts:
    def test_default_help_text_preserved_when_no_entry_exists(self):
        organization = OrganizationFactory()

        form = InformationSystemResourceForm(organization=organization, url_parent=None)

        assert form.fields["name"].help_text != ""

    def test_dynamic_help_text_overrides_default(self):
        organization = OrganizationFactory()
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_INFORMATION_SYSTEM,
            field_name="name",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = InformationSystemResourceForm(organization=organization, url_parent=None)

        assert form.fields["name"].help_text == "Dinaminis tekstas"

    def test_empty_dynamic_help_text_keeps_default(self):
        organization = OrganizationFactory()
        default_help_text = (
            InformationSystemResourceForm(organization=organization, url_parent=None).fields["name"].help_text
        )
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_INFORMATION_SYSTEM,
            field_name="name",
            help_text_lt="",
        )

        with translation_override("lt"):
            form = InformationSystemResourceForm(organization=organization, url_parent=None)

        assert form.fields["name"].help_text == default_help_text

    def test_dynamic_help_text_respects_active_language(self):
        organization = OrganizationFactory()
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_INFORMATION_SYSTEM,
            field_name="name",
            help_text_lt="LT tekstas",
            help_text_en="EN text",
        )

        with translation_override("lt"):
            form_lt = InformationSystemResourceForm(organization=organization, url_parent=None)
        with translation_override("en"):
            form_en = InformationSystemResourceForm(organization=organization, url_parent=None)

        assert form_lt.fields["name"].help_text == "LT tekstas"
        assert form_en.fields["name"].help_text == "EN text"

    def test_unknown_field_name_does_not_raise(self):
        organization = OrganizationFactory()
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_INFORMATION_SYSTEM,
            field_name="nonexistent_field",
            help_text_lt="Tekstas",
        )

        form = InformationSystemResourceForm(organization=organization, url_parent=None)

        assert "nonexistent_field" not in form.fields

    def test_information_system_update_form_inherits_dynamic_help_text(self):
        organization = OrganizationFactory()
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_INFORMATION_SYSTEM,
            field_name="name",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = InformationSystemUpdateForm(organization=organization, url_parent=None)

        assert form.fields["name"].help_text == "Dinaminis tekstas"

    def test_service_form_applies_dynamic_help_text(self):
        organization = OrganizationFactory()
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_SERVICE,
            field_name="endpoint_url",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = ServiceResourceForm(organization=organization, url_parent=None)

        assert form.fields["endpoint_url"].help_text == "Dinaminis tekstas"

    def test_service_update_form_inherits_dynamic_help_text(self):
        organization = OrganizationFactory()
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_SERVICE,
            field_name="endpoint_url",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = ServiceUpdateForm(organization=organization, url_parent=None)

        assert form.fields["endpoint_url"].help_text == "Dinaminis tekstas"

    def test_dataset_form_applies_dynamic_help_text(self):
        organization = OrganizationFactory()
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_DATASET,
            field_name="documentation",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = DatasetResourceForm(organization=organization, url_parent=None)

        assert form.fields["documentation"].help_text == "Dinaminis tekstas"

    def test_dataset_update_form_inherits_dynamic_help_text(self):
        organization = OrganizationFactory()
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_DATASET,
            field_name="documentation",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = DatasetUpdateForm(organization=organization, url_parent=None)

        assert form.fields["documentation"].help_text == "Dinaminis tekstas"

    def test_distribution_form_applies_dynamic_help_text(self):
        dataset = DatasetFactory()
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_DISTRIBUTION,
            field_name="documentation",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = DatasetDistributionForm(dataset=dataset)

        assert form.fields["documentation"].help_text == "Dinaminis tekstas"

    def test_distribution_form_empty_dynamic_help_text_keeps_default(self):
        dataset = DatasetFactory()
        default_help_text = DatasetDistributionForm(dataset=dataset).fields["documentation"].help_text
        FormFieldHelpTextFactory(
            form_name=FormFieldHelpText.DCAT_DISTRIBUTION,
            field_name="documentation",
            help_text_lt="",
        )

        with translation_override("lt"):
            form = DatasetDistributionForm(dataset=dataset)

        assert form.fields["documentation"].help_text == default_help_text

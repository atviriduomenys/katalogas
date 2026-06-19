import pytest
from django.utils.translation import override as translation_override

from vitrina.classifiers.factories import FormFieldTextFactory
from vitrina.classifiers.models import FormFieldText
from vitrina.dcat.forms.contact_forms import DcatContactForm, DcatContactUpdateForm
from vitrina.datasets.factories import ContactFactory
from vitrina.orgs.factories import OrganizationFactory

pytestmark = pytest.mark.django_db


class TestDcatContactForm:
    def test_contact_name_is_required(self):
        form = DcatContactForm()
        assert form.fields["contact_name"].required is True

    def test_email_is_required(self):
        form = DcatContactForm()
        assert form.fields["email"].required is True

    def test_contact_name_label(self):
        form = DcatContactForm()
        assert form.fields["contact_name"].label == "Palaikomas produktas ar paslauga"

    def test_phone_validator_attached(self):
        form = DcatContactForm(
            data={
                "contact_name": "Test",
                "phone": "invalid-phone",
            }
        )
        form.is_valid()
        assert "phone" in form.errors

    def test_phone_valid(self):
        form = DcatContactForm(
            data={
                "contact_name": "Test",
                "phone": "+37061234567",
            }
        )
        form.is_valid()
        assert "phone" not in form.errors

    def test_phone_placeholder_set(self):
        form = DcatContactForm()
        assert form.fields["phone"].widget.attrs["placeholder"] == "Formatas 0... arba +370..."

    def test_dynamic_help_text_applied(self):
        FormFieldTextFactory(
            form_name=FormFieldText.DCAT_CONTACT,
            field_name="served_area",
            help_text_lt="Dinaminis tekstas",
        )

        with translation_override("lt"):
            form = DcatContactForm()

        assert form.fields["served_area"].help_text == "Dinaminis tekstas"

    def test_helper_form_id(self):
        form = DcatContactForm()
        assert form.helper.form_id == "contact-form"


class TestDcatContactUpdateForm:
    def test_contact_name_is_required(self):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind="service")
        form = DcatContactUpdateForm(instance=contact)
        assert form.fields["contact_name"].required is True

    def test_email_is_required(self):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind="service")
        form = DcatContactUpdateForm(instance=contact)
        assert form.fields["email"].required is True

    def test_phone_validator_attached(self):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind="service")
        form = DcatContactUpdateForm(
            data={
                "contact_name": "Test",
                "phone": "invalid-phone",
            },
            instance=contact,
        )
        form.is_valid()
        assert "phone" in form.errors

    def test_dynamic_help_text_applied(self):
        FormFieldTextFactory(
            form_name=FormFieldText.DCAT_CONTACT,
            field_name="work_hours",
            help_text_lt="Dinaminis darbo valandų tekstas",
        )
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind="service")

        with translation_override("lt"):
            form = DcatContactUpdateForm(instance=contact)

        assert form.fields["work_hours"].help_text == "Dinaminis darbo valandų tekstas"

    def test_helper_form_id(self):
        org = OrganizationFactory()
        contact = ContactFactory(organization=org, kind="service")
        form = DcatContactUpdateForm(instance=contact)
        assert form.helper.form_id == "contact-form"

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from vitrina.classifiers.models import FormFieldText
from vitrina.dcat.form_helpers import apply_dynamic_help_texts
from vitrina.datasets.models import Contact
from vitrina.validators import phone_validator


class BaseDcatContactForm(ModelForm):
    class Meta:
        model = Contact
        fields = (
            "served_area",
            "languages",
            "contact_options",
            "contact_type",
            "email",
            "work_hours",
            "contact_name",
            "phone",
        )
        widgets = {
            "languages": Select2MultipleWidget,
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["contact_name"].required = True
        self.fields["contact_name"].label = _("Palaikomas produktas ar paslauga")
        self.fields["contact_name"].help_text = _(
            "Produktas arba paslauga, su kuria yra susijęs šis palaikymo kontaktinis taškas (pvz., produkto "
            "palaikymas tam tikrai produktų linijai). Tai gali būti konkretus produktas arba produktų linija "
            "arba bendra produktų ar paslaugų kategorija"
        )
        self.fields["phone"].validators.append(phone_validator)
        self.fields["phone"].widget.attrs["placeholder"] = _("Formatas 0... arba +370...")

        apply_dynamic_help_texts(self, FormFieldText.DCAT_CONTACT)

    @staticmethod
    def _build_helper(submit_label: str) -> FormHelper:
        helper = FormHelper()
        helper.attrs["novalidate"] = ""
        helper.form_id = "contact-form"
        helper.layout = Layout(
            Field("served_area"),
            Field("languages"),
            Field("contact_options"),
            Field("contact_type"),
            Field("email"),
            Field("work_hours"),
            Field("contact_name"),
            Field("phone"),
            Submit("submit", submit_label, css_class="button is-primary"),
        )

        return helper


class DcatContactForm(BaseDcatContactForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.helper = self._build_helper(submit_label=_("Sukurti"))


class DcatContactUpdateForm(BaseDcatContactForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.helper = self._build_helper(submit_label=_("Redaguoti"))

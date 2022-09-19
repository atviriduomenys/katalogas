from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ModelForm, EmailField, ChoiceField
from django.utils.translation import gettext_lazy as _

from vitrina.orgs.models import Representative


class RepresentativeUpdateForm(ModelForm):
    role = ChoiceField(label=_("Rolė"), choices=Representative.ROLES)

    class Meta:
        model = Representative
        fields = ('role',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "representative-form"
        self.helper.layout = Layout(
            Div(Div(Field('role', css_class="select is-fullwidth"),
                    css_class="control is-expanded"), css_class="field"),
            Submit('submit', _("Redaguoti"), css_class='button is-primary')
        )

    def clean_role(self):
        role = self.cleaned_data.get('role')
        organization = self.instance.organization
        if role != Representative.COORDINATOR and not Representative.objects.filter(
                Q(organization=organization) & Q(role=Representative.COORDINATOR)).\
                exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("Negalima panaikinti koordinatoriaus rolės naudotojui, "
                                    "jei tai yra vienintelis koordinatoriaus rolės atstovas."))
        return role


class RepresentativeCreateForm(ModelForm):
    email = EmailField(label=_("El. paštas"))
    role = ChoiceField(label=_("Rolė"), choices=Representative.ROLES)

    class Meta:
        model = Representative
        fields = ('email', 'role',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "representative-form"
        self.helper.layout = Layout(
            Div(Div(Field('email', css_class="input", placeholder=_("El. paštas"), ),
                    css_class="control"), css_class="field"),
            Div(Div(Field('role', css_class="select is-fullwidth"),
                    css_class="control is-expanded"), css_class="field"),
            Submit('submit', _("Sukurti"), css_class='button is-primary')
        )


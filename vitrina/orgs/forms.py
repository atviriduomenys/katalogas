from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ModelForm, EmailField, ChoiceField
from django.utils.translation import gettext_lazy as _

from vitrina.orgs.models import Representative
from vitrina.helpers import buttons, submit


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
            Field('role'),
            Submit('submit', _("Redaguoti"), css_class='button is-primary'),
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

    def __init__(self, organization_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization_id = organization_id
        self.helper = FormHelper()
        self.helper.form_id = "representative-form"
        self.helper.layout = Layout(
            Field('email'),
            Field('role'),
            Submit('submit', _("Sukurti"), css_class='button is-primary'),
        )

    def clean(self):
        email = self.cleaned_data.get('email')
        if Representative.objects.filter(organization_id=self.organization_id, email=email).exists():
            self.add_error('email', _("Organizacijos narys su šiuo el. pašto adresu jau egzistuoja "))
        return self.cleaned_data

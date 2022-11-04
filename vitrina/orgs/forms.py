from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import ModelForm, EmailField, ChoiceField, BooleanField, CharField, TextInput, HiddenInput
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit

from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import get_coordinators_count


class RepresentativeUpdateForm(ModelForm):
    role = ChoiceField(label=_("Rolė"), choices=Representative.ROLES)
    has_api_access = BooleanField(label=_("Suteikti API prieigą"), required=False)
    api_key = CharField(label=_("API raktas"), required=False, widget=TextInput(attrs={'readonly': True}))
    regenerate_api_key = BooleanField(label=_("Pergeneruoti raktą"), required=False)

    object_model = Organization

    class Meta:
        model = Representative
        fields = ('role', 'has_api_access', 'api_key', 'regenerate_api_key',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "representative-form"
        self.helper.layout = Layout(
            Field('role'),
            Field('has_api_access'),
            Field('regenerate_api_key'),
            Field('api_key', css_class="is-borderless"),
            Submit('submit', _("Redaguoti"), css_class='button is-primary'),
        )
        if self.instance.has_api_access and self.instance.apikey_set.exists():
            self.initial['api_key'] = self.instance.apikey_set.first().api_key
        else:
            self.fields['api_key'].widget = HiddenInput()

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if (
            self.instance.role == Representative.COORDINATOR and
            role != Representative.COORDINATOR and
            get_coordinators_count(
                self.object_model,
                self.instance.object_id,
            ) == 1
        ):
            raise ValidationError(_(
                "Negalima panaikinti koordinatoriaus rolės naudotojui, "
                "jei tai yra vienintelis koordinatoriaus rolės atstovas."
            ))
        return role


class RepresentativeCreateForm(ModelForm):
    email = EmailField(label=_("El. paštas"))
    role = ChoiceField(label=_("Rolė"), choices=Representative.ROLES)
    has_api_access = BooleanField(label=_("Suteikti API prieigą"), required=False)

    object_model = Organization
    object_id: int

    class Meta:
        model = Representative
        fields = ('email', 'role', 'has_api_access')

    def __init__(self, object_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_id = object_id
        self.helper = FormHelper()
        self.helper.form_id = "representative-form"
        self.helper.layout = Layout(
            Field('email'),
            Field('role'),
            Field('has_api_access'),
            Submit('submit', _("Sukurti"), css_class='button is-primary'),
        )

    def clean(self):
        email = self.cleaned_data.get('email')
        content_type = ContentType.objects.get_for_model(self.object_model)
        if (
            Representative.objects.
            filter(
                content_type=content_type,
                object_id=self.object_id,
                email=email
            ).
            exists()
        ):
            self.add_error('email', _(
                "Narys su šiuo el. pašto adresu jau egzistuoja."
            ))
        return self.cleaned_data

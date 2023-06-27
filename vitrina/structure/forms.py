import markdown
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from lark import ParseError

from vitrina.structure import spyna
from vitrina.structure.models import EnumItem, Metadata


class EnumForm(forms.ModelForm):
    value = forms.CharField(label=_("Reikšmė"))
    source = forms.CharField(label=_("Reikšmė šaltinyje"), required=False)
    access = forms.ChoiceField(label=_("Prieigos lygmuo"), choices=Metadata.ACCESS_TYPES, required=False)
    title = forms.CharField(label=_("Pavadinimas"), required=False)
    description = forms.CharField(label=_("Aprašymas"), widget=forms.Textarea(attrs={'rows': 8}), required=False)

    class Meta:
        model = EnumItem
        fields = ('value', 'source', 'access', 'title', 'description')

    def __init__(self, prop=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.prop = prop
        self.helper = FormHelper()
        self.helper.form_id = "enum-form"
        self.helper.layout = Layout(
            Field('value'),
            Field('source'),
            Field('access'),
            Field('title'),
            Field('description'),
            Submit('submit', _("Redaguoti") if instance else _("Sukurti"), css_class='button is-primary'),
        )

        if instance and instance.metadata.first():
            metadata = instance.metadata.first()
            if self.prop.metadata.first() and self.prop.metadata.first().type == 'string':
                value = metadata.prepare.replace('"', '')
            else:
                value = metadata.prepare
            self.initial['value'] = value
            self.initial['source'] = metadata.source
            self.initial['access'] = metadata.access
            self.initial['title'] = metadata.title
            self.initial['description'] = metadata.description

    def clean_value(self):
        value = self.cleaned_data.get('value')
        if value:
            if metadata := self.prop.metadata.first():
                if metadata.type == 'integer':
                    try:
                        int(value)
                    except ValueError:
                        raise ValidationError(_("Reikšmė turi būti integer tipo."))
            try:
                spyna.parse(value)
            except ParseError as e:
                raise ValidationError(e)
        return value

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            md = markdown.Markdown()
            try:
                md.convert(description)
            except:
                raise ValidationError(_("Aprašymas neatitinka Markdown formato."))
        return description

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from vitrina.messages.models import Subscription

from django.utils.translation import gettext_lazy as _


class SubscriptionForm(ModelForm):
    class Meta:
        model = Subscription
        fields = (
            'email_subscribed',
            'dataset_update_sub',
            'request_update_sub',
            'dataset_comments_sub',
            'request_comments_sub',
            'project_update_sub',
            'project_comments_sub'
        )

    def __init__(self, *args, **kwargs):
        self.ct = kwargs.pop('ct', None)

        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "subscribe-form"

        self.fields['dataset_update_sub'].widget.attrs['class'] = 'toggleable'
        self.fields['request_update_sub'].widget.attrs['class'] = 'toggleable'
        self.fields['project_update_sub'].widget.attrs['class'] = 'toggleable'

        permanent_fields = [
            Field('email_subscribed'),
        ]

        dynamic_fields = []

        if self.ct.model.upper() == Subscription.ORGANIZATION:
            dynamic_fields.extend([
                Field('dataset_update_sub'),
                Field('dataset_comments_sub'),
                Field('request_update_sub'),
                Field('request_comments_sub'),
            ])

        if self.ct.model.upper() == Subscription.DATASET:
            dynamic_fields.extend([
                Field('dataset_update_sub'),
                Field('dataset_comments_sub'),
            ])

        if self.ct.model.upper() == Subscription.REQUEST:
            dynamic_fields.extend([
                Field('request_update_sub'),
                Field('request_comments_sub'),
            ])

        if self.ct.model.upper() == Subscription.PROJECT:
            dynamic_fields.extend([
                Field('project_update_sub'),
                Field('project_comments_sub'),
            ])

        dynamic_fields.extend([Submit('submit', _("Prenumeruoti"), css_class='button is-primary')])
        self.helper.layout = Layout(*permanent_fields, *dynamic_fields)

    def clean(self):
        dataset_update_sub = self.cleaned_data.get('dataset_update_sub')
        request_update_sub = self.cleaned_data.get('request_update_sub')
        project_update_sub = self.cleaned_data.get('project_update_sub')

        dataset_comments_sub = self.cleaned_data.get('dataset_comments_sub')
        request_comments_sub = self.cleaned_data.get('request_comments_sub')
        project_comments_sub = self.cleaned_data.get('project_comments_sub')

        if dataset_comments_sub and not dataset_update_sub:
            raise ValidationError(_("Jei norima prenumeruoti duomenų rinkinių komentarus,"
                                    " būtina prenumeruoti ir duomenų rinkinius"))

        if request_comments_sub and not request_update_sub:
            raise ValidationError(_("Jei norima prenumeruoti poreikių komentarus,"
                                    " būtina prenumeruoti ir poreikius"))

        if project_comments_sub and not project_update_sub:
            raise ValidationError(_("Jei norima prenumeruoti projektų komentarus,"
                                    " būtina prenumeruoti ir projektus"))

        if self.ct.model.upper() == Subscription.DATASET and (request_update_sub or project_update_sub):
            raise ValidationError(_("Ši forma skirta tik duomenų rinkinių prenumeratai, kitas prenumeratas galite gauti"
                                    "kitose atitinkamose formose"))

        if self.ct.model.upper() == Subscription.REQUEST and project_update_sub:
            raise ValidationError(_("Jei norite prenumeruoti projektus,"
                                    " tą galite padaryti iš atitinkamo projekto puslapio"))

        if self.ct.model.upper() == Subscription.PROJECT and (dataset_update_sub or request_update_sub):
            raise ValidationError(_("Ši forma skirta tik projektų prenumeratai, kitas prenumeratas galite gauti "
                                    "kitose atitinkamose formose"))

        if not dataset_update_sub and not request_update_sub and not project_update_sub:
            raise ValidationError(_("Būtina pasirinkti bent vieną prenumeratos tipą"))

        return self.cleaned_data

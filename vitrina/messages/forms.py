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
            'sub_type',
            'email_subscribed',
            'dataset_update_sub',
            'request_update_sub',
            'dataset_comments_sub',
            'request_comments_sub',
        )

    def __init__(self, *args, **kwargs):
        ct = kwargs.pop('ct', None)

        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "subscribe-form"

        self.fields['dataset_update_sub'].widget.attrs['class'] = 'toggleable'
        self.fields['request_update_sub'].widget.attrs['class'] = 'toggleable'

        permanent_fields = [
            Field('sub_type'),
            Field('email_subscribed'),
        ]

        dynamic_fields = []

        if ct:
            self.fields['sub_type'].initial = ct.model.upper()
            self.fields['sub_type'].widget.attrs['disabled'] = 'disabled'

        if ct.model.upper() == Subscription.ORGANIZATION:
            dynamic_fields.extend([
                Field('dataset_update_sub'),
                Field('dataset_comments_sub'),
                Field('request_update_sub'),
                Field('request_comments_sub'),
            ])
        if ct.model.upper() == Subscription.DATASET:
            dynamic_fields.extend([
                Field('dataset_update_sub'),
                Field('dataset_comments_sub'),
            ])
        if ct.model.upper() == Subscription.REQUEST:
            dynamic_fields.extend([
                Field('request_update_sub'),
                Field('request_comments_sub'),
            ])
        dynamic_fields.extend([Submit('submit', _("Prenumeruoti"), css_class='button is-primary')])
        self.helper.layout = Layout(*permanent_fields, *dynamic_fields)

    def clean_sub_type(self):
        return self.cleaned_data.get('sub_type')

    def clean(self):
        cleaned_data = super().clean()

        dataset_update_sub = cleaned_data.get('dataset_update_sub')
        request_update_sub = cleaned_data.get('request_update_sub')

        dataset_comments_sub = cleaned_data.get('dataset_comments_sub')
        request_comments_sub = cleaned_data.get('request_comments_sub')

        if dataset_comments_sub and not dataset_update_sub:
            raise ValidationError(_("Jei norima prenumeruoti duomenų rinkinių komentarus,"
                                    " būtina prenumeruoti ir duomenų rinkinius"))

        if request_comments_sub and not request_update_sub:
            raise ValidationError(_("Jei norima prenumeruoti poreikių komentarus,"
                                    " būtina prenumeruoti ir poreikius"))


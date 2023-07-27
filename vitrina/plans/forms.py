from django import forms

from vitrina.plans.models import Plan
from django.utils.translation import gettext_lazy as _


class PlanAdminForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = '__all__'

    def clean(self):
        provider = self.cleaned_data.get('provider')
        provider_title = self.cleaned_data.get('provider_title')

        if provider and provider_title:
            self.add_error(
                'provider',
                _('Turi būti nurodytas arba paslaugų teikėjas, arba paslaugų teikėjo pavadinimas, bet ne abu.')
            )
        elif not provider and not provider_title:
            self.add_error(
                'provider',
                _('Turi būti nurodytas paslaugų teikėjas arba paslaugų teikėjo pavadinimas.')
            )

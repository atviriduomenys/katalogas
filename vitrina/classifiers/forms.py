from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

from vitrina.classifiers.models import AreaOfManagement
from vitrina.orgs.models import Organization


class AreaOfManagementAdminForm(forms.ModelForm):
    organizations = forms.ModelMultipleChoiceField(
        queryset=Organization.objects.all(),
        widget=FilteredSelectMultiple("Organizacijos", is_stacked=False),
        required=False
    )

    class Meta:
        model = AreaOfManagement
        fields = '__all__'
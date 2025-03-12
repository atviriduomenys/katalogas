from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

from vitrina.classifiers.models import AreaOfManagement
from vitrina.orgs.models import Organization


class AreaOfManagementAdminForm(forms.ModelForm):
    organizations = forms.ModelMultipleChoiceField(
        queryset=Organization.objects.all(),
        widget=FilteredSelectMultiple("Organizacijos", is_stacked=False),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["organizations"].initial = self.instance.organization_set.all()

    class Meta:
        model = AreaOfManagement
        fields = "__all__"

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from vitrina.uapi.models import Agent


class AgentForm(ModelForm):
    class Meta:
        model = Agent
        fields = [
            "title",
            "is_enabled",
            "is_open_data_published",
            "open_data_publish_url",
            "object_type",
            "service",
            "environment",
            "auth_server_url",
            "api_gate_server_url",
            "agent_address",
        ]

    def __init__(self, *args, **kwargs) -> None:
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

        self.fields["service"].queryset = self.fields["service"].queryset.filter(
            organization=self.organization,
            service=True,
        )
        self.fields["agent_address"].required = True

        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.layout = Layout(
            Field("title"),
            Field("object_type"),
            Field("service"),
            Field("environment"),
            Field("agent_address"),
            Field("auth_server_url"),
            Field("api_gate_server_url"),
            Field("is_enabled"),
            Field("is_open_data_published"),
            Field("open_data_publish_url"),
            Submit(
                "submit",
                _("Sukurti") if self.instance._state.adding else _("Redaguoti"),
                css_class="button is-primary",
            ),
        )

    def clean(self) -> None:
        cleaned_data = super().clean()
        if cleaned_data.get("is_open_data_published") and not cleaned_data.get("open_data_publish_url"):
            self.add_error(
                "open_data_publish_url",
                _('Šis laukas yra privalomas, jei nustatytas požymis "Atviri duomenys publikuojami Saugykloje".'),
            )

        if (title := cleaned_data.get("title")) and self.organization:
            existing_agent = (
                Agent.objects.filter(
                    organization=self.organization,
                    codename=Agent.get_codename(title),
                    is_archived=False,
                )
                .exclude(
                    pk=self.instance.pk,
                )
                .exists()
            )
            if existing_agent:
                self.add_error(
                    "title",
                    _("Agentas su tokiu pavadinimu jau registruotas organizacijoje, pasirinkite kitą pavadinimą."),
                )

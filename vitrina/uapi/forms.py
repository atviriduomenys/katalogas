from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from vitrina.uapi.models import Agent, AgentEnvironment
from vitrina.uapi import Environment


class AgentForm(ModelForm):
    class Meta:
        model = Agent
        fields = [
            "title",
            "object_type",
        ]

    def __init__(self, *args, **kwargs) -> None:
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.layout = Layout(
            Field("title"),
            Field("object_type"),
            Submit(
                "submit",
                _("Sukurti") if self.instance._state.adding else _("Redaguoti"),
                css_class="button is-primary",
            ),
        )

    def clean(self) -> None:
        cleaned_data = super().clean()

        if (title := cleaned_data.get("title")) and self.organization:
            existing_agent = (
                Agent.not_archived.filter(
                    organization=self.organization,
                    codename=Agent.get_codename(title),
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


class AgentEnvironmentForm(ModelForm):
    class Meta:
        model = AgentEnvironment
        fields = [
            "is_open_data_published",
            "open_data_publish_url",
            "environment",
            "auth_server_url",
            "api_gate_server_url",
            "agent_address",
            "is_enabled",
        ]

    def __init__(self, agent: Agent, *args, **kwargs) -> None:
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = "agent-env-form"
        self.helper.attrs["novalidate"] = ""
        available_environments = agent.missing_environments
        if not self.instance._state.adding and self.instance.environment not in available_environments:
            available_environments.append(Environment(self.instance.environment))
        self.fields["environment"].choices = [(env.value, env.label) for env in available_environments]
        self.helper.layout = Layout(
            Field("environment"),
            Field("agent_address"),
            Field("auth_server_url"),
            Field("api_gate_server_url"),
            Field("is_open_data_published"),
            Field("open_data_publish_url"),
            Field("is_enabled"),
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

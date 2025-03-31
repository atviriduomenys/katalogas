import yaml

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.views.generic import CreateView
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from vitrina.api_example.forms import YamlFileUploadForm
from vitrina.orgs.services import has_perm, Action
from ..orgs.models import Representative
from ..structure.views import DatasetStructureMixin

from .models import ApiExample


class YamlFileImportView(
    DatasetStructureMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = ApiExample
    form_class = YamlFileUploadForm
    template_name = "base_form.html"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "current_title": _("Pavyzdinio failo importas"),
            "parent_links": {
                reverse("home"): _("Pradžia"),
                reverse("dataset-list"): _("Duomenų rinkiniai"),
                reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
            },
            "parent_title": self.dataset.title,
            "parent_url": self.dataset.get_absolute_url(),
            "tabs": "vitrina/datasets/tabs.html",
            "can_view_members": has_perm(
                self.request.user,
                Action.VIEW,
                Representative,
                self.dataset,
            ),
        }

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.CREATE,
            ApiExample,
        )

    def form_valid(self, form):
        file_data = form.cleaned_data["yaml_file"]
        try:
            yaml.safe_load(file_data)
        except yaml.YAMLError:
            raise ValidationError("Neteisingas YAML failas.")

        except ValidationError as e:
            raise e
        file_instance = ApiExample(yaml_file=file_data, dataset=self.dataset)
        file_instance.save()

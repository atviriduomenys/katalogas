import yaml

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import CreateView

from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.api_example.forms import YamlFileUploadForm
from vitrina.orgs.services import has_perm, Action

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

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.CREATE,
            ApiExample,
        )

    def form_valid(self, form):
        file_data = form.cleaned_data["yaml_file"]
        file_instance = ApiExample(yaml_file=file_data, dataset=self.dataset)
        file_instance.save()

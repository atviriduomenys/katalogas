import hashlib
import subprocess
import tempfile
from io import StringIO

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.files.base import ContentFile
from django.shortcuts import redirect
from django.views.generic import CreateView

import yaml

from vitrina.api_example.forms import YamlFileUploadForm
from vitrina.orgs.services import has_perm, Action
from vitrina.structure.services import export_dataset_structure
from vitrina.structure.views import DatasetStructureMixin

from ..orgs.models import Representative
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

    def get(self, request, *args, **kwargs):
        if not settings.DEBUG:
            redirect_url = reverse(
                "model-data", args=[self.dataset.pk, self.models[0].name]
            )

            return redirect(redirect_url)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        form = YamlFileUploadForm(dataset=self.dataset)
        return {
            **super().get_context_data(**kwargs),
            "current_title": _("Pavyzdinio failo įkėlimas"),
            "parent_links": {
                reverse("home"): _("Pradžia"),
                reverse("dataset-list"): _("Duomenų rinkiniai"),
                reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
                reverse("model-data", args=[self.dataset.pk, self.models[0].name]): _(
                    f"{self.models[0].name}"
                ),
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
            "code_mirror": True,
            "form": form,
        }

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.CREATE,
            ApiExample,
        )

    def get_success_url(self):
        return reverse(
            "model-data-table",
            kwargs={"pk": self.dataset.pk, "model": self.dataset.get_absolute_url()},
        )

    def form_valid(self, form):
        yaml_content = form.cleaned_data["code_field"]
        if not self.is_valid_yaml(yaml_content)[0]:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    alert=True,
                    alert_content=f"{self.is_valid_yaml(yaml_content)[1]}",
                )
            )

        file_data_hash = self.generate_file_hash(yaml_content)
        result = self.handle_existing_file(file_data_hash, yaml_content, form)
        if result:
            return self.render_to_response(
                self.get_context_data(
                    form=form, success=True, success_content="Atnaujinimas sėkmingas."
                )
            )
        elif result is False:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    alert=True,
                    alert_content="Jokių atnaujinimų nepastebėta.",
                )
            )
        else:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    success=True,
                    success_content="Naujas pavyzdinis failas sėkmingai pridėtas.",
                )
            )

    def is_valid_yaml(self, yaml_content):
        try:
            yaml_content = yaml.safe_load_all(yaml_content)
            return self.get_manifest_and_run_spinta(yaml_content)
        except yaml.YAMLError:
            return False, "Neteisingas YAML failas."
        except subprocess.SubprocessError as e:
            lines = e.stderr.strip().split("\n")
            last_n = lines[-10:]
            return False, "\n".join(last_n).replace(",", "/n")

    def generate_file_hash(self, file_content):
        return hashlib.sha256(file_content.encode("utf-8")).hexdigest()

    def handle_existing_file(self, file_data_hash, yaml_content, form):
        current_example = ApiExample.objects.filter(dataset=self.dataset).first()

        if current_example:
            existing_file_hash = self.get_existing_file_hash(current_example)
            if file_data_hash != existing_file_hash:
                return self.update_example_file(current_example, yaml_content)
            else:
                return False
        else:
            return self.create_new_example(yaml_content)

    def get_existing_file_hash(self, example):
        if example.yaml_file:
            if not example.yaml_file.closed:
                example.yaml_file.open("rb")
            existing_file_hash = hashlib.sha256(example.yaml_file.read()).hexdigest()
            example.yaml_file.close()
            return existing_file_hash
        return None

    def update_example_file(self, example, yaml_content):
        file_content = ContentFile(yaml_content.encode("utf-8"), name="example.yaml")
        example.yaml_file.save("example.yaml", file_content, save=True)
        return True

    def create_new_example(self, yaml_content):
        new_example = ApiExample(dataset=self.dataset)
        file_content = ContentFile(yaml_content.encode("utf-8"), name="example.yaml")
        new_example.yaml_file.save("example.yaml", file_content, save=False)
        new_example.save()
        return True

    def collect_and_save_to_temp_file(self) -> str:
        generator = export_dataset_structure(self.dataset)

        string_io = StringIO()

        for chunk in generator:
            string_io.write(chunk)

        with tempfile.NamedTemporaryFile(
            delete=False,
            mode="w",
            newline="",
            encoding="utf-8",
            prefix="manifest",
            suffix=".csv",
        ) as temp_file:
            temp_file.write(string_io.getvalue())

            temp_file_path = temp_file.name

        return temp_file_path

    def get_manifest_and_run_spinta(self, yaml_data):
        temp_file_path = self.collect_and_save_to_temp_file()
        with tempfile.NamedTemporaryFile(
            delete=False,
            mode="w",
            newline="",
            encoding="utf-8",
            prefix="example",
            suffix=".yaml",
        ) as temp_file_yaml:
            yaml.dump_all(yaml_data, temp_file_yaml)
        temp_file_path_yaml = temp_file_yaml.name
        return self.run_spinta_getall(temp_file_path, temp_file_path_yaml)

    def run_spinta_getall(self, manifest_path, yaml_path):
        result = subprocess.run(
            [
                "spinta",
                "getall",
                f"{manifest_path}",
                f"{yaml_path}",
                f"{self.models[0]}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

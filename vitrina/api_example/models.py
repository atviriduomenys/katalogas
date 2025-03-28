from django.db import models
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import Dataset


class ApiExample(models.Model):
    dataset = models.OneToOneField(
        Dataset, on_delete=models.CASCADE, related_name="examples"
    )
    yaml_file = models.FileField(
        upload_to="data/files/yaml_examples",
        verbose_name=_("Pridėtas YAML duomenų pavyzdys"),
    )

    class Meta:
        db_table = "api_example"

    def __str__(self):
        return f"API example for {self.dataset=}"

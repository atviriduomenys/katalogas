from django.db import models

from vitrina.datasets.models import Dataset


class ApiExample(models.Model):
    dataset = models.OneToOneField(Dataset, on_delete=models.CASCADE, related_name='examples')
    file_data = models.TextField(help_text="getAll yaml example with list of objects")

    class Meta:
        db_table = "api_example"

    def __str__(self):
        return f"API example for {self.dataset=}"


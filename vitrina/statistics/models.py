from django.db import models

class ModelDownloadStats(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    model_format = models.CharField(max_length=255, blank=True, null=True)
    model_requests = models.BigIntegerField(blank=True, null=True)
    model_objects = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'model_download_statistic'


class DatasetStats(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    dataset_id = models.IntegerField(blank=False, null=False)
    object_count = models.IntegerField(blank=True, null=True)
    field_count = models.IntegerField(blank=True, null=True)
    model_count = models.IntegerField(blank=True, null=True)
    distribution_count = models.IntegerField(blank=True, null=True)
    request_count = models.IntegerField(blank=True, null=True)
    project_count = models.IntegerField(blank=True, null=True)
    maturity_level = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'dataset_statistic'

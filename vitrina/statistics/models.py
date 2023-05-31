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
    dataset_id = models.CharField(unique=True, max_length=255, blank=True, null=True)
    download_request_count = models.CharField(unique=True, max_length=255, blank=True, null=True)
    download_object_count = models.CharField(unique=True, max_length=255, blank=True, null=True)
    object_count = models.CharField(unique=True, max_length=255, blank=True, null=True)
    field_count = models.CharField(unique=True, max_length=255, blank=True, null=True)
    model_count = models.CharField(unique=True, max_length=255, blank=True, null=True)
    distribution_count = models.CharField(unique=True, max_length=255, blank=True, null=True)
    request_count = models.CharField(unique=True, max_length=255, blank=True, null=True)
    project_count = models.CharField(unique=True, max_length=255, blank=True, null=True)
    maturity_level = models.CharField(unique=True, max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'dataset_statistic'

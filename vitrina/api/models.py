from django.db import models

from vitrina.orgs.models import Organization, Representative


class ApiKey(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField(default=1)

    api_key = models.CharField(max_length=255, blank=True, null=True)
    enabled = models.BooleanField(blank=True, null=True)
    expires = models.DateTimeField(blank=True, null=True)
    representative = models.ForeignKey(Representative, models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'api_key'

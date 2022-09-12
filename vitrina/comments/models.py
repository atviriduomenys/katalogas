from django.db import models


class Comment(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    deleted_date = models.DateTimeField(blank=True, null=True)

    author_id = models.BigIntegerField(blank=True, null=True)
    author_name = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.CharField(max_length=255, blank=True, null=True)

    body = models.TextField(blank=True, null=True)

    parent_id = models.BigIntegerField(blank=True, null=True)

    dataset_id = models.BigIntegerField(blank=True, null=True)
    dataset_uuid = models.CharField(max_length=255, blank=True, null=True)

    request_id = models.BigIntegerField(blank=True, null=True)


    class Meta:
        managed = True
        db_table = 'comment'


# TODO: To be removed.
class Suggestion(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'suggestion'

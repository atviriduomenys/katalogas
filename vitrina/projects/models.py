from django.db import models

from vitrina.users.models import User
from vitrina.projects.managers import PublicProjectManager


class Project(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    beneficiary_group = models.CharField(max_length=255, blank=True, null=True)
    benefit = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    extra_information = models.TextField(blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usecase'

    objects = models.Manager()
    public = PublicProjectManager()


class UsecaseDatasetIds(models.Model):
    project = models.ForeignKey(Project, models.DO_NOTHING)
    dataset_ids = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usecase_dataset_ids'


class UsecaseLike(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    usecase_uuid = models.CharField(max_length=255, blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usecase_like'


# TODO: To be removed:
# --------------------------->8-------------------------------------
class PartnerApplication(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    email = models.TextField(blank=True, null=True)
    filename = models.TextField(blank=True, null=True)
    letter = models.TextField(blank=True, null=True)
    organization_title = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    viisp_email = models.CharField(max_length=255, blank=True, null=True)
    viisp_first_name = models.CharField(max_length=255, blank=True, null=True)
    viisp_last_name = models.CharField(max_length=255, blank=True, null=True)
    viisp_phone = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    viisp_dob = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'partner_application'


class ApplicationSetting(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    name = models.CharField(max_length=255, blank=True, null=True)
    value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'application_setting'


class ApplicationUseCase(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    author = models.CharField(max_length=255, blank=True, null=True)
    beneficiary = models.CharField(max_length=255, blank=True, null=True)
    platform = models.CharField(max_length=255, blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'application_usecase'


class ApplicationUsecaseDatasetIds(models.Model):
    application_usecase = models.ForeignKey(ApplicationUseCase, models.DO_NOTHING)
    dataset_ids = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'application_usecase_dataset_ids'
# --------------------------->8-------------------------------------

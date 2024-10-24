from django.db import models
from django.urls import reverse
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType

from filer.fields.image import FilerImageField

from vitrina.users.models import User
from vitrina.projects.managers import PublicProjectManager


class Project(models.Model):
    UPLOAD_TO = "data/files"

    CREATED = "CREATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STATUSES = {
        (CREATED, _("Pateiktas")),
        (APPROVED, _("Patvirtintas")),
        (REJECTED, _("Atmestas")),
    }

    EDITED = "EDITED"
    STATUS_CHANGED = "STATUS_CHANGED"
    DELETED = "DELETED"
    HISTORY_MESSAGES = {
        CREATED: _("Sukurta"),
        EDITED: _("Redaguota"),
        DELETED: _("Ištrinta"),
    }

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    beneficiary_group = models.CharField(max_length=255, blank=True, null=True)
    benefit = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    extra_information = models.TextField(blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, choices=STATUSES, blank=False, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey(User, models.PROTECT, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    image = FilerImageField(null=True, blank=True, related_name="image_project", on_delete=models.SET_NULL)

    comments = GenericRelation('vitrina_comments.Comment')
    datasets = models.ManyToManyField("vitrina_datasets.Dataset")

    # Deprecated fields
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        db_table = 'usecase'

    objects = models.Manager()
    public = PublicProjectManager()

    def __str__(self):
        return self.get_title()

    def get_absolute_url(self):
        return reverse('project-detail', kwargs={'pk': self.pk})

    def get_title(self):
        if self.title:
            return self.title
        else:
            return Truncator(self.url).chars(42)

    def get_acl_parents(self):
        return [self]

    def get_likes(self):
        from vitrina.likes.models import Like
        content_type = ContentType.objects.get_for_model(self)
        return (
            Like.objects.
            filter(
                content_type=content_type,
                object_id=self.pk,
            ).
            count()
        )


class UsecaseLike(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    usecase_uuid = models.CharField(max_length=255, blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = True
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
        managed = True
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
        managed = True
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
    user = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'application_usecase'


class ApplicationUsecaseDatasetIds(models.Model):
    application_usecase = models.ForeignKey(ApplicationUseCase, models.CASCADE)
    dataset_ids = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'application_usecase_dataset_ids'
# --------------------------->8-------------------------------------

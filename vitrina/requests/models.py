from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from vitrina.orgs.models import Organization
from vitrina.requests.managers import PublicRequestManager
from vitrina.users.models import User


CREATED = "CREATED"
REJECTED = "REJECTED"
APPROVED = "APPROVED"
EDITED = "EDITED"
STATUS_CHANGED = "STATUS_CHANGED"
ASSIGNED = "ASSIGNED"
REQUEST_HISTORY_STATUSES = {
    CREATED: _("Sukurta"),
    REJECTED: _("Atmesta"),
    APPROVED: _("Patvirtinta"),
    EDITED: _("Redaguota"),
    STATUS_CHANGED: _("Pakeistas statusas"),
    ASSIGNED: _("Priskirta")
}


class Request(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    CREATED = "CREATED"
    REJECTED = "REJECTED"
    OPENED = "OPENED"
    ANSWERED = "ANSWERED"
    APPROVED = "APPROVED"
    STATUSES = {
        (CREATED, _("Pateiktas")),
        (REJECTED, _("Atmestas")),
        (OPENED, _("Atvertas")),
        (ANSWERED, _("Atsakytas")),
        (APPROVED, _("Patvirtintas"))
    }

    EDITED = "EDITED"
    STATUS_CHANGED = "STATUS_CHANGED"
    ASSIGNED = "ASSIGNED"
    DELETED = "DELETED"
    HISTORY_MESSAGES = {
        CREATED: _("Sukurta"),
        REJECTED: _("Atmesta"),
        APPROVED: _("Patvirtinta"),
        EDITED: _("Redaguota"),
        STATUS_CHANGED: _("Pakeistas statusas"),
        ASSIGNED: _("Priskirta"),
        DELETED: _("Ištrinta"),
    }

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    comment = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    format = models.CharField(max_length=255, blank=True, null=True)
    is_existing = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    organization = models.ForeignKey(Organization, models.DO_NOTHING, blank=True, null=True)
    periodicity = models.CharField(max_length=255, blank=True, null=True)
    planned_opening_date = models.DateField(blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, choices=STATUSES, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    changes = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.BooleanField(default=True)
    structure_data = models.TextField(blank=True, null=True)
    structure_filename = models.CharField(max_length=255, blank=True, null=True)

    content_type = models.ForeignKey(ContentType, models.CASCADE, verbose_name=_("Objekto tipas"), null=True)
    object_id = models.PositiveIntegerField(_("Objekto id"), null=True)
    object = GenericForeignKey('content_type', 'object_id')

    external_object_id = models.CharField(max_length=255, blank=True, null=True)
    external_content_type = models.CharField(max_length=255, blank=True, null=True)

    objects = models.Manager()
    public = PublicRequestManager()

    class Meta:
        db_table = 'request'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('request-detail', kwargs={'pk': self.pk})

    def get_acl_parents(self):
        parents = [self]
        if self.organization:
            parents.extend(self.organization.get_acl_parents())
        return parents

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

    def is_created(self):
        return self.status == self.CREATED


# TODO: https://github.com/atviriduomenys/katalogas/issues/59
class RequestEvent(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    meta = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    request = models.ForeignKey(Request, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'request_event'


# TODO: https://github.com/atviriduomenys/katalogas/issues/14
class RequestStructure(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    data_notes = models.CharField(max_length=255, blank=True, null=True)
    data_title = models.CharField(max_length=255, blank=True, null=True)
    data_type = models.CharField(max_length=255, blank=True, null=True)
    dictionary_title = models.CharField(max_length=255, blank=True, null=True)
    request_id = models.BigIntegerField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'request_structure'

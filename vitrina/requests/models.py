from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from vitrina.orgs.models import Organization
from vitrina.requests.managers import PublicRequestManager
from vitrina.users.models import User
from vitrina.datasets.models import Dataset


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
    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    STATUSES = {
        (CREATED, _("Pateiktas")),
        (REJECTED, _("Atmestas")),
        (OPENED, _("Įvykdytas")),
        (ANSWERED, _("Atsakytas")),
        (PLANNED, _("Suplanuotas")),
        (APPROVED, _("Įvertintas"))
    }
    FILTER_STATUSES = {
        CREATED: _("Pateiktas"),
        REJECTED: _("Atmestas"),
        OPENED: _("Įvykdytas"),
        ANSWERED: _("Atsakytas"),
        PLANNED: _("Suplanuotas"),
        APPROVED: _("Įvertintas")
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
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True, related_name='dataset_request')
    description = models.TextField(blank=True, null=True)
    format = models.CharField(max_length=255, blank=True, null=True)
    is_existing = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
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
    organizations = models.ManyToManyField(Organization)


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
        for org in self.organizations.all():
            parents.extend(org.get_acl_parents())
        return parents

    def get_plan_title(self):
        if self.requestobject_set.filter(
            external_object_id__isnull=False,
            external_content_type__isnull=False,
        ).exists():
            return _("Klaidų duomenyse pataisymas")
        return _("Duomenų rinkinio papildymas")

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

    def is_not_closed(self):
        return self.status != self.REJECTED and self.status != self.OPENED
    
    def jurisdiction(self) -> int | None:
        jurisdictions = []
        for org in self.organizations.all():
            root_org = org.get_root()
            if root_org.get_children_count() > 1:
                jurisdictions.append(root_org.pk)
        return jurisdictions

    def dataset_statuses(self):
        return list(Dataset.objects.filter(
            request_objects__request=self
        ).values_list('status', flat=True))

    def dataset_organizations(self):
        orgs = []
        dataset_ids = [ro.object_id for ro in RequestObject.objects.filter(
            request_id=self.pk,
            content_type=ContentType.objects.get_for_model(Dataset)
        )]
        for dataset_id in dataset_ids:
            dataset = Dataset.objects.filter(id=dataset_id).first()
            if dataset and dataset.organization not in orgs:
                orgs.append(dataset.organization.pk)
        return orgs

    def dataset_categories(self):
        cats = []
        dataset_ids = [ro.object_id for ro in RequestObject.objects.filter(
            request_id=self.pk,
            content_type=ContentType.objects.get_for_model(Dataset)
        )]
        for dataset_id in dataset_ids:
            dataset = Dataset.objects.filter(id=dataset_id).first()
            if dataset and dataset.category not in cats:
                cats.append(dataset.category)
        return cats

    def dataset_parent_categories(self):
        cats = []
        dataset_ids = [ro.object_id for ro in RequestObject.objects.filter(
            request_id=self.pk,
            content_type=ContentType.objects.get_for_model(Dataset)
        )]
        for dataset_id in dataset_ids:
            dataset = Dataset.objects.filter(id=dataset_id).first()
            if dataset:
                for category in dataset.parent_category():
                    if category not in cats:
                        cats.append(category)
        return cats

    def dataset_group_list(self):
        groups = []
        dataset_ids = [ro.object_id for ro in RequestObject.objects.filter(
            request_id=self.pk,
            content_type=ContentType.objects.get_for_model(Dataset)
        )]
        for dataset_id in dataset_ids:
            dataset = Dataset.objects.filter(id=dataset_id).first()
            if dataset:
                for group in dataset.get_group_list():
                    if group not in groups:
                        groups.append(group)
        return groups

    def dataset_get_tag_list(self):
        tags = []
        dataset_ids = [ro.object_id for ro in RequestObject.objects.filter(
            request_id=self.pk,
            content_type=ContentType.objects.get_for_model(Dataset)
        )]
        for dataset_id in dataset_ids:
            dataset = Dataset.objects.filter(id=dataset_id).first()
            if dataset:
                for tag in dataset.get_tag_list():
                    if tag not in tags:
                        tags.append(tag)
        return tags


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
    request = models.ForeignKey(Request, models.CASCADE, blank=True, null=True)

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


class RequestObject(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    request = models.ForeignKey(Request, on_delete=models.CASCADE)

    external_object_id = models.CharField(max_length=255, blank=True, null=True)
    external_content_type = models.CharField(max_length=255, blank=True, null=True)


class RequestAssignment(models.Model):
    organization = models.ForeignKey(Organization, models.DO_NOTHING, db_column='organization', blank=True, null=True)
    request = models.ForeignKey(Request, models.DO_NOTHING, db_column='request', blank=True, null=True)
    status = models.CharField(max_length=255, choices=Request.STATUSES, blank=True, null=True)
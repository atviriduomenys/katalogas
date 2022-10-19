from datetime import datetime

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from treebeard.mp_tree import MP_Node, MP_NodeManager

from vitrina.orgs.managers import PublicOrganizationManager

from django.utils.translation import gettext_lazy as _


class Region(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'region'


class Municipality(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    title = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'municipality'


class Organization(MP_Node):
    GOV = "gov"
    COM = "com"
    ORG = "org"
    ORGANIZATION_KINDS = {
        (GOV, _("Valstybinė įstaiga")),
        (COM, _("Verslo organizacija")),
        (ORG, _("Nepelno ir nevalstybinė organizacija"))
    }

    created = models.DateTimeField(blank=True, null=True, default=datetime.now)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    municipality = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255, blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    company_code = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.BooleanField(blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    jurisdiction = models.CharField(max_length=255, blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)
    kind = models.CharField(max_length=36, choices=ORGANIZATION_KINDS, default=ORG)

    node_order_by = ["created"]

    class Meta:
        db_table = 'organization'

    def __str__(self):
        return self.title

    objects = MP_NodeManager()
    public = PublicOrganizationManager()

    def get_absolute_url(self):
        return reverse('organization-detail', kwargs={'pk': self.pk})

    def get_acl_parents(self):
        return [self]


class Representative(models.Model):
    COORDINATOR = 'coordinator'
    MANAGER = 'manager'
    ROLES = {
        (COORDINATOR, _("Koordinatorius")),
        (MANAGER, _("Tvarkytojas"))
    }

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    email = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    role = models.CharField(choices=ROLES, max_length=255)
    user = models.ForeignKey("vitrina_users.User", models.PROTECT, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'representative'
        unique_together = ['content_type', 'object_id', 'user']

    def __str__(self):
        return self.email

    def get_acl_parents(self):
        parents = [self]
        parents.extend(self.content_object.get_acl_parents())
        return parents


class PublishedReport(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    data = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'published_report'


class Report(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    body = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'report'

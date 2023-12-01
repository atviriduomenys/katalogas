from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from filer.fields.image import FilerImageField
from treebeard.mp_tree import MP_Node, MP_NodeManager

from vitrina.orgs.managers import PublicOrganizationManager

from django.utils.translation import gettext_lazy as _


class Region(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'region'

    def __str__(self):
        return self.title


class Municipality(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    title = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'municipality'

    def __str__(self):
        return self.title


class Organization(MP_Node):
    UPLOAD_TO = "data/files"

    GOV = "gov"
    COM = "com"
    ORG = "org"
    ORGANIZATION_KINDS = {
        (GOV, _("Valstybinė įstaiga")),
        (COM, _("Verslo organizacija")),
        (ORG, _("Nepelno ir nevalstybinė organizacija"))
    }

    GROUP = "group"
    MINISTRY = "ministry"
    MUNICIPALITY = "municipality"
    ROLES = (
        (GROUP, _("Grupė")),
        (MINISTRY, _("Ministerija")),
        (MUNICIPALITY, _("Savivaldybė"))
    )

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    description = models.TextField(blank=True, null=True, verbose_name=_('Aprašymas'))
    municipality = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Savivaldybė'))
    region = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Regionas'))
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True, verbose_name=_('Pavadinimas'))
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Adresas'))
    company_code = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Registracijos numeris'))
    email = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Elektroninis paštas'))
    is_public = models.BooleanField(blank=True, null=True, verbose_name=_('Organizacija viešinama'))
    phone = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Telefono numeris'))
    jurisdiction = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Jurisdikcija'))
    website = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Tinklalapis'))
    kind = models.CharField(max_length=36, choices=ORGANIZATION_KINDS, default=ORG, verbose_name=_('Tipas'))
    role = models.CharField(max_length=255, choices=ROLES, null=True, blank=True, verbose_name=_('Vaidmuo'))
    image = FilerImageField(null=True, blank=True,
                            related_name="image_organization",
                            on_delete=models.SET_NULL, verbose_name=_('Logotipas'))
    provider = models.BooleanField(default=False, verbose_name=_("Atvėrimo duomenų teikėjas"))
    name = models.TextField(max_length=255, unique=True, blank=True, null=True)

    # Deprecated fields
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    node_order_by = ["title"]
    representatives = GenericRelation('Representative')

    class Meta:
        db_table = 'organization'

    def __str__(self):
        return self.title

    objects = MP_NodeManager()
    public = PublicOrganizationManager()

    def get_absolute_url(self):
        return reverse('organization-detail', kwargs={'pk': self.pk})

    def get_acl_parents(self):
        parents = [self]
        parents.extend(self.get_ancestors())
        return parents

    def dataset_tags(self):
        from vitrina.datasets.models import Dataset
        tags = []
        for dataset in Dataset.objects.filter(organization=self.pk).all():
            for tag in dataset.get_tag_list():
                if tag not in tags:
                    tags.append(tag)
        return tags


class Representative(models.Model):
    COORDINATOR = 'coordinator'
    MANAGER = 'manager'
    SUPERVISOR = 'supervisor'
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
    has_api_access = models.BooleanField(default=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = models.Manager()

    class Meta:
        db_table = 'representative'
        unique_together = ['content_type', 'object_id', 'user']

    def __str__(self):
        return self.email

    def get_acl_parents(self):
        parents = [self]
        parents.extend(self.content_object.get_acl_parents())
        return parents

    def is_supervisor(self, organization):
        if isinstance(self.content_object, Organization):
            if organization in self.content_object.get_descendants():
                return True
        return False


class PublishedReport(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    data = models.TextField(blank=True, null=True, verbose_name=_("Duomenys"))
    title = models.TextField(blank=True, null=True, verbose_name=_('Pavadinimas'))

    class Meta:
        managed = True
        db_table = 'published_report'
        verbose_name = _("Ataskaita")
        verbose_name_plural = _("Ataskaitos")


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


class OrganizationMapping(models.Model):
    org_id = models.IntegerField(blank=False, null=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'organization_mapping'


class RepresentativeRequest(models.Model):
    user = models.ForeignKey('vitrina_users.User', models.DO_NOTHING, blank=True, null=True)
    document = models.FileField(upload_to='data/files/request_assignments')
    organization = models.ForeignKey(Organization, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'representative_request'
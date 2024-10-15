from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from filer.fields.image import FilerImageField
from treebeard.mp_tree import MP_Node, MP_NodeManager

from vitrina.orgs.managers import PublicOrganizationManager, OrganizationRepresentativeManager, RepresentativeManager, \
    RepresentativeWithDeletedManager, OrganizationRepresentativeWithDeletedManager

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
        verbose_name = _("Organizacija")
        verbose_name_plural = _("Organizacijos")

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # save related datasets to update search index
        for dataset in self.dataset_set.all():
            dataset.save()

        # save related requests to update search index
        for request_assignment in self.requestassignment_set.all():
            request_assignment.request.save()


class Representative(models.Model):
    COORDINATOR = 'coordinator'
    MANAGER = 'manager'
    SUPERVISOR = 'supervisor'
    ROLES = {
        (COORDINATOR, _("Koordinatorius")),
        (MANAGER, _("Tvarkytojas"))
    }

    ACTIVE = 'active'
    AWAITING_CONFIRMATION = 'awaiting_confirmation'
    DELETED = 'deleted'
    STATUSES = (
        (ACTIVE, _("Aktyvus")),
        (AWAITING_CONFIRMATION, _("Laukiama patvirtinimo")),
        (DELETED, _("Pašalintas")),
    )

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    email = models.CharField(_("Elektroninis paštas"), max_length=255)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    role = models.CharField(_("Rolė"), choices=ROLES, max_length=255)
    user = models.ForeignKey("vitrina_users.User", models.PROTECT, null=True)
    has_api_access = models.BooleanField(default=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    status = models.CharField(max_length=255, blank=True, null=True, choices=STATUSES)

    objects = RepresentativeManager()
    objects_with_deleted = RepresentativeWithDeletedManager()

    class Meta:
        db_table = 'representative'

    def __str__(self):
        return self.full_name_with_email

    def get_acl_parents(self):
        parents = [self]
        parents.extend(self.content_object.get_acl_parents())
        return parents

    def is_supervisor(self, organization):
        if isinstance(self.content_object, Organization):
            if organization in self.content_object.get_descendants():
                return True
        return False

    @property
    def full_name(self):
        if self.user:
            return self.user.first_name + " " + self.user.last_name
        return self.email

    @property
    def full_name_with_email(self):
        if self.user:
            return f'{self.user.first_name} {self.user.last_name} ({self.email})'
        return self.email

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # save related datasets to update search index
        Dataset = apps.get_model('vitrina_datasets', 'Dataset')
        if isinstance(self.content_object, Dataset):
            self.content_object.save()


class OrganizationRepresentative(Representative):
    objects = OrganizationRepresentativeManager()
    objects_with_deleted = OrganizationRepresentativeWithDeletedManager()

    class Meta:
        proxy = True
        verbose_name = _("Organizacijos atstovas")
        verbose_name_plural = _("Organizacijos atstovų sąrašas")


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
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STATUSES = {
        (CREATED, _("Pateiktas")),
        (APPROVED, _("Patvirtintas")),
        (REJECTED, _("Atmestas")),
    }

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Sukurta"))
    user = models.ForeignKey(
        'vitrina_users.User',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name=_("Naudotojas")
    )
    document = models.FileField(upload_to='data/files/request_assignments', verbose_name=_("Pridėtas dokumentas"))
    organization = models.ForeignKey(
        Organization,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name=_("Organizacija"))
    phone = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Telefono numeris'))
    email = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('El. paštas'))
    status = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=STATUSES,
        verbose_name=_("Būsena"),
        default=CREATED
    )

    class Meta:
        managed = True
        db_table = 'representative_request'

    def __str__(self):
        return str(self.user) if self.user else ""


class Template(models.Model):
    REPRESENTATIVE_REQUEST_ID = "representative_request"

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Sukurta"))
    modified = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name=_("Modifikuota"))
    identifier = models.CharField(max_length=255, unique=True, verbose_name=_("Identifikatorius"))
    text = models.CharField(max_length=100, verbose_name=_("Tekstas"))
    document = models.FileField(upload_to='data/files/templates', verbose_name=_("Pridėtas dokumentas"))

    class Meta:
        db_table = 'template'

    def __str__(self):
        return self.document.name

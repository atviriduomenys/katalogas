from typing import TYPE_CHECKING

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from filer.fields.image import FilerImageField
from treebeard.mp_tree import MP_Node, MP_NodeManager

from vitrina.classifiers.models import AreaOfManagement
from vitrina.orgs.managers import PublicOrganizationManager

if TYPE_CHECKING:
    from vitrina.users.models import User


class Region(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "region"

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
        db_table = "municipality"

    def __str__(self):
        return self.title


class Organization(MP_Node):
    UPLOAD_TO = "data/files"

    GOV = "gov"
    COM = "com"
    ORG = "org"
    ORGANIZATION_KINDS = (
        (GOV, _("Valstybinė įstaiga")),
        (COM, _("Verslo organizacija")),
        (ORG, _("Ne pelno siekianti ar nevyriausybinė organizacija")),
    )

    GROUP = "group"
    MINISTRY = "ministry"
    MUNICIPALITY = "municipality"
    ROLES = (
        (GROUP, _("Grupė")),
        (MINISTRY, _("Ministerija")),
        (MUNICIPALITY, _("Savivaldybė")),
    )

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    description = models.TextField(blank=True, null=True, verbose_name=_("Aprašymas"))
    municipality = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Savivaldybė"))
    region = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Regionas"))
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True, verbose_name=_("Pavadinimas"))
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Adresas"))
    company_code = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Registracijos numeris"))
    email = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Elektroninis paštas"))
    is_public = models.BooleanField(blank=True, null=True, verbose_name=_("Organizacija viešinama"))
    phone = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Telefono numeris"))
    jurisdiction = models.ForeignKey(
        AreaOfManagement,
        related_name="organization_set",
        on_delete=models.SET_DEFAULT,
        default=1,
        verbose_name=_("Valdymo sritis"),
    )
    website = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Tinklalapis"))
    kind = models.CharField(max_length=36, choices=ORGANIZATION_KINDS, default=ORG, verbose_name=_("Tipas"))
    role = models.CharField(max_length=255, choices=ROLES, null=True, blank=True, verbose_name=_("Vaidmuo"))
    image = FilerImageField(
        null=True,
        blank=True,
        related_name="image_organization",
        on_delete=models.SET_NULL,
        verbose_name=_("Logotipas"),
    )
    publisher = models.BooleanField(default=False, verbose_name=_("Duomenų atvėrimo paslaugų teikėjas"))
    name = models.TextField(max_length=255, unique=True, blank=True, null=True)
    alternative_titles = models.TextField(_("Alternatyvūs pavadinimai"), null=True, blank=True)

    # Deprecated fields
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    node_order_by = ["title"]
    representatives = GenericRelation("Representative")

    class Meta:
        db_table = "organization"

    def __str__(self):
        return self.title

    objects = MP_NodeManager()
    public = PublicOrganizationManager()

    def get_absolute_url(self):
        return reverse("organization-detail", kwargs={"pk": self.pk})

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

    @property
    def whitelisted_names(self) -> list[str]:
        return [whitelisted_code.code_name for whitelisted_code in self.whitelisted_code_names.all()]


class PublisherOrganization(Organization):
    class Meta:
        proxy = True
        verbose_name = _("Duomenų atvėrimo paslaugų teikėjas")
        verbose_name_plural = _("Duomenų atvėrimo paslaugų teikėjai")


class Representative(models.Model):
    RESOURCE_COORDINATOR = "resource_coordinator"
    RESOURCE_MANAGER = "resource_manager"
    SUPERVISOR = "supervisor"
    OPEN_DATA_COORDINATOR = "open_data_coordinator"
    OPEN_DATA_MANAGER = "open_data_manager"
    OPEN_DATA_PUBLISHER = "open_data_publisher"

    COORDINATOR_ROLES = (
        RESOURCE_COORDINATOR,
        OPEN_DATA_COORDINATOR,
    )
    MANAGER_ROLES = (
        RESOURCE_MANAGER,
        OPEN_DATA_MANAGER,
    )

    ROLES = (
        (RESOURCE_COORDINATOR, _("Duomenų išteklių koordinatorius")),
        (RESOURCE_MANAGER, _("Duomenų išteklių tvarkytojas")),
        (OPEN_DATA_COORDINATOR, _("Atvirų duomenų koordinatorius")),
        (OPEN_DATA_MANAGER, _("Atvirų duomenų tvarkytojas")),
        (OPEN_DATA_PUBLISHER, _("Atvirų duomenų skelbėjas")),
    )

    OPEN_DATA_ROLES = (
        (OPEN_DATA_COORDINATOR, _("Atvirų duomenų koordinatorius")),
        (OPEN_DATA_MANAGER, _("Atvirų duomenų tvarkytojas")),
        (OPEN_DATA_PUBLISHER, _("Atvirų duomenų skelbėjas")),
    )

    RESOURCE_ROLES = (
        (RESOURCE_COORDINATOR, _("Duomenų išteklių koordinatorius")),
        (RESOURCE_MANAGER, _("Duomenų išteklių tvarkytojas")),
    )

    OPEN_DATA_ROLE_KEYS = {role[0] for role in OPEN_DATA_ROLES}
    RESOURCE_ROLE_KEYS = {role[0] for role in RESOURCE_ROLES}

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
    organization = models.ForeignKey(Organization, models.SET_NULL, blank=True, null=True, default=None)
    has_api_access = models.BooleanField(default=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    can_make_agreements = models.BooleanField(default=False)

    objects = models.Manager()

    class Meta:
        db_table = "representative"
        unique_together = ["content_type", "object_id", "user"]

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

    def can_be_updated_by(self, user: "User") -> bool:
        if user.is_superuser or user.is_staff:
            return True

        user_rep = user.representative_set.filter(organization=self.organization).first()
        if not user_rep:
            return False

        if user_rep.role == Representative.OPEN_DATA_COORDINATOR:
            return self.role in Representative.OPEN_DATA_ROLE_KEYS

        if user_rep.role == Representative.RESOURCE_COORDINATOR:
            return self.role in (
                Representative.RESOURCE_COORDINATOR,
                Representative.RESOURCE_MANAGER,
                Representative.OPEN_DATA_COORDINATOR,
                Representative.OPEN_DATA_MANAGER,
            )

        return False


class PublishedReport(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    data = models.TextField(blank=True, null=True, verbose_name=_("Duomenys"))
    title = models.TextField(blank=True, null=True, verbose_name=_("Pavadinimas"))

    class Meta:
        managed = True
        db_table = "published_report"
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
        db_table = "report"


class OrganizationMapping(models.Model):
    org_id = models.IntegerField(blank=False, null=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "organization_mapping"


class RepresentativeRequest(models.Model):
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STATUSES = (
        (CREATED, _("Pateiktas")),
        (APPROVED, _("Patvirtintas")),
        (REJECTED, _("Atmestas")),
    )

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Sukurta"))
    user = models.ForeignKey(
        "vitrina_users.User",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name=_("Naudotojas"),
    )
    document = models.FileField(
        upload_to="data/files/request_assignments",
        verbose_name=_("Pridėtas dokumentas"),
    )
    organization = models.ForeignKey(
        Organization,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name=_("Organizacija"),
    )
    phone = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Telefono numeris"))
    email = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("El. paštas"))
    status = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=STATUSES,
        verbose_name=_("Būsena"),
        default=CREATED,
    )

    class Meta:
        managed = True
        db_table = "representative_request"

    def __str__(self):
        return str(self.user) if self.user else ""


class Template(models.Model):
    REPRESENTATIVE_REQUEST_ID = "representative_request"

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Sukurta"))
    modified = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name=_("Modifikuota"))
    identifier = models.CharField(max_length=255, unique=True, verbose_name=_("Identifikatorius"))
    text = models.CharField(max_length=100, verbose_name=_("Tekstas"))
    document = models.FileField(upload_to="data/files/templates", verbose_name=_("Pridėtas dokumentas"))

    class Meta:
        db_table = "template"

    def __str__(self):
        return self.document.name


class WhitelistedCodeName(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="whitelisted_code_names",
        verbose_name=_("Organizacija"),
    )
    code_name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("Kodinis pavadinimas"),
        help_text=_("Unikalus kodinis pavadinimas, kurį galima naudoti kuriant duomenų išteklius."),
    )

    class Meta:
        verbose_name = _("Leistinas kodinis pavadinimas")
        verbose_name_plural = _("Leistini kodiniai pavadinimai")
        ordering = ["code_name"]

    def __str__(self):
        return self.code_name

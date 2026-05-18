import json
import logging
import pathlib
from datetime import datetime
from functools import cached_property
from random import randrange
from uuid import uuid4

from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, connection
from django.db.models import Sum, QuerySet, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from filer.fields.file import FilerFileField
from tagulous.models import TagModel
from parler.models import TranslatedFields, TranslatableModel
from tagulous.models import TagField
from treebeard.mp_tree import MP_Node

from vitrina.catalogs.models import Catalog, HarvestingJob
from vitrina.classifiers.models import (
    Category,
    Frequency,
    Concept,
    ApplicableLegislation,
    Rule,
    Status,
    Licence,
    LANGUAGE_CONCEPT_SCHEMA_URI,
    ProvenanceStatement,
    Activity,
    ServiceQualityPage,
)
from vitrina.utils import translate_text
from vitrina.datasets.managers import (
    EdpPublicDatasetManager,
    EdpRestrictedDatasetManager,
    PublicDatasetManager,
    TranslatableMPNodeManager,
    PermittedDatasetManager,
)
from vitrina.models import UUIDBaseModel
from vitrina.orgs.models import Organization, Representative
from vitrina.structure import VersionStatus
from vitrina.structure.models import Model, Base, Property, Metadata, StatusCode, ParamItem, EnumItem, Version
from vitrina.users.models import User
from vitrina.datasets.tasks import update_applicable_legislation_description
from vitrina.uapi.models import Agent

logger = logging.getLogger(__name__)


def get_default_subclass():
    return DCATResourceSubclass.objects.get(name="dataset").pk


class DatasetGroup(TranslatableModel):
    HVD = "hvd"

    translations = TranslatedFields(
        title=models.CharField(_("Title"), unique=True, max_length=255, blank=False),
    )
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    name = models.CharField(_("Kodinis pavadinimas"), max_length=255, blank=False)

    class Meta:
        ordering = ["created"]

    def __str__(self):
        return self.safe_translation_getter("title", language_code=self.get_current_language())


class DatasetGroupCategoryUri(models.Model):
    category = models.ForeignKey("vitrina_classifiers.Category", verbose_name=_("Kategorija"), on_delete=models.CASCADE)
    group = models.ForeignKey(DatasetGroup, verbose_name=_("Grupė"), on_delete=models.CASCADE)
    uri = models.CharField(_("Nuoroda į kontroliuojamą žodyną"), max_length=255, null=True, blank=True)

    class Meta:
        db_table = "dataset_group_category_uri"

    def __str__(self):
        return ""


class DatasetFile(models.Model):
    file = FilerFileField(verbose_name=_("Failas"), on_delete=models.CASCADE)
    dataset = models.ForeignKey(
        "Dataset",
        verbose_name=_("Duomenų rinkinys"),
        on_delete=models.CASCADE,
        related_name="dataset_files",
    )

    class Meta:
        db_table = "dataset_file"

    def filename_without_path(self):
        return pathlib.Path(self.file.file.name).name if self.file and self.file.file else ""


class Resource(MP_Node, TranslatableModel):
    """
    Conceptual abstract model.
    Created to have common terminology between code and business language.
    It May become a concrete model in the future
    """

    steplen = 25  # to set depth max up to 10 with 255 length path varchar (MP_Node default).
    depth = models.PositiveIntegerField(default=1)  # Root by default

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        if not self.path:
            self.add_root(instance=self)
        else:
            super().save(*args, **kwargs)

    def add_self_as_root(self) -> None:
        last_root = self.get_last_root_node()
        self.depth = 1
        self.path = last_root._inc_path() if last_root else self._get_path(None, 1, 1)
        self.save()
        self.fix_tree(fix_paths=True)


class Dataset(Resource):
    node_order_by = ("subclass",)

    UPLOAD_TO = "data/files"

    HAS_DATA = "HAS_DATA"
    INVENTORED = "INVENTORED"
    PLANNED = "PLANNED"
    UNASSIGNED = "UNASSIGNED"
    HAS_DATA_TITLE = _("Atvertas")
    STATUSES = (
        (HAS_DATA, HAS_DATA_TITLE),
        (INVENTORED, _("Inventorintas")),
        (PLANNED, _("Planuojamas atverti")),
        (UNASSIGNED, _("Nepriskirta")),
    )
    FILTER_STATUSES = {
        HAS_DATA: _("Atverti duomenys"),
        INVENTORED: _("Tik inventorinti"),
        PLANNED: _("Planuojama atverti"),
        UNASSIGNED: _("Nepriskirta"),
    }

    FILTER_SUBCLASSES = {
        "dataset": _("Duomenų rinkinys"),
        "catalog": _("Metaduomenų katalogas"),
        "information_system": _("Informacinė sistema"),
        "service": _("Duomenų publikavimo paslauga"),
        "series": _("Duomenų rinkinių serija"),
    }

    CREATED = "CREATED"
    EDITED = "EDITED"
    STATUS_CHANGED = "STATUS_CHANGED"
    TRANSFERRED = "TRANSFERRED"
    DATA_ADDED = "DATA_ADDED"
    DATA_UPDATED = "DATA_UPDATED"
    DELETED = "DELETED"
    PROJECT_SET = "PROJECT_SET"
    REQUEST_SET = "REQUEST_SET"
    CATEGORY_UPDATED = "CATEGORY_UPDATED"
    RELATION_ADDED = "RELATION_ADDED"
    RELATION_DELETED = "RELATION_DELETED"
    ATTRIBUTION_ADDED = "ATTRIBUTION_ADDED"
    ATTRIBUTION_DELETED = "ATTRIBUTION_DELETED"
    HISTORY_MESSAGES = {
        CREATED: _("Sukurta"),
        EDITED: _("Redaguota"),
        STATUS_CHANGED: _("Pakeistas statusas"),
        TRANSFERRED: _("Perkelta"),
        DATA_ADDED: _("Pridėti duomenys"),
        DATA_UPDATED: _("Redaguoti duomenys"),
        DELETED: _("Ištrinta"),
        PROJECT_SET: _("Priskirta projektui"),
        REQUEST_SET: _("Priskirta poreikiui"),
        CATEGORY_UPDATED: _("Pakeista kategorija(-os)"),
        RELATION_ADDED: _("Pridėtas ryšys"),
        RELATION_DELETED: _("Ištrintas ryšys"),
        ATTRIBUTION_ADDED: _("Priskirta organizacijai"),
        ATTRIBUTION_DELETED: _("Pašalinta iš organizacijos"),
    }

    PUBLIC = "PUBLIC"
    RESTRICTED = "RESTRICTED"
    NON_PUBLIC = "NON_PUBLIC"
    CONFIDENTIAL = "CONFIDENTIAL"

    ACCESS_RIGHTS = (
        (PUBLIC, _("Vieši")),
        (RESTRICTED, _("Apriboti")),
        (NON_PUBLIC, _("Nevieši")),
        (CONFIDENTIAL, _("Konfidencialūs")),
    )
    FILTER_ACCESS_RIGHTS = {
        PUBLIC: _("Vieši"),
        RESTRICTED: _("Apriboti"),
        NON_PUBLIC: _("Nevieši"),
        CONFIDENTIAL: _("Konfidencialūs"),
    }

    API_ORIGIN = "api"

    INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI = "dcataplt:Importance"
    INFORMATION_SYSTEM_TYPE_SCHEMA_URI = "dcataplt:Type"
    SERVICE_TYPE_SCHEME_URI = "http://publications.europa.eu/resource/authority/data-service-type"
    DATASET_TYPE_SCHEME_URI = "http://publications.europa.eu/resource/authority/dataset-type"

    translations = TranslatedFields(
        title=models.TextField(
            verbose_name=_("Pavadinimas"),
            blank=True,
            help_text=_("Duomenų ištekliui suteiktas pavadinimas. Atitinka dct:title."),
        ),
        description=models.TextField(
            verbose_name=_("Aprašymas"),
            blank=True,
            help_text=_("Laisvo teksto aprašas laisvos formos tekstu. Atitinka dct:description."),
        ),
        conditions=models.TextField(
            verbose_name=_("Teisės - Aprašymas"),
            blank=True,
            null=True,
            help_text=_(
                "Laisvu tekstu pateikiamas teisių deklaracijos aprašymas. Atitinka dct:rights / dct:description."
            ),
        ),
    )

    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(
        blank=True,
        null=True,
        auto_now_add=True,
    )
    modified = models.DateTimeField(
        blank=True,
        null=True,
        auto_now=True,
    )
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    soft_deleted = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField(default=1)  # TODO: Deprecated, versioning is done w/ django-reversion
    slug = models.CharField(
        unique=True,
        max_length=255,
        blank=False,
        null=True,
    )  # TODO: Deprecated, slugs are formed from id's
    uuid = models.UUIDField(unique=True, default=uuid4, editable=False)
    internal_id = models.CharField(max_length=255, blank=True, null=True)

    theme = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )  # TODO: Deprecated, category should be used instead.
    category = models.ManyToManyField(
        Category,
        verbose_name=_("Kategorija"),
        blank=True,
    )
    category_old = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    catalog = models.ForeignKey(
        Catalog,
        models.SET_NULL,
        db_column="catalog",
        blank=True,
        null=True,
        verbose_name=_("Katalogas"),
        help_text=_("Katalogas, kurio turinys domina šio katalogo kontekste. Atitinka dcat:Catalog."),
    )
    # TODO: Should not be used anymore, instead:
    #  - https://github.com/atviriduomenys/katalogas/blob/1c2e6cf69f271a655700b196ae7fd7e0fb6d2807/vitrina/datasets/models.py#L1399
    origin = models.CharField(max_length=255, blank=True, null=True)

    organization = models.ForeignKey(
        Organization,
        models.PROTECT,
        blank=True,
        null=True,
        verbose_name=_("Duomenų tvarkytojas"),
    )

    status = models.CharField(
        max_length=255,
        choices=STATUSES,
        default=UNASSIGNED,
    )
    published = models.DateTimeField(
        blank=True,
        null=True,
    )
    is_public = models.BooleanField(
        default=True,
        verbose_name=_("Duomenų išteklius viešinamas"),
    )

    # Used only in Partner API. Fields are set, but never used. Should be migrated to use languages field.
    language = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    languages = models.ManyToManyField(
        Concept,
        blank=True,
        related_name="languages",
        verbose_name=_("Kalba"),
        help_text=_("Ši savybė nurodo duomenų ištekliaus kalbą. Atitinka dct:language."),
        limit_choices_to={"concept_schemas__uri": LANGUAGE_CONCEPT_SCHEMA_URI},
    )

    spatial_coverage = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    temporal_coverage = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    update_frequency = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    frequency = models.ForeignKey(
        Frequency,
        models.SET_NULL,
        blank=False,
        null=True,
        verbose_name=_("Atnaujinimo dažnumas"),
        help_text=_("Duomenų atnaujinimo dažnumas. Atitinka dct:accrualPeriodicity."),
    )
    last_update = models.DateTimeField(
        blank=True,
        null=True,
    )

    access_rights = models.CharField(
        _("Prieigos teisės"),
        blank=True,
        default=PUBLIC,
        choices=ACCESS_RIGHTS,
        max_length=255,
        help_text=_(
            "Informacija ar duomenų rinkinys yra atviri duomenys, ar jam taikomi prieigos apribojimai, ar jis nėra viešas, ar jis konfidencialus. Atitinka dct:accessRights."
        ),
    )

    tags = TagField(
        blank=True,
        force_lowercase=True,
        space_delimiter=False,
        autocomplete_view="autocomplete_tags",
        autocomplete_limit=20,
        verbose_name=_("Žymės"),
        help_text=_("Duomenų išteklių apibūdinantys raktažodžiai arba žymos. Atitinka dcat:keyword."),
        autocomplete_settings={"width": "100%"},
        autocomplete_view_fulltext=True,
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )
    geoportal_id = models.CharField(
        _("Geoportalo id"),
        max_length=255,
        blank=True,
        null=True,
    )
    creator_text = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    publisher = models.ForeignKey(
        Organization,
        related_name="published_datasets",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Duomenų atvėrimo paslaugų teikėjas"),
    )
    landing_page = models.URLField(
        verbose_name=_("Prieigos nuoroda"),
        max_length=1024,
        null=True,
        blank=True,
        help_text=_(
            "Tinklalapis, kuriame galima susipažinti su duomenų ištekliu, jo pateiktimi ir (arba) papildoma informacija. Ji skirta nukreipti į pradinio duomenų paslaugos teikėjo, o ne į trečiosios šalies, pavyzdžiui, agregatoriaus, svetainės puslapį. Atitinka dcat:landingPage."
        ),
    )
    is_hvd = models.BooleanField(_("Ar duomenų rinkinys yra didelės vertės"), default=False)

    # DCAT 3 fields
    part_of = models.ManyToManyField(
        "DatasetRelation",
        related_name="related_datasets",
        verbose_name=_("Duomenų rinkinio ryšiai"),
        blank=True,
    )
    type = models.ManyToManyField(
        "Type",
        verbose_name=_("Tipas"),
        blank=True,
    )
    subclass = models.ForeignKey(
        "DCATResourceSubclass",
        models.PROTECT,
        verbose_name=_("Duomenų ištekliaus poklasis"),
        default=get_default_subclass,
    )
    agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        verbose_name=_("Agentas"),
        null=True,
        blank=True,
        related_name="services",
        help_text=_(
            "Duomenų publikavimo paslaugą teikiantis agentas. Privaloma nurodyti arba Agentą arba API adresą. Atitinka dcat:endpointURL"
        ),
    )
    endpoint_url = models.URLField(
        verbose_name=_("API adresas"),
        null=True,
        blank=True,
        max_length=512,
    )
    endpoint_type = models.ForeignKey(
        "vitrina_resources.Format",
        on_delete=models.SET_NULL,
        verbose_name=_("API formatas"),
        null=True,
        blank=True,
        related_name="format_endpoint_types",
        help_text=_("Struktūra, grąžinama kviečiant paslaugos URL. Atitinka dct:format."),
    )
    endpoint_description = models.URLField(
        verbose_name=_("API specifikacija"),
        null=True,
        blank=True,
    )
    endpoint_description_type = models.ForeignKey(
        "vitrina_resources.Format",
        on_delete=models.SET_NULL,
        verbose_name=_("API specifikacijos formatas"),
        null=True,
        blank=True,
        related_name="format_endpoint_description_types",
    )
    service = models.BooleanField(
        _("DataService rinkinys"),
        default=False,
    )
    series = models.BooleanField(
        _("DataSeries rinkinys"),
        default=False,
    )

    information_system_type = models.ForeignKey(
        Concept,
        on_delete=models.PROTECT,
        verbose_name=_("Informacinės sistemos tipas"),
        help_text=_(
            "Informacinės sistemos tipas pagal Valstybės informacinių "
            "išteklių valdymo įstatymo reikalavimus. Atitinka dcataplt:Type."
        ),
        related_name="information_system_types",
    )
    information_system_importance = models.ForeignKey(
        Concept,
        on_delete=models.PROTECT,
        verbose_name=_("Informacinės sistemos svarba"),
        related_name="information_system_importance_levels",
        help_text=_(
            "Informacinės sistemos svarba pagal Valstybės informacinių išteklių valdymo įstatymo reikalavimus. Atitinka dcataplt:Importance."
        ),
    )
    information_system_assessment_url = models.URLField(
        null=True,
        blank=True,
        max_length=512,
        verbose_name=_("Informacinės sistemos svarbos vertinimas"),
        help_text=_(
            "URL nuoroda į informacinės sistemos svarbos vertinimo dokumentą. "
            "Atitinka dcataplt:ISImportanceAssessmentURL."
        ),
    )
    temporal_start = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Laikotarpio pradžios data"),
        help_text=_("Ši savybė nurodo pradžios datą, kurią apima duomenų rinkinys. Atitinka dct:temporal."),
    )
    temporal_end = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Laikotarpio pabaigos data"),
        help_text=_("Ši savybė nurodo pabaigos datą, kurią apima duomenų rinkinys. Atitinka dct:temporal."),
    )
    information_system_publishers = models.ManyToManyField(
        Organization,
        related_name="information_system_publisher_datasets",
        blank=True,
        verbose_name=_("Informacinės sistemos tvarkytojai"),
        help_text=_("Ši savybė nurodo subjektus (organizacijas), atsakingas už IS prieinamumą. Atitinka dct:publisher"),
    )
    version_notes = models.TextField(
        null=True,
        verbose_name=_("Versijos pastabos"),
        help_text=_("Versijos skirtumų aprašymas. Atitinka adms:versionNotes."),
    )

    temporal_resolution = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Laiko skiriamoji geba (sekundėmis)"),
        help_text=_("Laiko skiriamoji geba sekundėmis. Atitinka dcat:temporalResolution."),
    )

    spatial_resolution = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Erdvinė skiriamoji geba (metrais)"),
        help_text=_("Erdvės skiriamoji geba metrais. Atitinka dcat:spatialResolutionInMeters."),
    )

    applicable_legislation = models.ManyToManyField(
        ApplicableLegislation,
        verbose_name=_("Teisinis pagrindas"),
        related_name="datasets",
        blank=True,
    )
    follows = models.ManyToManyField(
        Rule,
        blank=True,
        related_name="datasets",
        verbose_name=_("Taisyklė"),
        help_text=_("Nurodo taisyklę, kuria vadovaujamasi. Atitinka cpsv:follows."),
    )
    license = models.ForeignKey(
        Licence,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name=_("Licencija"),
        help_text=_("Ši savybė nurodo licenciją, pagal kurią platinama duomenų paslauga. Atitinka dct:license."),
    )
    documentation = models.ManyToManyField(
        verbose_name=_("Dokumentacija"),
        to="Documentation",
        blank=True,
    )
    service_quality = models.ManyToManyField(
        ServiceQualityPage,
        blank=True,
        verbose_name=_("Paslaugos kokybė"),
        help_text=_("Tinklalapis su išsamia informacija apie teikiamos paslaugos kokybę. Atitinka foaf:page."),
    )
    provenance = models.ManyToManyField(
        ProvenanceStatement,
        blank=True,
        verbose_name=_("Kilmė"),
        help_text=_("Deklaracija apie duomenų rinkinio kilmę. Atitinka dct:provenance."),
    )
    was_generated_by = models.ManyToManyField(
        Activity,
        blank=True,
        verbose_name=_("Buvo sukurtas dėl"),
        help_text=_("Veikla, dėl kurios buvo sukurtas duomenų rinkinys. Atitinka prov:wasGeneratedBy."),
    )

    rights_relation = models.URLField(
        verbose_name=_("Teisės - Susijęs dokumentas"),
        max_length=1024,
        null=True,
        blank=True,
        help_text=_("Teisių deklaracijos nuoroda. Atitinka dct:rights / dct:relation."),
    )
    contact = models.ForeignKey(
        "Contact",
        on_delete=models.SET_NULL,
        verbose_name=_("Kontaktinis asmuo ar organizacija"),
        null=True,
        related_name="contact_datasets",
    )
    conforms_to = models.ForeignKey(
        Concept,
        on_delete=models.SET_NULL,
        verbose_name=_("Atitinka"),
        null=True,
        blank=True,
        help_text=_("Nurodo, kokį standartą atitinka išteklius. Atitinka dct:conformsTo"),
    )
    service_type = models.ManyToManyField(
        Concept,
        blank=True,
        related_name="dataset_service_types",
        verbose_name=_("Tipas"),
        help_text=_("Paslaugos tipas. Atitinka dct:type"),
    )
    dataset_type = models.ForeignKey(
        Concept,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="datasets",
        verbose_name=_("Tipas"),
        help_text=_("Duomenų rinkinio tipas. Atitinka dct:type."),
        limit_choices_to={"concept_schemas__uri": DATASET_TYPE_SCHEME_URI},
    )

    # TODO: To be removed:
    # ---------------------------8<-------------------------------------
    meta = models.TextField(blank=True, null=True)

    # TODO: https://github.com/atviriduomenys/katalogas/issues/9
    priority_score = models.IntegerField(
        blank=True,
        null=True,
    )

    # TODO: https://github.com/atviriduomenys/katalogas/issues/14
    structure_data = models.TextField(
        blank=True,
        null=True,
    )
    structure_filename = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    current_structure = models.ForeignKey(
        "DatasetStructure",
        models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )

    # TODO: https://github.com/atviriduomenys/katalogas/issues/26
    financed = models.BooleanField(
        blank=True,
        null=True,
    )
    financing_plan_id = models.BigIntegerField(
        blank=True,
        null=True,
    )
    financing_priorities = models.TextField(
        blank=True,
        null=True,
    )
    financing_received = models.BigIntegerField(
        blank=True,
        null=True,
    )
    financing_required = models.BigIntegerField(
        blank=True,
        null=True,
    )
    will_be_financed = models.BooleanField(
        blank=True,
        default=False,
    )
    # --------------------------->8-------------------------------------

    metadata = GenericRelation(
        "vitrina_structure.Metadata",
    )
    comments = GenericRelation(
        "vitrina_comments.Comment",
    )
    tasks = GenericRelation(
        "vitrina_tasks.Task",
    )
    representatives = GenericRelation(
        "vitrina_orgs.Representative",
    )
    request_objects = GenericRelation(
        "vitrina_requests.RequestObject",
    )

    objects = TranslatableMPNodeManager()
    public = PublicDatasetManager()
    restricted = PermittedDatasetManager()
    edp_public = EdpPublicDatasetManager()
    edp_restricted = EdpRestrictedDatasetManager()

    class Meta:
        db_table = "dataset"
        verbose_name = _("Dataset")
        unique_together = (("internal_id", "organization_id"),)

    def __str__(self):
        return self.safe_translation_getter("title", language_code=self.get_current_language()) or " "

    def save(self, *args, **kwargs) -> None:
        if not all((self.information_system_type_id, self.information_system_importance_id)):
            default_concept, _ = Concept.objects.get_or_create(
                code="NOT-SET",
                defaults={
                    "valid_since": make_aware(datetime(2020, 1, 1)),
                    "valid_until": None,
                    "label": "Nenurodyta",
                    "description": "Informacija nėra nurodyta",
                },
            )

            if not self.information_system_type_id:
                self.information_system_type = default_concept
            if not self.information_system_importance_id:
                self.information_system_importance = default_concept
        super().save(*args, **kwargs)

    def lt_title(self):
        return self.safe_translation_getter("title", language_code="lt")

    def en_title(self):
        return self.safe_translation_getter("title", language_code="en")

    def lt_description(self):
        return self.safe_translation_getter("description", language_code="lt")

    def en_description(self):
        return self.safe_translation_getter("description", language_code="en")

    def lt_subclass_title(self) -> str:
        return self.subclass.safe_translation_getter("title", language_code="lt")

    def en_subclass_title(self) -> str:
        return self.subclass.safe_translation_getter("title", language_code="en")

    def get_absolute_url(self):
        return reverse("dataset-detail", kwargs={"pk": self.pk})

    def _get_tags_from_cache_or_db(self) -> list[TagModel]:
        if not hasattr(self, "_cached_tags"):
            prefetched = getattr(self, "_prefetched_objects_cache", {})
            if "tags" in prefetched:
                self._cached_tags = list(prefetched["tags"])
            else:
                self._cached_tags = list(self.tags.all())
        return self._cached_tags

    def get_tag_object_list(self) -> list[dict]:
        tags = self._get_tags_from_cache_or_db()
        return [{"name": tag.name, "pk": tag.pk} for tag in tags]

    def get_tag_list(self) -> list[int]:
        tags = self._get_tags_from_cache_or_db()
        return [tag.pk for tag in tags]

    def get_tag_title(self, tag_id) -> str:
        if tag := self.tags.tag_model.objects.filter(pk=tag_id).first():
            return tag.name
        return ""

    def get_resource_titles(self) -> list[str]:
        return [dist.title for dist in self.datasetdistribution_set.all() if dist.title]

    def get_model_title_list(self) -> list[str]:
        return [model.title for model in self.model_set.all()]

    def get_model_name_list(self) -> list[str]:
        return [model.full_name for model in self.model_set.all() if model.name]

    def get_property_title_list(self) -> list[str]:
        return [prop.title for model in self.model_set.all() for prop in model.model_properties.all() if prop.title]

    def get_request_title_list(self) -> list[str]:
        return [request.title for request in self.dataset_request.all() if request.title]

    def get_project_title_list(self) -> list[str]:
        return [project.title for project in self.project_set.all()]

    def get_resource_description(self) -> list[str]:
        return [dist.description for dist in self.datasetdistribution_set.all() if dist.description]

    def get_model_title_description(self) -> list[str]:
        return [model.description for model in self.model_set.all()]

    def get_property_title_description(self) -> list[str]:
        return [
            prop.description
            for model in self.model_set.all()
            for prop in model.model_properties.all()
            if prop.description
        ]

    def get_request_title_description(self) -> list[str]:
        return [request.description for request in self.dataset_request.all() if request.description]

    def get_project_title_description(self) -> list[str]:
        return [project.description for project in self.project_set.all()]

    def get_all_groups(self):
        ids = (
            self.category.filter(datasetgroupcategoryuri__group__isnull=False)
            .values_list("datasetgroupcategoryuri__group__pk", flat=True)
            .distinct()
        )
        return DatasetGroup.objects.filter(pk__in=ids).exclude(pk__in=self.get_excluded_groups())

    def get_group_list(self) -> list[int]:
        excluded_pks = self.get_excluded_groups()
        group_pks = {
            uri.group_id
            for category in self.category.all()
            for uri in category.datasetgroupcategoryuri_set.all()
            if uri.group_id is not None and uri.group_id not in excluded_pks
        }
        return list(group_pks)

    def get_excluded_groups(self) -> list[int]:
        return [excluded_group.group_id for excluded_group in self.excluded_groups.all()]

    def get_parent_organization_title(self):
        if self.organization:
            if self.organization.is_root():
                return self.organization.title
            else:
                return self.organization.get_root().title
        return None

    def parent_category(self):
        parents = []
        for category in self.category.all():
            if not category.is_root():
                parents.append(category.get_root().pk)
            else:
                parents.append(category.pk)
        return parents

    def parent_category_titles(self):
        parents = []
        for category in self.category.all():
            if not category.is_root():
                parents.append(category.get_root().title)
            else:
                parents.append(category.title)
        return parents

    def get_category_object_list_lt(self):
        categories = []
        for category in self.category.all():
            categories = [
                {"title": cat.title, "pk": cat.pk} for cat in category.get_ancestors() if cat.dataset_set.exists()
            ]
            categories.append({"title": category.title, "pk": category.pk})
        return categories

    def get_category_object_list_en(self):
        categories = []
        for category in self.category.all():
            categories = [
                {"title_en": cat.title_en, "pk": cat.pk} for cat in category.get_ancestors() if cat.dataset_set.exists()
            ]
            categories.append({"title_en": category.title_en, "pk": category.pk})
        return categories

    def level(self):
        return randrange(5)

    def latest_version(self) -> Version:
        return self.dataset_version.order_by("-version").first()

    @property
    def formats(self):
        return [obj.get_format() for obj in self.datasetdistribution_set.all() if obj.get_format()]

    def filter_formats(self):
        formats = [obj.get_format().pk for obj in self.datasetdistribution_set.all() if obj.get_format()]

        if list(self.model_set.all()) and any(
            dist.format.extension == "UAPI" for dist in self.datasetdistribution_set.all() if dist.format
        ):
            from vitrina.resources.models import Format

            additional_formats = Format.objects.filter(title__in=["CSV", "JSON", "JSONL"]).values_list("pk", flat=True)
            formats.extend(additional_formats)
        return formats

    @property
    def distinct_formats(self):
        if self.is_part_of_dataservice() and self.model_set.all():
            from vitrina.resources.models import Format

            additional_formats = [
                Format.objects.get(title="CSV"),
                Format.objects.get(title="JSON"),
                Format.objects.get(title="JSONL"),
            ]
            return sorted(set(self.formats + additional_formats), key=lambda x: x.title)
        return sorted(set(self.formats), key=lambda x: x.title)

    @cached_property
    def dataset_content_type(self):
        return ContentType.objects.get_for_model(Dataset)

    def get_acl_parents(self):
        parents = [self]
        parents.extend(self.get_ancestors())
        if self.organization:
            parents.extend(self.organization.get_acl_parents())
        return parents

    def get_members_url(self):
        return reverse("dataset-members", kwargs={"pk": self.pk})

    def get_effective_user_role_via_organization(self, user: "User") -> str | None:
        """
        Determines the user's effective role on this dataset through organizational membership.
        Access is resolved indirectly: the user belongs to an organization which holds
        a Representative record on this dataset or one of its ancestors.
        The resulting role is capped by the user's own role within that organization.
        """
        organization_ct = ContentType.objects.get_for_model(Organization)

        user_org_map = dict(
            Representative.objects.filter(
                user=user,
                content_type=organization_ct,
            ).values_list("object_id", "role")
        )

        if not user_org_map:
            return None

        dataset_ct = self.dataset_content_type

        dataset_ids = {self.id}
        organization_ids = {self.organization_id}
        for parent in self.get_ancestors().only("pk", "organization_id"):
            dataset_ids.add(parent.pk)
            organization_ids.add(parent.organization_id)

        org_roles = Representative.objects.filter(
            Q(content_type=dataset_ct, object_id__in=dataset_ids)
            | Q(content_type=organization_ct, object_id__in=organization_ids),
            organization_id__in=user_org_map.keys(),
        ).values_list("organization_id", "role")

        effective_roles = []
        # Map coordinator roles to their manager equivalents before comparison
        coordinator_to_manager = dict(zip(Representative.COORDINATOR_ROLES, Representative.MANAGER_ROLES))

        for org_id, org_role in org_roles:
            user_role = coordinator_to_manager.get(user_org_map[org_id], user_org_map[org_id])
            if org_role not in Representative.MANAGER_ROLES or user_role not in Representative.MANAGER_ROLES:
                continue
            # Use the more restrictive role between the organization's role and the user's role within that org.
            # e.g. org has RESOURCE_MANAGER, user has OPEN_DATA_MANAGER → effective role is OPEN_DATA_MANAGER
            effective_roles.append(max(org_role, user_role, key=Representative.MANAGER_ROLES.index))

        if not effective_roles:
            return None

        # If the user represents multiple orgs, return the most privileged role across all of them.
        # e.g. ["open_data_manager", "resource_manager"] → "resource_manager"
        return min(effective_roles, key=Representative.MANAGER_ROLES.index)

    def get_managers_queryset(self, roles: list[str]) -> QuerySet["Dataset"]:
        dataset_ct = self.dataset_content_type
        organization_ct = ContentType.objects.get_for_model(Organization)

        dataset_ids = {self.id}
        organization_ids = {self.organization_id}
        for parent in self.get_ancestors().only("pk", "organization_id"):
            dataset_ids.add(parent.pk)
            organization_ids.add(parent.organization_id)
        return (
            Representative.objects.filter(
                Q(
                    content_type=dataset_ct,
                    object_id__in=dataset_ids,
                    role__in=roles,
                )
                | Q(
                    content_type=organization_ct,
                    object_id__in=organization_ids,
                    role__in=roles,
                ),
                user__isnull=False,
            )
            .values_list("user_id", flat=True)
            .distinct()
        )

    def _ensure_managers_cached(self) -> None:
        if hasattr(self, "_cached_resource_managers"):
            return

        resource_roles = {Representative.RESOURCE_COORDINATOR, Representative.RESOURCE_MANAGER}
        open_data_roles = {Representative.OPEN_DATA_COORDINATOR, Representative.OPEN_DATA_MANAGER}

        if self.depth == 1:
            ancestors = []
        else:
            ancestors = list(self.get_ancestors().only("pk", "organization_id"))

        if not ancestors:
            all_reps = list(self.representatives.all())
            if self.organization:
                all_reps.extend(self.organization.representatives.all())
        else:
            all_roles = resource_roles | open_data_roles
            dataset_ct = ContentType.objects.get_for_model(Dataset)
            organization_ct = ContentType.objects.get_for_model(Organization)

            dataset_ids = {self.id}
            organization_ids = {self.organization_id}
            for parent in ancestors:
                dataset_ids.add(parent.pk)
                organization_ids.add(parent.organization_id)

            all_reps = list(
                Representative.objects.filter(
                    Q(content_type=dataset_ct, object_id__in=dataset_ids, role__in=all_roles)
                    | Q(content_type=organization_ct, object_id__in=organization_ids, role__in=all_roles),
                    user__isnull=False,
                )
            )

        self._cached_resource_managers = {
            rep.user_id for rep in all_reps if rep.role in resource_roles and rep.user_id is not None
        }
        self._cached_open_data_managers = {
            rep.user_id for rep in all_reps if rep.role in open_data_roles and rep.user_id is not None
        }

    @property
    def resource_managers(self) -> set[int]:
        self._ensure_managers_cached()
        return self._cached_resource_managers

    @property
    def open_data_managers(self) -> set[int]:
        self._ensure_managers_cached()
        return self._cached_open_data_managers

    @property
    def language_array(self):
        if self.language:
            return [lang.replace(",", "") for lang in self.language.split(" ")]
        return []

    @property
    def tag_name_array(self):
        return [tag.name.strip() for tag in self.tags.tags]

    @property
    def category_titles(self):
        return self.category.values_list("title", flat=True)

    def jurisdiction(self) -> int | None:
        if self.organization and self.organization.jurisdiction:
            return self.organization.jurisdiction.pk
        return None

    def update_level(self):
        if metadata := self.metadata.first():
            levels = Metadata.objects.filter(
                dataset=self,
                content_type__in=[
                    ContentType.objects.get_for_model(Model),
                    ContentType.objects.get_for_model(Base),
                    ContentType.objects.get_for_model(Property),
                ],
                level__isnull=False,
            ).values_list("level", flat=True)

            if levels:
                metadata.average_level = sum(levels) / len(levels)
                metadata.save()

    def get_creators(self):
        return list(
            self.datasetattribution_set.filter(
                organization__isnull=False, attribution__name=Attribution.CREATOR
            ).values_list("organization__pk", flat=True)
        )

    def published_created_sort(self):
        return self.published or self.created

    def get_icon(self):
        root_category_ids = []
        for cat in self.category.all():
            root_category_ids.append(cat.get_root().pk)

        if root_category_ids:
            category = (
                Category.objects.filter(
                    pk__in=root_category_ids,
                    icon__isnull=False,
                )
                .order_by("title")
                .first()
            )
            if category:
                return category.icon
        return None

    def _get_first_metadata(self) -> Metadata | None:
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "metadata" in prefetched:
            if not hasattr(self, "_cached_first_metadata"):
                metadata_list = list(self.metadata.all())
                self._cached_first_metadata = metadata_list[0] if metadata_list else None
            return self._cached_first_metadata
        else:
            return self.metadata.first()

    @property
    def name(self):
        if metadata := self._get_first_metadata():
            return metadata.name
        return ""

    def get_level(self) -> int | None:
        if metadata := self._get_first_metadata():
            return metadata.average_level
        return None

    @property
    def identifier(self) -> str | None:
        from vitrina.identifiers.models import Agency

        return (
            identifier.notation
            if (identifier := self.identifiers.filter(scheme_agency__code=Agency.RISR_CODE).first())
            else None
        )

    def public_types(self) -> list[int]:
        return [t.pk for t in self.type.all() if t.show_filter]

    def type_order(self):
        order = 0
        related_datasets = self.related_datasets.all()
        part_of = self.part_of.all()
        if related_datasets and not part_of:
            order = 3
        elif related_datasets and part_of:
            order = 2
        elif part_of:
            order = 1
        return order

    def get_plan_title(self):
        if self.datasetdistribution_set.exists():
            return _("Duomenų rinkinio papildymas")
        return _("Duomenų atvėrimas")

    def get_likes(self):
        from vitrina.likes.models import Like

        content_type = ContentType.objects.get_for_model(self)
        return Like.objects.filter(
            content_type=content_type,
            object_id=self.pk,
        ).count()

    def get_download_count(self):
        from vitrina.statistics.models import ModelDownloadStats

        model_names = Metadata.objects.filter(
            content_type=ContentType.objects.get_for_model(Model), dataset__pk=self.pk
        ).values_list("name", flat=True)
        return (ModelDownloadStats.objects.filter(model__in=model_names).aggregate(Sum("model_requests")))[
            "model_requests__sum"
        ] or 0

    def get_metadata_objects_for_version(self, metadata_version):
        meta_objects = []
        models = []
        props = []
        dataset_distributions = set()
        metadata = self.metadata.filter(metadata_version=metadata_version).first()
        dataset_param_item_metadata_ref = None
        dataset_enum_item_metadata_ref = None
        model_param_item_metadata_ref = None
        dataset_content_type_pk = ContentType.objects.get_for_model(Dataset).pk

        all_metadata_instances = (
            Metadata.objects.filter(dataset=self.pk, draft=True, metadata_version=metadata_version)
            .order_by("id")
            .select_related("metadata_version")
        )
        # TODO optimize by introducing manual collection of all related models.
        if metadata and metadata.draft is True:
            if latest_version := metadata.metadataversion_set.order_by("-version__created").first():
                if latest_version.name != metadata.name:
                    label = mark_safe(
                        f"<a href={self.get_absolute_url()}>{self.title}</a> name: "
                        f"<span class='tag is-danger is-light is-medium'>{latest_version.name}</span> -> "
                        f"<span class='tag is-success is-light is-medium'>{metadata.name}</span>"
                    )
                    meta_objects.append((metadata.pk, label))
            else:
                label = mark_safe(
                    f"<a href={self.get_absolute_url()}>{self.title}</a> name: "
                    f"<span class='tag is-success is-light is-medium'>{metadata.name}</span>"
                )
                meta_objects.append((metadata.pk, label))

        for metadata_instance in all_metadata_instances:
            metadata_model = metadata_instance.content_type.model
            if metadata_model == "prefix":
                label = mark_safe(
                    f"Prefix ref: "
                    f"<span class='tag is-success is-light is-medium model_metadata'>{metadata_instance.name}</span>"
                )

                meta_objects.append((metadata_instance.pk, label))

            if metadata_model == "paramitem":
                param_item_instance = (
                    ParamItem.objects.filter(metadata=metadata_instance).select_related("param").first()
                )
                if param_item_instance:
                    if param := param_item_instance.param:
                        if (
                            param.content_type_id == dataset_content_type_pk
                            and metadata_instance.metadata_version.status == VersionStatus.DRAFT
                        ):
                            if metadata_instance.ref:
                                dataset_param_item_metadata_ref = metadata_instance.ref
                            label = mark_safe(
                                f"Param ref:  <span class='tag is-success is-light is-medium model_metadata'>{dataset_param_item_metadata_ref}</span>"
                                f" prepare: <span class='tag is-success is-light is-medium'>{metadata_instance.prepare}</span>"
                            )
                            meta_objects.append((metadata_instance.pk, label))

            if metadata_model == "enumitem":
                enum_item_instance = EnumItem.objects.filter(metadata=metadata_instance).select_related("enum").first()
                if enum_item_instance:
                    if enum := enum_item_instance.enum:
                        if (
                            enum.content_type_id == dataset_content_type_pk
                            and metadata_instance.metadata_version.status == VersionStatus.DRAFT
                        ):
                            if metadata_instance.ref:
                                dataset_enum_item_metadata_ref = metadata_instance.ref
                            label = mark_safe(
                                f"Enum ref:  <span class='tag is-success is-light is-medium model_metadata'>{dataset_enum_item_metadata_ref}</span> "
                                f" prepare: <span class='tag is-success is-light is-medium'>{metadata_instance.prepare}</span>"
                            )
                            meta_objects.append((metadata_instance.pk, label))

        for model in self.model_set.all():
            dataset_distribution_for_model = model.distribution
            dataset_distribution_metadata = (
                dataset_distribution_for_model.metadata.first() if dataset_distribution_for_model else None
            )

            is_metadata_inside_expected_distributions = False
            is_version_draft = False

            if dataset_distribution_metadata:
                is_metadata_inside_expected_distributions = dataset_distribution_metadata.pk in dataset_distributions
                metadata_version_status = getattr(dataset_distribution_metadata.metadata_version, "status", None)
                is_version_draft = metadata_version_status == VersionStatus.DRAFT

            if (
                dataset_distribution_for_model
                and dataset_distribution_metadata
                and not is_metadata_inside_expected_distributions
                and is_version_draft
            ):
                label = mark_safe(
                    f"<a href={dataset_distribution_for_model.get_absolute_url()}>{dataset_distribution_metadata.name}</a> name: "
                    f"<span class='tag is-success is-light is-medium'>{dataset_distribution_metadata.name}</span>"
                )
                dataset_distributions.add(dataset_distribution_metadata.pk)
                meta_objects.append((dataset_distribution_metadata.pk, label))

            metadata = model.metadata.first()
            if metadata and metadata.draft is True:
                models.append(model)
                if latest_version := metadata.metadataversion_set.order_by("-version__created").first():
                    label_str = f"<a href='{model.get_absolute_url()}' class='model_metadata'>{model.name}</a>"
                    if latest_version.name != metadata.name:
                        label_str += (
                            f" name: <span class='tag is-danger is-light is-medium'>{latest_version.name}</span> ->"
                            f" <span class='tag is-success is-light is-medium'>{metadata.name}</span>"
                        )
                    if latest_version.status != metadata.status:
                        changes_to_message = metadata.status.codename
                        if metadata.status == Status.objects.filter(codename=StatusCode.DEVELOP).first():
                            completed_status = Status.objects.filter(codename=StatusCode.COMPLETED).first()
                            changes_to_message = f"{metadata.status.codename} -> {completed_status.codename}"

                        label_str += (
                            f" status: <span class='tag is-danger is-light is-medium'>{latest_version.status.codename}</span> ->"
                            f" <span class='tag is-success is-light is-medium'>{changes_to_message}</span>"
                        )
                    latest_version.ref = None if latest_version.ref == "" else latest_version.ref
                    metadata.ref = None if metadata.ref == "" else metadata.ref
                    if latest_version.ref != metadata.ref:
                        label_str += (
                            f" ref: <span class='tag is-danger is-light is-medium'>{latest_version.ref}</span> -> "
                            f"<span class='tag is-success is-light is-medium'>{metadata.ref}</span>"
                        )
                    if latest_version.level_given != metadata.level_given:
                        label_str += (
                            f" level: <span class='tag is-danger is-light is-medium'>{latest_version.level_given}"
                            f"</span> -> <span class='tag is-success is-light is-medium'>{metadata.level_given}"
                            f"</span>"
                        )
                    if latest_version.base != model.base:
                        label_str += (
                            f" base: <span class='tag is-danger is-light is-medium'>{latest_version.base}</span> ->"
                            f" <span class='tag is-success is-light is-medium'>{model.base.model.name}</span>"
                        )
                    label = mark_safe(label_str)
                    meta_objects.append((metadata.pk, label))
                else:
                    label_str = (
                        f"<a href='{model.get_absolute_url()}' class='model_metadata'>{model.name}</a>"
                        f" name: <span class='tag is-success is-light is-medium'>{metadata.name}</span>"
                    )
                    if metadata.ref:
                        label_str += f" ref: <span class='tag is-success is-light is-medium'>{metadata.ref}</span>"
                    if metadata.level_given:
                        label_str += (
                            f" level: <span class='tag is-success is-light is-medium'>{metadata.level_given}</span>"
                        )
                    if model.base:
                        label_str += (
                            f" base: <span class='tag is-success is-light is-medium'>{model.base.model.name}</span>"
                        )
                    label = mark_safe(label_str)
                    meta_objects.append((metadata.pk, label))

                if param := model.params.first():
                    for param_item in param.paramitem_set.all():
                        metadata = param_item.metadata.first()
                        if metadata and metadata.metadata_version.status == VersionStatus.DRAFT and metadata.ref:
                            model_param_item_metadata_ref = metadata.ref
                        label = mark_safe(
                            f"Param ref:  <span class='tag is-success is-light is-medium prop_metadata'>{model_param_item_metadata_ref}</span>"
                            f" prepare: <span class='tag is-success is-light is-medium'>{metadata.prepare}</span>"
                        )
                        meta_objects.append((metadata.pk, label))

            for prop in model.model_properties.all():
                metadata = prop.metadata.first()
                if metadata and metadata.draft is True:
                    props.append(prop)

                    if prop.model not in models:
                        label_str = (
                            f"<a href='{prop.model.get_absolute_url()}' class='model_metadata disabled'>"
                            f"{prop.model.name}</a> <small>({_('Jau įtraukta į versiją')})</small>"
                        )
                        label = mark_safe(label_str)
                        meta_objects.append((prop.model.metadata.first().pk, label))
                        models.append(prop.model)

                    if latest_version := metadata.metadataversion_set.order_by("-version__created").first():
                        label_str = f"<a href='{prop.get_absolute_url()}' class='prop_metadata'>{prop.name}</a>"
                        if latest_version.name != metadata.name:
                            label_str += (
                                f" name: <span class='tag is-danger is-light is-medium'>"
                                f"{latest_version.name}</span> ->"
                                f" <span class='tag is-success is-light is-medium'>{metadata.name}</span>"
                            )

                        if latest_version.status != metadata.status:
                            changes_to_message = metadata.status.codename
                            if metadata.status == Status.objects.filter(codename=StatusCode.DEVELOP).first():
                                completed_status = Status.objects.filter(codename=StatusCode.COMPLETED).first()
                                changes_to_message = f"{metadata.status.codename} -> {completed_status.codename}"

                            label_str += (
                                f" status: <span class='tag is-danger is-light is-medium'>"
                                f"{latest_version.status.codename}</span> ->"
                                f" <span class='tag is-success is-light is-medium'>{changes_to_message}</span>"
                            )
                        if latest_version.type_repr != metadata.type_repr:
                            label_str += (
                                f" type: <span class='tag is-danger is-light is-medium'>"
                                f"{latest_version.type_repr}</span> -> "
                                f"<span class='tag is-success is-light is-medium'>{metadata.type_repr}</span>"
                            )
                        latest_version.ref = None if latest_version.ref == "" else latest_version.ref
                        metadata.ref = None if metadata.ref == "" else metadata.ref
                        if latest_version.ref != metadata.ref:
                            label_str += (
                                f" ref: <span class='tag is-danger is-light is-medium'>"
                                f"{latest_version.ref}</span> -> "
                                f"<span class='tag is-success is-light is-medium'>{metadata.ref}</span>"
                            )
                        if latest_version.level_given != metadata.level_given:
                            label_str += (
                                f" level: <span class='tag is-danger is-light is-medium'>"
                                f"{latest_version.level_given}"
                                f"</span> -> <span class='tag is-success is-light is-medium'>"
                                f"{metadata.level_given}</span>"
                            )
                        if latest_version.access != metadata.access:
                            label_str += (
                                f" access: <span class='tag is-danger is-light is-medium'>"
                                f"{latest_version.get_access_display()}</span> ->"
                                f" <span class='tag is-success is-light is-medium'>"
                                f"{metadata.get_access_display()}</span>"
                            )
                        label = mark_safe(label_str)
                        meta_objects.append((metadata.pk, label))
                    else:
                        label_str = (
                            f"<a href='{prop.get_absolute_url()}' class='prop_metadata'>{prop.name}</a>"
                            f" name: <span class='tag is-success is-light is-medium'>{metadata.name}</span>"
                        )
                        if metadata.type:
                            label_str += (
                                f" type: <span class='tag is-success is-light is-medium'>{metadata.type_repr}</span>"
                            )
                        if metadata.ref:
                            label_str += f" ref: <span class='tag is-success is-light is-medium'>{metadata.ref}</span>"
                        if metadata.level_given:
                            label_str += (
                                f" level: <span class='tag is-success is-light is-medium'>{metadata.level_given}</span>"
                            )
                        if metadata.access:
                            label_str += (
                                f" access: <span class='tag is-success is-light is-medium'>"
                                f"{metadata.get_access_display()}</span>"
                            )
                        label = mark_safe(label_str)
                        meta_objects.append((metadata.pk, label))
                if enum := prop.enums.first():
                    for enum_item in enum.enumitem_set.all():
                        metadata = enum_item.metadata.first()
                        if metadata and metadata.draft is True:
                            if enum.object.model not in models:
                                label_str = (
                                    f"<a href='{enum.object.model.get_absolute_url()}' class='model_metadata disabled'>"
                                    f"{enum.object.model.name}</a> <small>({_('Jau įtraukta į versiją')})</small>"
                                )
                                label = mark_safe(label_str)
                                meta_objects.append((enum.object.model.metadata.first().pk, label))
                                models.append(enum.object.model)
                            if enum.object not in props:
                                label_str = (
                                    f"<a href='{enum.object.get_absolute_url()}' class='prop_metadata disabled'>"
                                    f"{enum.object.name}</a> <small>({_('Jau įtraukta į versiją')})</small>"
                                )
                                label = mark_safe(label_str)
                                meta_objects.append((enum.object.metadata.first().pk, label))
                                props.append(enum.object)

                            if latest_version := metadata.metadataversion_set.order_by("-version__created").first():
                                label_str = f"<a href='{prop.get_absolute_url()}' class='enum_metadata'>{enum_item}</a>"

                                latest_version.prepare = (
                                    None if latest_version.prepare == "" else latest_version.prepare
                                )
                                metadata.prepare = None if metadata.prepare == "" else metadata.prepare
                                if latest_version.prepare != metadata.prepare:
                                    label_str += (
                                        f" prepare: <span class='tag is-danger is-light is-medium'>"
                                        f"{latest_version.prepare}</span> ->"
                                        f" <span class='tag is-success is-light is-medium'>{metadata.prepare}</span>"
                                    )
                                latest_version.source = None if latest_version.source == "" else latest_version.source
                                metadata.source = None if metadata.source == "" else metadata.source
                                if latest_version.status != metadata.status:
                                    changes_to_message = metadata.status.codename
                                    if metadata.status == Status.objects.filter(codename=StatusCode.DEVELOP).first():
                                        completed_status = Status.objects.filter(codename=StatusCode.COMPLETED).first()
                                        changes_to_message = (
                                            f"{metadata.status.codename} -> {completed_status.codename}"
                                        )

                                    label_str += (
                                        f" status: <span class='tag is-danger is-light is-medium'>{latest_version.status.codename}</span> ->"
                                        f" <span class='tag is-success is-light is-medium'>{changes_to_message}</span>"
                                    )
                                if latest_version.source != metadata.source:
                                    label_str += (
                                        f" source: <span class='tag is-danger is-light is-medium'>"
                                        f"{latest_version.source}</span> -> "
                                        f"<span class='tag is-success is-light is-medium'>{metadata.source}</span>"
                                    )
                                label = mark_safe(label_str)
                                meta_objects.append((metadata.pk, label))
                            else:
                                label_str = f"<a href='{prop.get_absolute_url()}' class='enum_metadata'>{enum_item}</a>"
                                if metadata.prepare:
                                    label_str += (
                                        f" prepare: <span class='tag is-success is-light is-medium'>"
                                        f"{metadata.prepare}</span>"
                                    )
                                if metadata.source:
                                    label_str += (
                                        f" source: <span class='tag is-success is-light is-medium'>"
                                        f"{metadata.source}</span>"
                                    )
                                label = mark_safe(label_str)
                                meta_objects.append((metadata.pk, label))
        return meta_objects

    def save_translations(self, *args, **kwargs):
        super(Dataset, self).save_translations(*args, **kwargs)

        if not self.has_translation(language_code="en") or not self.en_title() or not self.en_description():
            lt_title = self.lt_title()
            lt_description = self.lt_description()

            if not self.has_translation(language_code="en"):
                self.create_translation(language_code="en")
            self.set_current_language("en")

            if lt_title and not self.en_title():
                self.title = translate_text(lt_title, f"dataset {self.id} title")

            if lt_description and not self.en_description():
                self.description = translate_text(lt_description, f"dataset {self.id} description")

    def get_main_contact(self):
        if contact := self.contact:
            return contact

        if self.publisher:
            return self._create_virtual_contact(self.publisher)

        return self._create_virtual_contact(self.organization)

    def _create_virtual_contact(self, org: Organization):
        content_type = ContentType.objects.get_for_model(org)
        contact = Contact(
            content_type=content_type,
            object_id=org.id,
            content_object=org,
            phone=org.phone if org.phone else None,
        )
        return contact

    def is_opened(self):
        return self.status == self.HAS_DATA

    def get_json_ld(self, model_url: str = None):
        formats: list = ["CSV", "JSON", "JSONL", "ASCII", "RDF"]
        json_ld = {
            "@context": "https://schema.org/",
            "@type": "Dataset",
            "name": self.title or None,
            "description": self.description or None,
            "url": self.get_absolute_url() or None,
            "creator": {
                "@type": "Organization",
                "name": str(self.organization) if self.organization else None,
            },
            "keywords": [tag["name"].strip() for tag in self.get_tag_object_list()] or None,
            "distribution": [
                {
                    "@type": "DataDownload",
                    "encodingFormat": fmt,
                    "contentUrl": f"{model_url}?format({fmt.lower()})",
                }
                for fmt in formats
            ]
            if model_url
            else None,
            "datePublished": str(self.published) if self.published else None,
            "isAccessibleForFree": self.is_public if self.is_public else None,
        }
        return json.dumps(json_ld, ensure_ascii=False)

    def is_part_of_dataservice(self):
        if self.datasetdistribution_set.filter(format__extension="UAPI").exists():
            return True
        return False

    def update_applicable_legislation(self, urls: list[str]) -> None:
        legislations: list[ApplicableLegislation] = []
        legislation_ids_to_update = []
        for url in urls:
            legislation, created = ApplicableLegislation.objects.get_or_create(url=url)
            if created:
                legislation_ids_to_update.append(legislation.uuid)
            legislations.append(legislation)
        update_applicable_legislation_description.delay(legislation_ids_to_update)
        self.applicable_legislation.set(legislations)

    def update_documentation(self, urls: list[str]) -> None:
        documentations: list[Documentation] = []

        for url in urls:
            documentation, created = Documentation.objects.get_or_create(documentation_link=url)
            documentations.append(documentation)

        self.documentation.set(documentations)

    def update_service_quality(self, urls: list[str]) -> None:
        service_qualities: list[ServiceQualityPage] = []

        for url in urls:
            service_quality, created = ServiceQualityPage.objects.get_or_create(url=url)
            service_qualities.append(service_quality)

        self.service_quality.set(service_qualities)

    def get_dependent_models(self, version: Version | None = None) -> list[dict]:
        """
        Get dependent (child) models for this dataset by querying the
        dsa_model_dependencies database view.
        """
        with connection.cursor() as cursor:
            model_dependency_query = """
                SELECT DISTINCT
                    root_model_id,
                    root_version_id,
                    child_model_id,
                    path,
                    depth,
                    root_dataset_id
                FROM dsa_model_dependencies
                WHERE root_dataset_id = %s
                ORDER BY root_model_id, depth DESC, child_model_id
            """

            versioned_model_dependency_query = """
                SELECT DISTINCT
                    root_model_id,
                    root_version_id,
                    child_model_id,
                    path,
                    depth,
                    root_dataset_id
                FROM dsa_model_dependencies
                WHERE root_dataset_id = %s
                    AND root_version_id = %s
                ORDER BY root_model_id, depth DESC, child_model_id
            """

            if version is not None:
                query = versioned_model_dependency_query
                params = [self.id, version.id]
            else:
                query = model_dependency_query
                params = [self.id]

            cursor.execute(query, params)
            columns = ["root_model_id", "root_version_id", "child_model_id", "path", "depth", "root_dataset_id"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_endpoint_urls(self) -> list[tuple[str | None, str]]:
        """Return endpoint URLs as a list of (url_name, url).

        If no agent is set, url_name is None.
        """
        if self.agent:
            return [
                (
                    environment.get_environment_display(),
                    environment.api_gate_server_url or environment.agent_address,
                )
                for environment in self.agent.environments.not_archived()
            ]

        return [(None, self.endpoint_url)]

    def get_endpoint_description(self) -> str | None:
        if self.agent:
            # TODO: Update to possibly different url once DataService OpenAPI export is implemented
            metadata_version = self.latest_version()
            return reverse("dataset-structure-export-openapi", args=[self.pk, metadata_version.pk])

        return self.endpoint_description


class DatasetReport(Dataset):
    class Meta:
        proxy = True
        verbose_name = _("Duomenų rinkinių atnaujinimo ataskaita")
        verbose_name_plural = _("Duomenų rinkinių atnaujinimo ataskaita")


# TODO: To be merged into Dataset:
#       https://github.com/atviriduomenys/katalogas/issues/22
# ---------------------------8<-------------------------------------
class GeoportalLtEntry(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    raw_data = models.TextField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "geoportal_lt_entry"


class OpenDataGovLtEntry(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    alt_title = models.TextField(blank=True, null=True)
    code = models.TextField(blank=True, null=True)
    contact_info = models.TextField(blank=True, null=True)
    data_extent = models.TextField(blank=True, null=True)
    data_trustworthiness = models.TextField(blank=True, null=True)
    dataset_begins = models.TextField(blank=True, null=True)
    dataset_conditions = models.TextField(blank=True, null=True)
    dataset_ends = models.TextField(blank=True, null=True)
    dataset_type = models.TextField(blank=True, null=True)
    date_meta_published = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    format = models.TextField(blank=True, null=True)
    keywords = models.TextField(blank=True, null=True)
    publisher = models.TextField(blank=True, null=True)
    refresh_period = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    topic = models.TextField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "open_data_gov_lt_entry"


class HarvestingResult(models.Model):
    published = models.BooleanField()
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    remote_id = models.CharField(max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    job = models.ForeignKey(HarvestingJob, models.CASCADE, blank=True, null=True)
    description_en = models.TextField(blank=True, null=True)
    keywords = models.TextField(blank=True, null=True)
    organization = models.TextField(blank=True, null=True)
    raw_data = models.TextField(blank=True, null=True)
    title_en = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = "harvesting_result"


# --------------------------->8-------------------------------------


# TODO: To be removed:
# ---------------------------8<-------------------------------------
class DatasetMigrate(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    catalog_id = models.BigIntegerField(blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    licence_id = models.BigIntegerField(blank=True, null=True)
    organization_id = models.BigIntegerField(blank=True, null=True)
    representative_id = models.BigIntegerField(blank=True, null=True)
    tags = models.TextField(blank=True, null=True)
    theme = models.CharField(max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    version = models.IntegerField()
    update_frequency = models.CharField(max_length=255, blank=True, null=True)
    internal_id = models.CharField(max_length=255, blank=True, null=True)
    origin = models.CharField(max_length=255, blank=True, null=True)
    published = models.DateTimeField(blank=True, null=True)
    language = models.CharField(max_length=255, blank=True, null=True)
    temporal_coverage = models.CharField(max_length=255, blank=True, null=True)
    spatial_coverage = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.BooleanField(blank=True, null=True)
    meta = models.TextField(blank=True, null=True)
    coordinator_id = models.BigIntegerField(blank=True, null=True)
    financed = models.BooleanField(blank=True, null=True)
    financing_plan_id = models.BigIntegerField(blank=True, null=True)
    financing_priorities = models.TextField(blank=True, null=True)
    financing_received = models.BigIntegerField(blank=True, null=True)
    financing_required = models.BigIntegerField(blank=True, null=True)
    priority_score = models.IntegerField(blank=True, null=True)
    slug = models.CharField(max_length=255, blank=True, null=True)
    soft_deleted = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    will_be_financed = models.BooleanField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "dataset_migrate"


class DatasetRemark(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    author = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    dataset = models.ForeignKey(Dataset, models.CASCADE, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "dataset_remark"


class DatasetResource(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    data = models.TextField(blank=True, null=True)
    dataset_id = models.BigIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    filename = models.TextField(blank=True, null=True)
    issued = models.CharField(max_length=255, blank=True, null=True)
    mime = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    spatial_coverage = models.CharField(max_length=255, blank=True, null=True)
    temporal_coverage = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "dataset_resource"


# TODO: https://github.com/atviriduomenys/katalogas/issues/59
class DatasetEvent(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    dataset_id = models.BigIntegerField(blank=True, null=True)
    details = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    user = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    user_0 = models.ForeignKey(
        User, models.CASCADE, db_column="user_id", blank=True, null=True
    )  # Field renamed because of name conflict.

    class Meta:
        db_table = "dataset_event"


class DatasetResourceMigrate(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    data = models.TextField(blank=True, null=True)
    dataset_id = models.BigIntegerField(blank=True, null=True)
    filename = models.TextField(blank=True, null=True)
    mime = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    version = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    temporal = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    spatial = models.CharField(max_length=255, blank=True, null=True)
    spatial_coverage = models.CharField(max_length=255, blank=True, null=True)
    temporal_coverage = models.CharField(max_length=255, blank=True, null=True)
    issued = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "dataset_resource_migrate"


class DatasetStructureLink(models.Model):
    name = models.CharField(max_length=255, blank=True)
    dataset_id = models.IntegerField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = "dataset_structure_link"


# TODO: https://github.com/atviriduomenys/katalogas/issues/14
class DatasetStructure(models.Model):
    UPLOAD_TO = "data/structure"

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    title = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey(
        Dataset,
        models.SET_NULL,
        blank=True,
        null=True,
    )
    file = FilerFileField(blank=True, null=True, related_name="file_structure", on_delete=models.SET_NULL)

    # Deprecatd feilds
    standardized = models.BooleanField(blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    distribution_version = models.IntegerField(blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)

    class Meta:
        db_table = "dataset_structure"

    def __str__(self):
        if self.dataset and self.dataset.metadata.first():
            if self.dataset.metadata.first().title:
                return self.dataset.metadata.first().title
            else:
                return self.dataset.metadata.first().name
        else:
            return str(_("Struktūra"))

    def get_absolute_url(self):
        metadata_version = self.dataset.metadata.last().metadata_version
        return reverse("dataset-structure", kwargs={"pk": self.dataset.pk, "version_id": metadata_version.pk})

    def file_size(self):
        if self.file:
            return self.file.size
        return 0

    def filename_without_path(self):
        return pathlib.Path(self.file.file.name).name if self.file and self.file.file else ""

    def get_acl_parents(self):
        return [self.dataset]


# TODO: https://github.com/atviriduomenys/katalogas/issues/14
class DatasetStructureField(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    data_title = models.CharField(max_length=255, blank=True, null=True)
    db_table_name = models.CharField(max_length=255, blank=True, null=True)
    order_id = models.IntegerField()
    scheme = models.CharField(max_length=255, blank=True, null=True)
    standard_title = models.CharField(max_length=255, blank=True, null=True)
    technical_title = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    dataset = models.ForeignKey(Dataset, models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = "dataset_structure_field"


# TODO: https://github.com/atviriduomenys/katalogas/issues/60
class DatasetVisit(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    last_visited = models.DateTimeField(blank=True, null=True)
    visit_count = models.IntegerField()
    dataset = models.ForeignKey(Dataset, models.SET_NULL, blank=True, null=True)

    class Meta:
        db_table = "dataset_visit"


# TODO: https://github.com/atviriduomenys/katalogas/issues/60
class HarvestedVisit(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    last_visited = models.DateTimeField(blank=True, null=True)
    visit_count = models.IntegerField()
    harvesting_result = models.ForeignKey(HarvestingResult, models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = "harvested_visit"


# --------------------------->8-------------------------------------


class Attribution(models.Model):
    CREATOR = "creator"
    CONTRIBUTOR = "contributor"
    PUBLISHER = "publisher"

    name = models.CharField(_("Kodinis pavadinimas"), max_length=255)
    uri = models.CharField(_("Ryšio identifikatorius"), max_length=255, blank=True)
    title = models.CharField(_("Pavadinimas"), max_length=255, blank=True)

    class Meta:
        db_table = "attribution"

    def __str__(self):
        return self.title if self.title else self.name


class DatasetAttribution(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, verbose_name=_("Duomenų rinkinys"))
    attribution = models.ForeignKey(Attribution, on_delete=models.PROTECT, verbose_name=_("Priskyrimo rūšis"))
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Organizacija"),
    )
    agent = models.CharField(_("Agentas"), max_length=255, null=True, blank=True)

    class Meta:
        db_table = "dataset_attribution"

    def __str__(self):
        if self.organization:
            return f"{self.attribution} - {self.dataset}, {self.organization}"
        else:
            return f"{self.attribution} - {self.dataset}, {self.agent}"


class Type(TranslatableModel):
    SERIES = "series"
    SERVICE = "service"

    name = models.CharField(_("Kodinis pavadinimas"), max_length=255)
    uri = models.CharField(_("Nuoroda į kontroliuojamą žodyną"), max_length=255, blank=True)
    translations = TranslatedFields(
        title=models.CharField(_("Pavadinimas"), max_length=255),
    )
    description = models.TextField(_("Apibūdinimas"), blank=True)
    show_filter = models.BooleanField(_("Rodyti filtre"), default=False)

    class Meta:
        db_table = "type"
        verbose_name = _("Tipas")
        verbose_name_plural = _("Tipai")

    def __str__(self):
        return self.safe_translation_getter("title", language_code=self.get_current_language())


class DCATResourceSubclass(TranslatableModel, UUIDBaseModel):
    SERIES = "series"
    SERVICE = "service"
    DATASET = "dataset"
    INFORMATION_SYSTEM = "information_system"
    CATALOG = "catalog"

    name = models.CharField(_("Kodinis pavadinimas"), max_length=255, unique=True)
    uri = models.CharField(_("Nuoroda į kontroliuojamą žodyną"), max_length=255, blank=True)

    translations = TranslatedFields(
        title=models.CharField(max_length=255, verbose_name=_("Pavadinimas")),
        description=models.TextField(verbose_name=_("Aprašymas")),
    )

    class Meta:
        verbose_name = _("Duomenų ištekliaus poklasis")
        verbose_name_plural = _("Duomenų išteklių poklasiai")

    def __str__(self):
        return self.name

    @property
    def translated_title(self) -> str:
        return self.safe_translation_getter("title", language_code=self.get_current_language())

    @property
    def translated_description(self) -> str:
        return self.safe_translation_getter("description", language_code=self.get_current_language())

    @property
    def is_information_system(self) -> bool:
        return self.name == DCATResourceSubclass.INFORMATION_SYSTEM

    @property
    def is_dataset(self) -> bool:
        return self.name == DCATResourceSubclass.DATASET

    @property
    def is_catalog(self) -> bool:
        return self.name == DCATResourceSubclass.CATALOG


class Documentation(UUIDBaseModel):
    documentation_link = models.CharField(max_length=500, blank=True, unique=True)


class Relation(TranslatableModel):
    PART_OF = "part-of"
    SERIES = "series"
    SERVICE = "service"
    CATALOG = "hasPart"
    RELATES_TO_INFORMATION_SYSTEM = "relatesToInformationSystem"

    name = models.CharField(_("Kodinis pavadinimas"), max_length=255)
    uri = models.CharField(_("Nuoroda į kontroliuojamą žodyną"), max_length=255, blank=True)
    translations = TranslatedFields(
        title=models.CharField(_("Pavadinimas"), max_length=255),
        inversive_title=models.CharField(_("Atvirkštinio ryšio pavadinimas"), max_length=255),
    )

    class Meta:
        db_table = "relation"
        verbose_name = _("Ryšys")
        verbose_name_plural = _("Ryšiai")

    def __str__(self):
        return self.safe_translation_getter("title", language_code=self.get_current_language())


class DatasetRelation(models.Model):
    relation = models.ForeignKey(Relation, verbose_name=_("Ryšio tipas"), on_delete=models.PROTECT)
    dataset = models.ForeignKey(
        Dataset,
        verbose_name=_("Duomenų rinkinys"),
        on_delete=models.CASCADE,
        related_name="dataset_relations",
    )
    part_of = models.ForeignKey(
        Dataset,
        verbose_name=_("Priklauso rinkiniui"),
        on_delete=models.CASCADE,
        related_name="related_datasets",
    )

    class Meta:
        db_table = "dataset_relation"
        verbose_name = _("Duomenų rinkinių ryšys")
        verbose_name_plural = _("Duomenų rinkinių ryšiai")


class DatasetQualifiedRelation(UUIDBaseModel):
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        verbose_name=_("Duomenų rinkinys"),
        related_name="qualified_relations",
    )
    url = models.URLField(
        verbose_name=_("Nuoroda"),
        help_text=_(
            "Nuoroda į susijusį dokumentą, kuriame aprašytas šis duomenų rinkinys. "
            "Įprastai IS techninė specifikacija. Atitinka dcat:qualifiedRelation."
        ),
    )

    class Meta:
        verbose_name = _("Kvalifikuotas ryšys")
        verbose_name_plural = _("Kvalifikuoti ryšiai")


class DataServiceType(models.Model):
    title = models.CharField(_("Pavadinimas"), max_length=255)

    class Meta:
        db_table = "data_service_type"

    def __str__(self):
        return self.title


class DataServiceSpecType(models.Model):
    title = models.CharField(_("Pavadinimas"), max_length=255)

    class Meta:
        db_table = "data_service_spec_type"

    def __str__(self):
        return self.title


class DatasetStructureMapping(models.Model):
    dataset_id = models.IntegerField(blank=False, null=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    org = models.CharField(max_length=255, blank=True, null=True)
    checksum = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "dataset_structure_mapping"


class Contact(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        verbose_name=_("Organizacija"),
    )
    contact_name = models.CharField(_("Vardas Pavardė"), max_length=255, blank=True)
    position = models.CharField(_("Pareigos"), max_length=255, blank=True)
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type"),
        limit_choices_to={"model__in": ("organization", "user")},
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(verbose_name=_("Object ID"), null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    email = models.EmailField(_("Email"), blank=True)
    phone = models.CharField(_("Phone"), max_length=50, blank=True)

    class Meta:
        verbose_name = _("Kontaktas")
        verbose_name_plural = _("Kontaktai")
        constraints = [models.UniqueConstraint(fields=["email", "organization"], name="unique_email_per_organization")]

    def __str__(self):
        if self.content_type:
            if self.content_type.model == "organization":
                return self.content_object.title
            elif self.content_type.model == "user":
                return f"{self.content_object.get_full_name()} ({self.position})"
            return self.content_object.get_full_name()
        return f"{self.contact_name} ({self.position})"

    def get_email(self):
        if self.email:
            return self.email
        if hasattr(self.content_object, "email"):
            return self.content_object.email
        return ""

    def get_type(self):
        if self.content_type == ContentType.objects.get_for_model(Organization):
            return _("Organizacija")
        elif self.content_type == ContentType.objects.get_for_model(User):
            return _("Naudotojas")
        return _("Neregistruotas naudotojas")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_acl_parents(self):
        parents = [self]
        parents.extend(self.organization.get_acl_parents())
        if isinstance(self.content_object, Organization):
            parents.extend(self.content_object.get_acl_parents())
            return parents
        if isinstance(self.content_object, User) and self.content_object.organization:
            parents.extend(self.content_object.organization.get_acl_parents())
        return parents


class GeoportalDataServiceType(models.Model):
    data_service_type = models.ForeignKey(DataServiceType, verbose_name=_("API formatas"), on_delete=models.CASCADE)

    class Meta:
        db_table = "geoportal_data_service_type"
        verbose_name = _("Geoportalo API formatas")
        verbose_name_plural = _("Geoportalo API formatai")

    def __str__(self):
        return str(self.data_service_type)


class GeoportalDataServiceTypeValue(models.Model):
    geoportal_data_service_type = models.ForeignKey(
        GeoportalDataServiceType,
        verbose_name=_("Geoportalo API formatas"),
        on_delete=models.CASCADE,
    )
    value = models.CharField(_("Reikšmė"), max_length=255)

    class Meta:
        db_table = "geoportal_data_service_type_value"
        verbose_name = _("Geoportalo API formato reikšmė")
        verbose_name_plural = _("Geoportalo API formato reikšmės")

    def __str__(self):
        return self.value


class DatasetExcludedGroups(models.Model):
    dataset = models.ForeignKey("Dataset", on_delete=models.CASCADE, related_name="excluded_groups")
    group = models.ForeignKey("DatasetGroup", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("dataset", "group")
        db_table = "dataset_excluded_groups"

import builtins
import functools
import operator

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q, Max, Avg, QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from vitrina.classifiers.models import Status
from vitrina.models import UUIDBaseModel
from vitrina.structure import VersionStatus, VersionType, AccessType
from vitrina.structure.helpers import get_type_repr
from enum import Enum


class StatusCode(str, Enum):
    DEVELOP = "develop"
    COMPLETED = "completed"
    DISCONT = "discont"
    DEPRECATED = "deprecated"
    WITHDRAWN = "withdrawn"


class Prefix(models.Model):
    name = models.CharField(_("Pavadinimas"), max_length=255)
    uri = models.CharField(_("URI"), max_length=255)
    content_type = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        verbose_name=_("Objekto tipas"),
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(_("Objekto id"), null=True, blank=True)
    object = GenericForeignKey("content_type", "object_id")

    metadata = GenericRelation("Metadata")
    objects = models.Manager()
    metadata_version = models.ForeignKey("Version", models.SET_NULL, verbose_name=_("Versija"), null=True, blank=True)

    class Meta:
        db_table = "prefix"
        verbose_name = _("Prefiksas")
        verbose_name_plural = _("Prefiksai")

    def __str__(self):
        return self.name


class MetadataManager(models.Manager):
    def average_level(self):
        avg_level = self.exclude(average_level__isnull=True).aggregate(Avg("average_level"))["average_level__avg"]
        return round(avg_level) if avg_level is not None else None


class Metadata(models.Model):
    UNDEFINED = None
    PRIVATE = 0
    PROTECTED = 1
    PUBLIC = 2
    OPEN = 3
    PACKAGE = 2
    VISIBILITY_PUBLIC = 3

    uuid = models.CharField(_("Id"), max_length=255)
    name = models.CharField(_("Vardas"), max_length=400, blank=True)
    type = models.CharField(_("Tipas"), max_length=255, blank=True)
    ref = models.CharField(_("Ryšys"), max_length=255, blank=True, null=True)
    source = models.CharField(_("Šaltinis"), max_length=255, blank=True, null=True)
    prepare = models.CharField(_("Formulė"), max_length=255, blank=True, null=True)
    prepare_ast = models.JSONField(_("Formulės AST"), blank=True, null=True)
    level = models.IntegerField(_("Brandos lygis"), null=True, blank=True)
    level_given = models.IntegerField(_("Duotas brandos lygis"), null=True, blank=True)
    average_level = models.IntegerField(_("Apskaičiuotas brandos lygis"), null=True, blank=True)
    access = models.IntegerField(
        _("Prieiga"),
        choices=AccessType.choices,
        blank=True,
        null=True,
    )
    visibility = models.PositiveIntegerField(
        _("Metaduomenų matomumas"), null=True, blank=True, validators=[MaxValueValidator(3)]
    )
    eli = models.URLField(_("Europos teisės akto identifikatorius (ELI)"), blank=True, null=True, max_length=500)
    status = models.ForeignKey(Status, models.SET_NULL, verbose_name=_("Būsena"), null=True, blank=True)
    count = models.PositiveIntegerField(_("Eilučių kiekis"), null=True, blank=True)
    prefix = models.ForeignKey(Prefix, models.SET_NULL, verbose_name=_("Prefiksas"), null=True, blank=True)
    uri = models.CharField(_("Žodyno atitikmuo"), max_length=255, blank=True)
    version = models.IntegerField(_("Versija"), blank=True)
    title = models.TextField(_("Pavadinimas"), blank=True, null=True)
    description = models.TextField(_("Aprašymas"), blank=True, null=True)
    order = models.IntegerField(_("Rikiavimo tvarka"), null=True, blank=True)
    content_type = models.ForeignKey(ContentType, models.CASCADE, verbose_name=_("Objekto tipas"))
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey("content_type", "object_id")
    dataset = models.ForeignKey("vitrina_datasets.Dataset", models.CASCADE, verbose_name=_("Duomenų rinkinys"))
    required = models.BooleanField(_("Privalomas"), null=True, blank=True)
    unique = models.BooleanField(_("Unikalus"), null=True, blank=True)
    type_args = models.CharField(_("Tipo argumentai"), max_length=255, null=True, blank=True)
    metadata_version = models.ForeignKey("Version", verbose_name=_("Versija"), on_delete=models.CASCADE, null=True)
    draft = models.BooleanField(
        _("Priskirta versijai"),
        default=True,
    )

    objects = MetadataManager()

    class Meta:
        db_table = "metadata"
        verbose_name = _("Metaduomenys")

    def __str__(self):
        return self.name

    @property
    def uri_link(self):
        link = None
        if self.uri:
            if "://" in self.uri:
                link = self.uri
            elif ":" in self.uri:
                prefix, name = self.uri.split(":", 1)
                if prefix := Prefix.objects.filter(
                    Q(name=prefix, metadata__dataset=self.dataset) | Q(name=prefix, object_id=None, content_type=None)
                ).first():
                    link = f"{prefix.uri}{name}"
        return link

    @property
    def type_repr(self):
        if self.type:
            return get_type_repr(self)
        return ""


class Base(models.Model):
    model = models.ForeignKey(
        "Model",
        models.CASCADE,
        verbose_name=_("Paveldimas modelis"),
        related_name="ref_model_base",
    )

    metadata = GenericRelation("Metadata")
    property_list = GenericRelation("PropertyList")
    objects = models.Manager()
    metadata_version = models.ForeignKey("Version", models.SET_NULL, verbose_name=_("Versija"), null=True, blank=True)

    class Meta:
        db_table = "base"
        verbose_name = _("Bazė")

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ""


class Model(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    dataset = models.ForeignKey("vitrina_datasets.Dataset", models.CASCADE, verbose_name=_("Duomenų rinkinys"))
    distribution = models.ForeignKey(
        "vitrina_resources.DatasetDistribution",
        models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Duomenų šaltinis"),
    )
    base = models.ForeignKey(
        "Base",
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Bazė"),
        related_name="base_models",
    )
    is_parameterized = models.BooleanField(default=False, verbose_name=_("Parametrizuotas"))

    objects = models.Manager()
    metadata = GenericRelation("Metadata")
    property_list = GenericRelation("PropertyList")
    params = GenericRelation("Param")
    requests = GenericRelation("vitrina_requests.RequestObject")
    metadata_version = models.ForeignKey("Version", models.SET_NULL, verbose_name=_("Versija"), null=True, blank=True)

    class Meta:
        db_table = "model"
        verbose_name = _("Modelis")

    def _get_first_metadata(self) -> Metadata | None:
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "metadata" in prefetched:
            if not hasattr(self, "_cached_first_metadata"):
                metadata_list = list(self.metadata.all())
                self._cached_first_metadata = metadata_list[0] if metadata_list else None
            return self._cached_first_metadata
        return self.metadata.first()

    def __str__(self) -> str:
        if metadata := self._get_first_metadata():
            return metadata.name
        return ""

    @property
    def name(self) -> str:
        if metadata := self._get_first_metadata():
            return metadata.name.split("/")[-1]
        return ""

    @property
    def full_name(self) -> str:
        if metadata := self._get_first_metadata():
            return metadata.name
        return ""

    @property
    def title(self) -> str:
        if metadata := self._get_first_metadata():
            return metadata.title
        return ""

    @property
    def description(self) -> str:
        if metadata := self._get_first_metadata():
            return metadata.description
        return ""

    @property
    def visibility(self) -> int | None:
        if metadata := self._get_first_metadata():
            return metadata.visibility
        return None

    def update_level(self) -> None:
        if metadata := self.metadata.first():
            prop_ids = self.model_properties.values_list("pk", flat=True)
            where = [
                Q(
                    content_type=ContentType.objects.get_for_model(Model),
                    object_id=self.pk,
                ),
                Q(
                    content_type=ContentType.objects.get_for_model(Property),
                    object_id__in=prop_ids,
                ),
            ]
            if self.base:
                where.append(
                    Q(
                        content_type=ContentType.objects.get_for_model(Base),
                        object_id=self.base.pk,
                    )
                )
            where = functools.reduce(operator.or_, where)
            levels = Metadata.objects.filter(where, level__isnull=False).values_list("level", flat=True)
            if levels:
                metadata.average_level = round(sum(levels) / len(levels))
                metadata.save()

    def get_absolute_url(self) -> str | None:
        if self.name:
            return reverse(
                "model-structure",
                kwargs={"pk": self.dataset.pk, "model": self.name, "version_id": self.metadata_version.pk},
            )
        return None

    def get_data_url(self) -> str | None:
        if self.name:
            return reverse(
                "model-data",
                kwargs={"pk": self.dataset.pk, "model": self.name, "version_id": self.metadata_version.pk},
            )
        return None

    def get_api_url(self) -> str | None:
        if self.name:
            return reverse(
                "getall-api", kwargs={"pk": self.dataset.pk, "version_id": self.metadata_version.pk, "model": self.name}
            )
        return None

    def get_given_props(self) -> QuerySet:
        return self.model_properties.filter(given=True).order_by("metadata__order")

    def get_props_excluding_base(self) -> QuerySet:
        base_props = []
        for props in self.get_base_props().values():
            base_props.extend(props.values_list("metadata__name", flat=True))

        return self.get_given_props().exclude(metadata__name__in=base_props)

    def get_acl_parents(self) -> list:
        return [self.dataset]

    def get_base_props(self) -> dict:
        base = self.base
        base_props = {}
        while base:
            base_props[base.model] = base.model.get_given_props()
            base = base.model.base
        return base_props

    @property
    def access_display_value(self) -> str:
        access = Model.objects.annotate(access=Max("model_properties__metadata__access")).get(pk=self.pk).access
        if access is not None:
            for type in AccessType.choices:
                if type[0] == access:
                    return type[1]
        return ""

    def is_opened(self) -> bool:
        return self.dataset.is_opened()

    def save(self, *args, **kwargs) -> None:
        if self.distribution and self.distribution.format and self.distribution.format.extension == "UAPI":
            raise ValidationError(_("Negalima priskirti Saugyklos API distribucijos. Pasirinkite kitą distribuciją."))
        existing_distribution = None

        if self.pk:
            old_instance = Model.objects.get(pk=self.pk)
            existing_distribution = old_instance.distribution

        super().save(*args, **kwargs)

        if self.distribution:
            if self.distribution.metadata_version and self.distribution.metadata_version != self.metadata_version:
                return
            self.distribution.create_or_reuse_metadata_instance_and_assign_version(self.metadata_version.pk)
            self.distribution.metadata_version = self.metadata_version
            self.distribution.save(update_fields=["metadata_version"])

        if existing_distribution:
            existing_distribution.delete_resource_metadata_if_has_no_models()

    def delete(self, *args, **kwargs) -> None:
        distribution = self.distribution
        super().delete(*args, **kwargs)
        if distribution:
            distribution.delete_resource_metadata_if_has_no_models()


class Property(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    model = models.ForeignKey(
        Model,
        models.CASCADE,
        verbose_name=_("Modelis"),
        related_name="model_properties",
    )
    ref_model = models.ForeignKey(
        Model,
        models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Susijęs modelis"),
        related_name="ref_model_properties",
    )
    property = models.ForeignKey(
        "Property",
        models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Tėvinė savybė"),
        related_name="child_properties",
    )
    given = models.BooleanField(_("Duota savybė"), default=True)

    objects = models.Manager()
    metadata = GenericRelation("Metadata")
    property_list = GenericRelation("PropertyList")
    enums = GenericRelation("Enum")
    requests = GenericRelation("vitrina_requests.RequestObject")
    metadata_version = models.ForeignKey("Version", models.SET_NULL, verbose_name=_("Versija"), null=True, blank=True)

    class Meta:
        db_table = "property"
        verbose_name = _("Savybė")

    def _get_first_metadata(self) -> Metadata | None:
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "metadata" in prefetched:
            if not hasattr(self, "_cached_first_metadata"):
                metadata_list = list(self.metadata.all())
                self._cached_first_metadata = metadata_list[0] if metadata_list else None
            return self._cached_first_metadata
        return self.metadata.first()

    def __str__(self):
        if metadata := self._get_first_metadata():
            return metadata.name
        return ""

    def get_absolute_url(self):
        if self.model.name and self.name:
            return reverse(
                "property-structure",
                kwargs={
                    "pk": self.model.dataset.pk,
                    "model": self.model.name,
                    "prop": self.name,
                    "version_id": self.metadata_version.pk,
                },
            )
        return None

    @builtins.property
    def name(self):
        if metadata := self._get_first_metadata():
            return metadata.name
        return ""

    @builtins.property
    def title(self):
        if metadata := self._get_first_metadata():
            return metadata.title
        return ""

    @builtins.property
    def description(self):
        if metadata := self._get_first_metadata():
            return metadata.description
        return ""

    @builtins.property
    def visibility(self) -> int | None:
        if metadata := self._get_first_metadata():
            return metadata.visibility
        return None

    def get_acl_parents(self):
        return [self.model.dataset]

    def is_opened(self):
        return self.model.dataset.is_opened()


class PropertyList(models.Model):
    property = models.ForeignKey("Property", models.CASCADE, verbose_name=_("Savybė"))
    order = models.IntegerField(_("Rikiavimo tvarka"))
    content_type = models.ForeignKey(
        ContentType,
        models.CASCADE,
        verbose_name=_("Objekto tipas"),
    )
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey("content_type", "object_id")

    objects = models.Manager()
    metadata_version = models.ForeignKey("Version", models.SET_NULL, verbose_name=_("Versija"), null=True, blank=True)

    class Meta:
        db_table = "property_list"
        verbose_name = _("Savybių sąrašas")

    def __str__(self):
        return str(self.property)


class Enum(models.Model):
    name = models.CharField(_("Pavadinimas"), max_length=255)
    content_type = models.ForeignKey(
        ContentType,
        models.CASCADE,
        verbose_name=_("Objekto tipas"),
    )
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey("content_type", "object_id")

    metadata = GenericRelation("Metadata")
    objects = models.Manager()
    metadata_version = models.ForeignKey("Version", models.SET_NULL, verbose_name=_("Versija"), null=True, blank=True)

    class Meta:
        db_table = "enum"
        verbose_name = _("Pasirinkimų sąrašas")

    def __str__(self):
        return self.name


class EnumItem(models.Model):
    enum = models.ForeignKey(Enum, models.CASCADE, verbose_name=_("Pasirinkimų sąrašas"))

    metadata = GenericRelation("Metadata")
    objects = models.Manager()
    metadata_version = models.ForeignKey("Version", models.SET_NULL, verbose_name=_("Versija"), null=True, blank=True)

    class Meta:
        db_table = "enum_item"
        verbose_name = _("Pasirinkimas")

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.prepare
        return ""


class Param(models.Model):
    name = models.CharField(_("Pavadinimas"), max_length=255)
    content_type = models.ForeignKey(
        ContentType,
        models.CASCADE,
        verbose_name=_("Objekto tipas"),
    )
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey("content_type", "object_id")

    metadata = GenericRelation("Metadata")
    objects = models.Manager()
    metadata_version = models.ForeignKey("Version", models.SET_NULL, verbose_name=_("Versija"), null=True, blank=True)

    class Meta:
        db_table = "param"
        verbose_name = _("Parametras")

    def __str__(self):
        return self.name


class ParamItem(models.Model):
    param = models.ForeignKey(Param, models.CASCADE, verbose_name=_("Parametras"))

    metadata = GenericRelation("Metadata")
    objects = models.Manager()
    metadata_version = models.ForeignKey("Version", models.SET_NULL, verbose_name=_("Versija"), null=True, blank=True)

    class Meta:
        db_table = "param_item"
        verbose_name = _("Parametro dalis")

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ""


class Version(models.Model):
    dataset = models.ForeignKey(
        "vitrina_datasets.Dataset",
        verbose_name=_("Duomenų rinkinys"),
        on_delete=models.CASCADE,
        related_name="dataset_version",
    )
    version = models.IntegerField(_("Versija"), null=True, blank=True)
    created = models.DateTimeField(_("Sukūrimo data"), auto_now_add=True)
    released = models.DateField(_("Išleidimo data"), null=True, blank=True)
    description = models.TextField(_("Aprašymas"), null=True, blank=True)
    deployed = models.DateTimeField(_("Įkėlimo į saugyklą data"), null=True, blank=True)
    status = models.CharField(_("Versijos būsena"), max_length=20, choices=VersionStatus.choices, null=True)
    version_type = models.CharField(
        _("Versijos tipas"), max_length=20, choices=VersionType.choices, null=True, blank=True
    )
    external_version = models.CharField(_("Versijos numeris"), max_length=50, null=True, blank=True)
    major = models.IntegerField(_("Pagrindinis versijos numeris"), null=True, blank=True)
    minor = models.IntegerField(_("Papildomas versijos numeris"), null=True, blank=True)
    patch = models.IntegerField(_("Pataisos versijos numeris"), null=True, blank=True)

    class Meta:
        db_table = "version"
        verbose_name = _("Versija")
        unique_together = (("dataset", "version"),)

    def get_absolute_url(self):
        return reverse("version-detail", kwargs={"pk": self.dataset.pk, "version_id": self.pk})

    def is_draft(self) -> bool:
        return self.status == VersionStatus.DRAFT

    def __str__(self):
        return f"v{self.version}"


class MetadataVersion(models.Model):
    UNDEFINED = None
    PRIVATE = 0
    PROTECTED = 1
    PUBLIC = 2
    OPEN = 3

    version = models.ForeignKey(Version, verbose_name=_("Versija"), on_delete=models.CASCADE)
    metadata = models.ForeignKey(Metadata, verbose_name=_("Metaduomenys"), on_delete=models.CASCADE)

    # Metadata changes that are included in version
    name = models.CharField(_("Vardas"), max_length=255, blank=True, null=True)
    type = models.CharField(_("Tipas"), max_length=255, blank=True, null=True)
    required = models.BooleanField(_("Privalomas"), null=True, blank=True)
    unique = models.BooleanField(_("Unikalus"), null=True, blank=True)
    type_args = models.CharField(_("Tipo argumentai"), max_length=255, null=True, blank=True)
    ref = models.CharField(_("Ryšys"), max_length=255, blank=True, null=True)
    source = models.CharField(_("Šaltinis"), max_length=255, blank=True, null=True)
    prepare = models.CharField(_("Formulė"), max_length=255, blank=True, null=True)
    level_given = models.IntegerField(_("Duotas brandos lygis"), null=True, blank=True)
    access = models.IntegerField(_("Prieiga"), choices=AccessType.choices, blank=True, null=True)
    base = models.ForeignKey(
        "Base",
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Bazė"),
    )
    status = models.ForeignKey(Status, models.PROTECT, verbose_name=_("Būsena"), null=True, blank=True)

    class Meta:
        db_table = "metadata_version"
        verbose_name = _("Metaduomenų versija")
        unique_together = (("metadata", "version"),)

    @property
    def type_repr(self):
        if self.type:
            return get_type_repr(self)
        return ""


class ValidationStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    VALID = "VALID", _("Valid")
    INVALID = "INVALID", _("Invalid")


class ManifestValidationEntry(UUIDBaseModel):
    manifest_file = models.FileField(upload_to="manifest_files/", verbose_name="Manifest File")
    validation_status = models.CharField(
        max_length=10, choices=ValidationStatus.choices, default=ValidationStatus.PENDING
    )
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Manifest [{self.pk}] - {self.validation_status}"

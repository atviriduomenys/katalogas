import logging
import pathlib
from enum import StrEnum
import uuid
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from filer.fields.file import FilerFileField
from parler.managers import TranslatableManager
from parler.models import TranslatableModel, TranslatedFields

from vitrina.classifiers.models import Licence, ApplicableLegislation, Concept
from vitrina.structure import AccessType
from vitrina.structure.models import Metadata, Version
from vitrina.helpers import get_file_extension
from vitrina.utils import translate_text
from vitrina.datasets.tasks import update_applicable_legislation_description

logger = logging.getLogger()


def get_default_status() -> uuid.UUID:
    return Concept.objects.get(uri="http://publications.europa.eu/resource/authority/distribution-status/DEVELOP").pk


class FormatName(StrEnum):
    API = "API"
    UAPI = "UAPI"


class Format(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    # See FormatName for some values used in code.
    extension = models.TextField(_("Failo plėtinys"), blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    mimetype = models.TextField(_("MIME tipas"), blank=True, null=True)
    rating = models.IntegerField(_("Vertinimas"), blank=True, null=True)
    title = models.CharField(_("Pavadinimas"), max_length=255, blank=True)
    uri = models.CharField(_("Formato nuoroda į kontroliuojamą žodyną"), max_length=255, blank=True)
    media_type_uri = models.CharField(_("Laikmenos tipo nuoroda į kontroliuojamą žodyną"), max_length=255, blank=True)

    class Meta:
        db_table = "format"
        verbose_name = _("Formatas")
        verbose_name_plural = _("Formatai")

    def __str__(self):
        return self.title


class GeoportalFormat(models.Model):
    format = models.ForeignKey(Format, verbose_name=_("Formatas"), on_delete=models.CASCADE)

    class Meta:
        db_table = "geoportal_format"
        verbose_name = _("Geoportalo formatas")
        verbose_name_plural = _("Geoportalo formatai")

    def __str__(self):
        return str(self.format)


class GeoportalFormatValue(models.Model):
    geoportal_format = models.ForeignKey(
        GeoportalFormat, verbose_name=_("Geoportalo formatas"), on_delete=models.CASCADE
    )
    value = models.CharField(_("Reikšmė"), max_length=255)

    class Meta:
        db_table = "geoportal_format_value"
        verbose_name = _("Geoportalo formato reikšmė")
        verbose_name_plural = _("Geoportalo formato reikšmės")

    def __str__(self):
        return self.value


class DistributionFormat(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    title = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "distribution_format"


class CompressionFormat(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    extension = models.CharField(_("Failo plėtinys"), max_length=255, blank=True, null=True)
    title = models.CharField(_("Pavadinimas"), max_length=255, blank=True)
    uri = models.CharField(_("Formato nuoroda į kontroliuojamą žodyną"), max_length=255, blank=True)

    class Meta:
        db_table = "compression_format"
        verbose_name = _("Suspausto failo formatas")
        verbose_name_plural = _("Suspausto failo formatai")

    def __str__(self):
        return self.title


class PackagingFormat(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    extension = models.CharField(_("Failo plėtinys"), max_length=255, blank=True, null=True)
    title = models.CharField(_("Pavadinimas"), max_length=255, blank=True)
    uri = models.CharField(_("Formato nuoroda į kontroliuojamą žodyną"), max_length=255, blank=True)

    class Meta:
        db_table = "packaging_format"
        verbose_name = _("Suspausto failų paketo formatas")
        verbose_name_plural = _("Suspausto failų paketo formatai")

    def __str__(self):
        return self.title


class DatasetDistribution(TranslatableModel):
    DISTRIBUTION_STATUS_URI = "http://publications.europa.eu/resource/authority/distribution-status"
    UPLOAD_TO = "data"
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    data_last_updated = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    dataset = models.ForeignKey("vitrina_datasets.Dataset", models.CASCADE)
    translations = TranslatedFields(
        title=models.CharField(_("Pavadinimas"), blank=True, max_length=255),
        description=models.TextField(_("Aprašymas"), blank=True),
        conditions=models.TextField(
            _("Teisės - Aprašymas"),
            help_text=_(
                "Laisvu tekstu pateikiamas teisių deklaracijos aprašymas. Atitinka dct:rights / dct:description."
            ),
            blank=True,
            null=True,
        ),
    )

    access_url = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Prieigos nuoroda"),
        help_text=_(
            "Nuoroda į svetainę, kurioje galima rasti tiesiogines duomenų atsisiuntimo nuorodas. "
            "Atitinka dcat:accessUrl."
        ),
    )

    format = models.ForeignKey(
        Format,
        models.SET_NULL,
        blank=False,
        null=True,
        related_name="format_distributions",
        verbose_name=_("Duomenų formatas"),
        help_text=_("Pateikties failų formatas. Atitinka dct:format."),
    )
    compression_format = models.ForeignKey(
        CompressionFormat,
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Suspausto failo formatas"),
        help_text=_(
            "Ši savybė nurodo failo, kuriame yra duomenys, formatą suspaustoje formoje. Atitinka dcat:compressFormat."
        ),
    )
    packaging_format = models.ForeignKey(
        PackagingFormat,
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("(Failų) Pakavimo formatas"),
        help_text=_(
            "Ši savybė nurodo failo, kuriame yra vienas ar daugiau duomenų, formatą. Atitinka dcat:packageFormat."
        ),
    )

    download_url = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Atsisiuntimo nuoroda"),
        help_text=_(
            "Tiesioginė duomenų atsisiuntimo nuoroda. Ši nuoroda turi rodyti tiesiogiai į CSV, JSON "
            "ar kito formato duomenų failą. Atitinka dcat:downloadURL."
        ),
    )

    file = FilerFileField(
        blank=True,
        null=True,
        related_name="file_distribution",
        on_delete=models.SET_NULL,
        verbose_name=_("Duomenų failas"),
        help_text=_(
            "Atvirų duomenų katalogas nėra skirtas duomenų talpinimui ir "
            "įprastinių atveju duomenys turėtu būti talpinami atvirų duomenų "
            "Saugykloje ar kitoje vietoje, pateikiant tiesioginę duomenų "
            "atsisiuntimo nuorodą. Tačiau nedidelės apimties (iki 5Mb) "
            "duomenų failus, galima talpinti ir kataloge."
        ),
    )

    geo_location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Geografinė aprėptis"),
    )

    distribution_version = models.IntegerField(blank=True, null=True)

    issued = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    data_service = models.ForeignKey(
        "vitrina_datasets.Dataset",
        on_delete=models.SET_NULL,
        null=True,
        related_name="data_service_distributions",
        verbose_name=_("Duomenų paslauga"),
        help_text=_("Duomenų paslauga, per kurią prieinama duomenų pateiktis. Atitinka dcat:accessService."),
    )
    is_parameterized = models.BooleanField(default=False, verbose_name=_("Parametrizuotas"))
    upload_to_storage = models.BooleanField(default=False, verbose_name=_("Įkėlimas į saugyklą"))
    imported = models.BooleanField(default=False, verbose_name=_("Importuojamas išorinis metaduomenų katalogas"))
    licence = models.ForeignKey(
        Licence,
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Licencija"),
        help_text=_("Licencija, pagal kurią platinamas pateikimas. Atitinka dct:license."),
    )
    applicable_legislation = models.ManyToManyField(
        ApplicableLegislation,
        verbose_name=_("Teisinis pagrindas"),
        related_name="dataset_distributions",
        blank=True,
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

    status = models.ForeignKey(
        Concept,
        on_delete=models.PROTECT,
        related_name="dataset_distributions",
        verbose_name=_("Statusas"),
        help_text=_("Nurodomas pateikties brandos lygmuo. Atitinka adms:status."),
        default=get_default_status,
    )

    rights_relation = models.URLField(
        verbose_name=_("Teisės - Susijęs dokumentas"),
        max_length=1024,
        null=True,
        blank=True,
        help_text=_("Teisių deklaracijos nuoroda. Atitinka dct:rights / dct:relation."),
    )
    is_hvd = models.BooleanField(_("Ar pateiktis yra didelės vertės"), default=False)

    # Deprecated fields bellow
    period_start = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Periodo pradžia"),
    )
    period_end = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Periodo pabaiga"),
    )
    type = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)

    metadata = GenericRelation("vitrina_structure.Metadata")
    params = GenericRelation("vitrina_structure.Param")

    objects = TranslatableManager()

    metadata_version = models.ForeignKey(
        "vitrina_structure.Version",
        models.SET_NULL,
        blank=True,
        null=True,
    )

    access = models.IntegerField(
        _("Prieiga"),
        choices=AccessType.choices,
        blank=True,
        null=True,
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Kodinis pavadinimas"),
    )
    level = models.IntegerField(_("Brandos lygis"), null=True, blank=True)

    class Meta:
        db_table = "dataset_distribution"

    def __str__(self):
        return self.safe_translation_getter("title", language_code=self.get_current_language()) or ""

    def extension(self) -> str:
        if self.file and self.file.file:
            return get_file_extension(self.file.file.name).upper()
        else:
            return ""

    def filename_without_path(self):
        return pathlib.Path(self.file.file.name).name if self.file and self.file.file else ""

    def is_external_url(self):
        return True if self.download_url else False

    def get_download_url(self):
        if self.is_external_url():
            return self.download_url
        elif self.file:
            return self.file.url
        return ""

    def get_access_url(self):
        if self.access_url:
            return self.access_url
        elif self.dataset and self.dataset.landing_page:
            return self.dataset.landing_page
        elif download_url := self.get_download_url():
            return download_url
        return ""

    def get_format(self):
        return self.format

    def is_previewable(self):
        return (
            self.file
            and self.file.file
            and self.file.file.storage.exists(self.file.file.name)
            and (self.extension() == "CSV" or self.extension() == "XLSX")
            and self.file.file.size > 0
        )

    def get_acl_parents(self):
        parents = [self]
        if self.dataset:
            parents.extend(self.dataset.get_acl_parents())
        return parents

    def get_absolute_url(self) -> str:
        if self.metadata_version and self.metadata_version.pk:
            return reverse(
                "resource-detail",
                kwargs={"pk": self.dataset.pk, "resource_id": self.pk, "version_id": self.metadata_version.pk},
            )
        return reverse(
            "resource-detail-no-version",
            kwargs={
                "pk": self.dataset.pk,
                "resource_id": self.pk,
            },
        )

    def lt_title(self):
        return self.safe_translation_getter("title", language_code="lt")

    def en_title(self):
        return self.safe_translation_getter("title", language_code="en")

    def lt_conditions(self):
        return self.safe_translation_getter("conditions", language_code="lt")

    def en_conditions(self):
        return self.safe_translation_getter("conditions", language_code="en")

    def lt_description(self):
        return self.safe_translation_getter("description", language_code="lt")

    def en_description(self):
        return self.safe_translation_getter("description", language_code="en")

    def save_translations(self, *args, **kwargs):
        super(DatasetDistribution, self).save_translations(*args, **kwargs)

        if (
            not self.has_translation(language_code="en")
            or not self.en_title()
            or not self.en_description()
            or not self.en_conditions()
        ):
            lt_title = self.lt_title()
            lt_description = self.lt_description()
            lt_conditions = self.lt_conditions()

            if not self.has_translation(language_code="en"):
                self.create_translation(language_code="en")
            self.set_current_language("en")

            if lt_title and not self.en_title():
                self.title = translate_text(lt_title, f"distribution {self.id} title")

            if lt_description and not self.en_description():
                self.description = translate_text(lt_description, f"distribution {self.id} description")

            if lt_conditions and not self.en_conditions():
                self.conditions = translate_text(lt_conditions, f"distribution {self.id} conditions")

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

    def create_or_reuse_metadata_instance_and_assign_version(self, metadata_version_id: int) -> Metadata:
        metadata_version = Version.objects.filter(pk=metadata_version_id).first()
        if not metadata_version:
            logging.error(f"Version with pk={metadata_version_id} does not exist")
            raise ValueError(f"Version with pk={metadata_version_id} does not exist")

        if metadata_instance := self.metadata.first():
            metadata_instance.metadata_version = metadata_version
            metadata_instance.save(update_fields=["metadata_version"])
        else:
            metadata_instance = Metadata.objects.create(
                uuid=str(uuid.uuid4()),
                dataset=self.dataset,
                content_type=ContentType.objects.get_for_model(DatasetDistribution),
                object_id=self.pk,
                name=self.name,
                prepare_ast={},
                access=self.access or None,
                version=1,
                title=self.title,
                description=self.description,
                level_given=self.level,
                metadata_version=metadata_version,
            )

        return metadata_instance

    def delete_resource_metadata_if_has_no_models(self):
        if not self.model_set.exists():
            self.metadata_version = None
            self.save()
            self.metadata.all().delete()

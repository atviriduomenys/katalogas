import pathlib

from django.db import models
from django.utils.translation import gettext_lazy as _
from filer.fields.file import FilerFileField

from vitrina.datasets.models import Dataset


class Format(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    extension = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    mimetype = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'format'

    def __str__(self):
        return self.title


class DistributionFormat(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    title = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'distribution_format'


class DatasetDistribution(models.Model):
    UPLOAD_TO = "data"

    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    dataset = models.ForeignKey(Dataset, models.CASCADE)
    title = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_('Pavadinimas'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Aprašymas'),
    )

    access_url = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Prieigos nuoroda'),
        help_text=_(
            'Nuoroda į svetainę iš kurios galima atsisiųsti duomenis.'
        ),
    )

    format = models.ForeignKey(
        Format,
        models.SET_NULL,
        blank=False,
        null=True,
        verbose_name=_('Duomenų formatas'),
    )

    download_url = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Atsisiuntimo nuoroda'),
        help_text=_(
            'Tiesioginė duomenų atsisiuntimo nuoroda.'
        ),
    )

    file = FilerFileField(
        blank=True,
        null=True,
        related_name="file_distribution",
        on_delete=models.SET_NULL,
        verbose_name=_('Duomenų failas'),
        help_text=_(
            'Atvirų duomenų katalogas nėra skirtas duomenų talpinimui ir '
            'įprastinių atveju duomenys turėtu būti talpinami atvirų duomenų '
            'Saugykloje ar kitoje vietoje, pateikiant tiesioginę duomenų '
            'atsisiuntimo nuorodą. Tačiau nedidelės apimties (iki 5Mb) '
            'duomenų failus, galima talpinti ir kataloge.'
        ),
    )

    geo_location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Geografinė aprėptis'),
    )
    period_start = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('Periodo pradžia'),
    )
    period_end = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('Periodo pabaiga'),
    )

    distribution_version = models.IntegerField(blank=True, null=True)

    issued = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    # Deprecated fields bellow
    type = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'dataset_distribution'

    def __str__(self):
        return self.title

    def extension(self) -> str:
        if self.file and self.file.file:
            path = pathlib.Path(self.file.file.name)
            return path.suffix.lstrip('.').upper()
        else:
            return ''

    def filename_without_path(self):
        return pathlib.Path(self.file.file.name).name if self.file and self.file.file else ""

    def is_external_url(self):
        return self.type == "URL"

    def get_download_url(self):
        if self.is_external_url():
            return self.download_url
        elif self.file:
            return self.file.url
        return ""

    def get_format(self):
        return self.format

    def is_previewable(self):
        return (self.extension() == "CSV" or self.extension() == "XLSX") and self.file.file.size > 0

    def get_acl_parents(self):
        parents = [self]
        if self.dataset:
            parents.extend(self.dataset.get_acl_parents())
        return parents

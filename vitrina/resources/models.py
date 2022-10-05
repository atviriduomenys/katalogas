import pathlib

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from vitrina.orgs.models import Region
from vitrina.orgs.models import Municipality
from vitrina.datasets.models import Dataset


class Format(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
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
    version = models.IntegerField()
    title = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'distribution_format'


class DatasetDistribution(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    dataset = models.ForeignKey(Dataset, models.CASCADE)

    identifier = models.CharField(max_length=255, blank=True, null=True)

    title = models.CharField(
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
        verbose_name=_('Šaltinio formatas'),
    )

    download_url = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Atsisniuntimo nuoroda'),
        help_text=_(
            'Tiesioginė duomenų atsisiuntimo nuoroda.'
        ),
    )

    file = models.FileField(
        upload_to='data/',
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Duomenų failas'),
        help_text=_(
            'Atvirų duomenų katalogas nėra skirtas duomenų talpinimui ir '
            'įprastinių atveju duomenys turėtu būti talpinami atvirų duomenų '
            'Saugykloje ar kitoje vietoje, pateikiant tiesioginę duomenų '
            'atsisiuntimo nuorodą. Tačiau nedidelės apimties (iki 5Mb) '
            'duomenų failus, galima talpinti ir kataloge.'
        ),
    )

    region = models.ForeignKey(
        Region,
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_('Regionas'),
    )
    municipality = models.ForeignKey(
        Municipality,
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_('Savivaldybė'),
    )

    period_start = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Periodo pradžia'),
    )
    period_end = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Periodo pabaiga'),
    )

    distribution_version = models.IntegerField(blank=True, null=True)

    type = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    issued = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'dataset_distribution'

    def __str__(self):
        return self.title

    def extension(self) -> str:
        if self.file:
            path = pathlib.Path(self.file.name)
            return path.suffix.lstrip('.').upper()
        else:
            return ''

    def filename_without_path(self):
        return pathlib.Path(self.file.name).name if self.file else ""

    def is_external_url(self):
        return self.type == "URL"

    def get_download_url(self):
        if self.is_external_url():
            return self.url
        return reverse('dataset-distribution-download', kwargs={
            'dataset_id': self.dataset.pk,
            'distribution_id': self.pk,
            'filename': self.filename_without_path()
        })

    def get_format(self):
        if self.is_external_url() and self.url_format:
            return self.url_format.extension
        else:
            if not self.file:
                return self.mime_type
            elif self.url_format:
                return self.url_format.extension
            else:
                return self.extension()

    def is_previewable(self):
        return (self.extension() == "CSV" or self.extension() == "XLSX") and self.file.file.size > 0

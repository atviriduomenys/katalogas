from datetime import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _
from filer.fields.image import FilerImageField
from parler.models import TranslatableModel, TranslatedFields


class ModelDownloadStats(models.Model):
    created = models.DateTimeField(blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    model_format = models.CharField(max_length=255, blank=True, null=True)
    model_requests = models.BigIntegerField(blank=True, null=True)
    model_objects = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'model_download_statistic'


class DatasetStats(models.Model):
    created = models.DateField(blank=True, null=True, default=datetime.today)
    dataset_id = models.IntegerField(blank=False, null=False)
    object_count = models.IntegerField(blank=True, null=True)
    field_count = models.IntegerField(blank=True, null=True)
    model_count = models.IntegerField(blank=True, null=True)
    distribution_count = models.IntegerField(blank=True, null=True)
    request_count = models.IntegerField(blank=True, null=True)
    project_count = models.IntegerField(blank=True, null=True)
    maturity_level = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'dataset_statistic'


class StatRoute(TranslatableModel):
    translations = TranslatedFields(
        title=models.CharField(_("Pavadinimas"), max_length=255),
        description=models.TextField(_("Aprašymas"), blank=True, null=True),
    )
    image = FilerImageField(verbose_name=_("Paveiksliukas"), null=True, blank=True, on_delete=models.SET_NULL)
    url = models.CharField(_("Nuoroda"), max_length=512)
    featured = models.BooleanField(_("Rodoma tituliniame puslapyje"), default=False)
    order = models.IntegerField(_("Eiliškumas"), null=True, blank=True)

    class Meta:
        db_table = 'stat_route'
        verbose_name = _("Statistikos nuoroda")
        verbose_name_plural = _("Statistikos nuorodos")

    def __str__(self):
        return self.safe_translation_getter('title', language_code=self.get_current_language())

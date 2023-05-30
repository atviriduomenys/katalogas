import builtins
import functools
import operator

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Prefix(models.Model):
    name = models.CharField(_("Pavadinimas"), max_length=255)
    uri = models.CharField(_("URI"), max_length=255)
    content_type = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        verbose_name=_("Objekto tipas"),
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(_("Objekto id"), null=True, blank=True)
    object = GenericForeignKey('content_type', 'object_id')

    metadata = GenericRelation('Metadata')
    objects = models.Manager()

    class Meta:
        db_table = 'prefix'
        verbose_name = _('Prefiksas')

    def __str__(self):
        return self.name


class Metadata(models.Model):
    uuid = models.CharField(_("Id"), max_length=255)
    name = models.CharField(_("Vardas"), max_length=255, blank=True)
    type = models.CharField(_("Tipas"), max_length=255, blank=True)
    ref = models.CharField(_("Ryšys"), max_length=255, blank=True)
    source = models.CharField(_("Šaltinis"), max_length=255, blank=True)
    prepare = models.CharField(_("Formulė"), max_length=255, blank=True)
    prepare_ast = models.JSONField(_("Formulės AST"), blank=True)
    level = models.IntegerField(_("Brandos lygis"), null=True, blank=True)
    level_given = models.IntegerField(_("Duotas brandos lygis"), null=True, blank=True)
    average_level = models.FloatField(_("Apskaičiuotas brandos lygis"), null=True, blank=True)
    access = models.CharField(_("Prieiga"), max_length=255, blank=True)
    prefix = models.ForeignKey(Prefix, models.SET_NULL, verbose_name=_("Prefiksas"), null=True, blank=True)
    uri = models.CharField(_("Žodyno atitikmuo"), max_length=255, blank=True)
    version = models.IntegerField(_("Versija"), blank=True)
    title = models.CharField(_("Pavadinimas"), max_length=255, blank=True)
    description = models.TextField(_("Aprašymas"), blank=True)
    order = models.IntegerField(_("Rikiavimo tvarka"), null=True, blank=True)
    content_type = models.ForeignKey(ContentType, models.CASCADE, verbose_name=_("Objekto tipas"))
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey('content_type', 'object_id')
    dataset = models.ForeignKey('vitrina_datasets.Dataset', models.CASCADE, verbose_name=_('Duomenų rinkinys'))
    required = models.BooleanField(_("Privalomas"), null=True, blank=True)
    unique = models.BooleanField(_("Unikalus"), null=True, blank=True)

    objects = models.Manager()

    class Meta:
        db_table = 'metadata'
        verbose_name = _('Metaduomenys')

    def __str__(self):
        return self.name

    @property
    def uri_link(self):
        link = None
        if self.uri:
            prefix, name = self.uri.split(':', 1)
            if prefix := Prefix.objects.filter(
                name=prefix,
                metadata__dataset=self.dataset
            ).first():
                link = f"{prefix.uri}{name}"
        return link


class Base(models.Model):
    model = models.ForeignKey(
        'Model',
        models.CASCADE,
        verbose_name=_('Paveldimas modelis'),
        related_name="ref_model_base"
    )

    metadata = GenericRelation('Metadata')
    objects = models.Manager()

    class Meta:
        db_table = 'base'
        verbose_name = _('Bazė')

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ""


class Model(models.Model):
    dataset = models.ForeignKey('vitrina_datasets.Dataset', models.CASCADE, verbose_name=_("Duomenų rinkinys"))
    distribution = models.ForeignKey(
        'vitrina_resources.DatasetDistribution',
        models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Duomenų šaltinis")
    )
    base = models.ForeignKey(
        'Base',
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Bazė"),
        related_name='base_models'
    )

    objects = models.Manager()
    metadata = GenericRelation('Metadata')
    property_list = GenericRelation('PropertyList')

    class Meta:
        db_table = 'model'
        verbose_name = _('Modelis')

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ""

    @property
    def name(self):
        if metadata := self.metadata.first():
            return metadata.name.split('/')[-1]
        return ''

    @property
    def title(self):
        if metadata := self.metadata.first():
            return metadata.title
        return ''

    def update_level(self):
        if metadata := self.metadata.first():
            prop_ids = self.model_properties.values_list('pk', flat=True)
            where = [
                Q(content_type=ContentType.objects.get_for_model(Model), object_id=self.pk),
                Q(content_type=ContentType.objects.get_for_model(Property), object_id__in=prop_ids)
            ]
            if self.base:
                where.append(
                    Q(content_type=ContentType.objects.get_for_model(Base), object_id=self.base.pk)
                )
            where = functools.reduce(operator.or_, where)
            levels = Metadata.objects.filter(where, level__isnull=False).values_list('level', flat=True)
            if levels:
                metadata.average_level = sum(levels) / len(levels)
                metadata.save()

    def get_absolute_url(self):
        return reverse('model-structure', kwargs={
            'pk': self.dataset.pk,
            'model': self.name,
        })

    def get_data_url(self):
        return reverse('model-data', kwargs={
            'pk': self.dataset.pk,
            'model': self.name,
        })

    def get_given_props(self):
        return self.model_properties.filter(given=True).order_by('metadata__order')

    def get_acl_parents(self):
        return [self.dataset]


class Property(models.Model):
    model = models.ForeignKey(
        Model,
        models.CASCADE,
        verbose_name=_("Modelis"),
        related_name="model_properties"
    )
    ref_model = models.ForeignKey(
        Model,
        models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Susijęs modelis"),
        related_name="ref_model_properties"
    )
    property = models.ForeignKey(
        'Property',
        models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Tėvinė savybė"),
        related_name="child_properties"
    )
    given = models.BooleanField(_('Duota savybė'), default=True)

    objects = models.Manager()
    metadata = GenericRelation('Metadata')
    property_list = GenericRelation('PropertyList')
    enums = GenericRelation('Enum')

    class Meta:
        db_table = 'property'
        verbose_name = _('Savybė')

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ""

    def get_absolute_url(self):
        return reverse('property-structure', kwargs={
            'pk': self.model.dataset.pk,
            'model': self.model.name,
            'prop': self.name,
        })

    @builtins.property
    def name(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ''

    @builtins.property
    def title(self):
        if metadata := self.metadata.first():
            return metadata.title
        return ''

    def get_acl_parents(self):
        return [self.model.dataset]


class PropertyList(models.Model):
    property = models.ForeignKey('Property', models.CASCADE, verbose_name=_("Savybė"))
    order = models.IntegerField(_("Rikiavimo tvarka"))
    content_type = models.ForeignKey(ContentType, models.CASCADE, verbose_name=_("Objekto tipas"),)
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey('content_type', 'object_id')

    objects = models.Manager()

    class Meta:
        db_table = 'property_list'
        verbose_name = _('Savybių sąrašas')

    def __str__(self):
        return str(self.property)


class Enum(models.Model):
    name = models.CharField(_("Pavadinimas"), max_length=255)
    content_type = models.ForeignKey(ContentType, models.CASCADE, verbose_name=_("Objekto tipas"), )
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey('content_type', 'object_id')

    metadata = GenericRelation('Metadata')
    objects = models.Manager()

    class Meta:
        db_table = 'enum'
        verbose_name = _('Pasirinkimų sąrašas')

    def __str__(self):
        return self.name


class EnumItem(models.Model):
    enum = models.ForeignKey(Enum, models.CASCADE, verbose_name=_("Pasirinkimų sąrašas"))

    metadata = GenericRelation('Metadata')
    objects = models.Manager()

    class Meta:
        db_table = 'enum_item'
        verbose_name = _('Pasirinkimas')

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.prepare
        return ""


class Param(models.Model):
    name = models.CharField(_("Pavadinimas"), max_length=255)
    content_type = models.ForeignKey(ContentType, models.CASCADE, verbose_name=_("Objekto tipas"), )
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey('content_type', 'object_id')

    metadata = GenericRelation('Metadata')
    objects = models.Manager()

    class Meta:
        db_table = 'param'
        verbose_name = _('Parametras')

    def __str__(self):
        return self.name


class ParamItem(models.Model):
    param = models.ForeignKey(Param, models.CASCADE, verbose_name=_("Parametras"))

    metadata = GenericRelation('Metadata')
    objects = models.Manager()

    class Meta:
        db_table = 'param_item'
        verbose_name = _('Parametro dalis')

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ""

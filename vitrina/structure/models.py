from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
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
    access = models.CharField(_("Prieiga"), max_length=255, blank=True)
    prefix = models.ForeignKey(Prefix, models.SET_NULL, verbose_name=_("Prefiksas"), null=True, blank=True)
    uri = models.CharField(_("Žodyno atitikmuo"), max_length=255, blank=True)
    version = models.IntegerField(_("Versija"), blank=True)
    title = models.CharField(_("Pavadinimas"), max_length=255, blank=True)
    description = models.CharField(_("Aprašymas"), max_length=255, blank=True)
    order = models.IntegerField(_("Rikiavimo tvarka"), null=True, blank=True)
    content_type = models.ForeignKey(ContentType, models.CASCADE, verbose_name=_("Objekto tipas"))
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey('content_type', 'object_id')
    dataset = models.ForeignKey('vitrina_datasets.Dataset', models.CASCADE, verbose_name=_('Duomenų rinkinys'))

    objects = models.Manager()

    class Meta:
        db_table = 'metadata'
        verbose_name = _('Metaduomenys')

    def __str__(self):
        return self.name


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
        if self.metadata.first():
            return self.metadata.first().name
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
        if self.metadata.first():
            return self.metadata.first().name
        return ""


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

    class Meta:
        db_table = 'property'
        verbose_name = _('Savybė')

    def __str__(self):
        if self.metadata.first():
            return self.metadata.first().name
        return ""


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
        if self.metadata.first():
            return self.metadata.first().prepare
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
        if self.metadata.first():
            return self.metadata.first().name
        return ""

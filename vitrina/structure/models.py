import builtins
import functools
import operator

import reversion
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, Max, Avg
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from vitrina.structure.helpers import get_type_repr


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
        verbose_name_plural = _('Prefiksai')

    def __str__(self):
        return self.name


class MetadataManager(models.Manager):
    def average_level(self):
        return self.exclude(average_level__isnull=True).aggregate(Avg('average_level'))['average_level__avg']


class Metadata(models.Model):
    UNDEFINED = None
    PRIVATE = 0
    PROTECTED = 1
    PUBLIC = 2
    OPEN = 3
    ACCESS_TYPES = (
        (UNDEFINED, _("nepasirinkta")),
        (PRIVATE, _("private")),
        (PROTECTED, _("protected")),
        (PUBLIC, _("public")),
        (OPEN, _("open")),
    )

    uuid = models.CharField(_("Id"), max_length=255)
    name = models.CharField(_("Vardas"), max_length=255, blank=True)
    type = models.CharField(_("Tipas"), max_length=255, blank=True)
    ref = models.CharField(_("Ryšys"), max_length=255, blank=True, null=True)
    source = models.CharField(_("Šaltinis"), max_length=255, blank=True, null=True)
    prepare = models.CharField(_("Formulė"), max_length=255, blank=True, null=True)
    prepare_ast = models.JSONField(_("Formulės AST"), blank=True, null=True)
    level = models.IntegerField(_("Brandos lygis"), null=True, blank=True)
    level_given = models.IntegerField(_("Duotas brandos lygis"), null=True, blank=True)
    average_level = models.FloatField(_("Apskaičiuotas brandos lygis"), null=True, blank=True)
    access = models.IntegerField(_("Prieiga"), choices=ACCESS_TYPES, blank=True, null=True)
    prefix = models.ForeignKey(Prefix, models.SET_NULL, verbose_name=_("Prefiksas"), null=True, blank=True)
    uri = models.CharField(_("Žodyno atitikmuo"), max_length=255, blank=True)
    version = models.IntegerField(_("Versija"), blank=True)
    title = models.TextField(_("Pavadinimas"), blank=True, null=True)
    description = models.TextField(_("Aprašymas"), blank=True, null=True)
    order = models.IntegerField(_("Rikiavimo tvarka"), null=True, blank=True)
    content_type = models.ForeignKey(ContentType, models.CASCADE, verbose_name=_("Objekto tipas"))
    object_id = models.PositiveIntegerField(_("Objekto id"))
    object = GenericForeignKey('content_type', 'object_id')
    dataset = models.ForeignKey('vitrina_datasets.Dataset', models.CASCADE, verbose_name=_('Duomenų rinkinys'))
    required = models.BooleanField(_("Privalomas"), null=True, blank=True)
    unique = models.BooleanField(_("Unikalus"), null=True, blank=True)
    type_args = models.CharField(_("Tipo argumentai"), max_length=255, null=True, blank=True)
    metadata_version = models.ForeignKey('Version', verbose_name=_("Versija"), on_delete=models.CASCADE, null=True)
    draft = models.BooleanField(_("Priskirta versijai"), default=True,)

    objects = MetadataManager()

    class Meta:
        db_table = 'metadata'
        verbose_name = _('Metaduomenys')

    def __str__(self):
        return self.name

    @property
    def uri_link(self):
        link = None
        if self.uri:
            if '://' in self.uri:
                link = self.uri
            elif ':' in self.uri:
                prefix, name = self.uri.split(':', 1)
                if prefix := Prefix.objects.filter(
                    Q(name=prefix, metadata__dataset=self.dataset) |
                    Q(name=prefix, object_id=None, content_type=None)
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
        'Model',
        models.CASCADE,
        verbose_name=_('Paveldimas modelis'),
        related_name="ref_model_base"
    )

    metadata = GenericRelation('Metadata')
    property_list = GenericRelation('PropertyList')
    objects = models.Manager()

    class Meta:
        db_table = 'base'
        verbose_name = _('Bazė')

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ""


@reversion.register()
class Model(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    dataset = models.ForeignKey('vitrina_datasets.Dataset',
                                models.CASCADE,
                                verbose_name=_("Duomenų rinkinys"))
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
    is_parameterized = models.BooleanField(default=False, verbose_name=_("Parametrizuotas"))

    objects = models.Manager()
    metadata = GenericRelation('Metadata')
    property_list = GenericRelation('PropertyList')
    params = GenericRelation('Param')
    requests = GenericRelation('vitrina_requests.RequestObject')

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
    def full_name(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ''

    @property
    def title(self):
        if metadata := self.metadata.first():
            return metadata.title
        return ''

    @property
    def description(self):
        if metadata := self.metadata.first():
            return metadata.description
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
        if self.name:
            return reverse('model-structure', kwargs={
                'pk': self.dataset.pk,
                'model': self.name,
            })
        return None

    def get_data_url(self):
        if self.name:
            return reverse('model-data', kwargs={
                'pk': self.dataset.pk,
                'model': self.name,
            })
        return None

    def get_api_url(self):
        if self.name:
            return reverse('getall-api', kwargs={
                'pk': self.dataset.pk,
                'model': self.name
            })
        return None

    def get_given_props(self):
        return self.model_properties.filter(given=True).order_by('metadata__order')

    def get_props_excluding_base(self):
        base_props = []
        for props in self.get_base_props().values():
            base_props.extend(props.values_list('metadata__name', flat=True))

        return self.get_given_props().exclude(metadata__name__in=base_props)

    def get_acl_parents(self):
        return [self.dataset]

    def get_base_props(self):
        base = self.base
        base_props = {}
        while base:
            base_props[base.model] = base.model.get_given_props()
            base = base.model.base
        return base_props

    @property
    def access_display_value(self):
        access = Model.objects.annotate(
            access=Max('model_properties__metadata__access')
        ).get(pk=self.pk).access
        if access is not None:
            for type in Metadata.ACCESS_TYPES:
                if type[0] == access:
                    return type[1]
        return ''

    def is_opened(self):
        return self.dataset.is_opened()


@reversion.register()
class Property(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
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
    requests = GenericRelation('vitrina_requests.RequestObject')

    class Meta:
        db_table = 'property'
        verbose_name = _('Savybė')

    def __str__(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ""

    def get_absolute_url(self):
        if self.model.name and self.name:
            return reverse('property-structure', kwargs={
                'pk': self.model.dataset.pk,
                'model': self.model.name,
                'prop': self.name,
            })
        return None

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

    @builtins.property
    def description(self):
        if metadata := self.metadata.first():
            return metadata.description
        return ''

    def get_acl_parents(self):
        return [self.model.dataset]

    def is_opened(self):
        return self.model.dataset.is_opened()


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


class Version(models.Model):
    dataset = models.ForeignKey(
        'vitrina_datasets.Dataset',
        verbose_name=_("Duomenų rinkinys"),
        on_delete=models.CASCADE,
        related_name='dataset_version'
    )
    version = models.IntegerField(_("Versija"), null=True, blank=True)
    created = models.DateTimeField(_("Sukūrimo data"), auto_now_add=True)
    released = models.DateField(_("Išleidimo data"), null=True, blank=True)
    description = models.TextField(_("Aprašymas"), null=True, blank=True)
    deployed = models.DateTimeField(_("Įkėlimo į saugyklą data"), null=True, blank=True)

    class Meta:
        db_table = 'version'
        verbose_name = _('Versija')
        unique_together = (('dataset', 'version'),)

    def get_absolute_url(self):
        return reverse('version-detail', kwargs={
            'pk': self.dataset.pk,
            'version_id': self.pk
        })

    def __str__(self):
        return f"v{self.version}"


class MetadataVersion(models.Model):
    UNDEFINED = None
    PRIVATE = 0
    PROTECTED = 1
    PUBLIC = 2
    OPEN = 3
    ACCESS_TYPES = (
        (UNDEFINED, _("nepasirinkta")),
        (PRIVATE, _("private")),
        (PROTECTED, _("protected")),
        (PUBLIC, _("public")),
        (OPEN, _("open")),
    )

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
    access = models.IntegerField(_("Prieiga"), choices=ACCESS_TYPES, blank=True, null=True)
    base = models.ForeignKey(
        'Base',
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Bazė"),
    )

    class Meta:
        db_table = 'metadata_version'
        verbose_name = _('Metaduomenų versija')
        unique_together = (('metadata', 'version'),)

    @property
    def type_repr(self):
        if self.type:
            return get_type_repr(self)
        return ""

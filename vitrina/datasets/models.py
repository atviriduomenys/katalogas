import pathlib
import tagulous
import requests
import reversion
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType

from django.db import models
from django.db.models import Sum
from django.dispatch import receiver
from django.urls import reverse
from django.utils.safestring import mark_safe

from django.apps import apps

from filer.fields.file import FilerFileField
from parler.signals import post_translation_save
from tagulous.models import TagField
from parler.managers import TranslatableManager
from parler.models import TranslatedFields, TranslatableModel
from random import randrange

from vitrina.structure.models import Model, Base, Property, Metadata
from vitrina.users.models import User
from vitrina.orgs.models import Organization, Representative
from vitrina.catalogs.models import Catalog, HarvestingJob
from vitrina.classifiers.models import Category, Licence, Frequency
from vitrina.datasets.managers import PublicDatasetManager

from vitrina.settings import TRANSLATION_CLIENT_ID

from django.utils.translation import gettext_lazy as _


class DatasetGroup(TranslatableModel):
    translations = TranslatedFields(
        title=models.CharField(_("Title"), unique=True, max_length=255, blank=False),
    )
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.safe_translation_getter('title', language_code=self.get_current_language())


class DatasetFile(models.Model):
    file = FilerFileField(verbose_name=_("Failas"), on_delete=models.CASCADE)
    dataset = models.ForeignKey(
        'Dataset',
        verbose_name=_("Duomenų rinkinys"),
        on_delete=models.CASCADE,
        related_name='dataset_files'
    )

    class Meta:
        db_table = 'dataset_file'

    def filename_without_path(self):
        return pathlib.Path(self.file.file.name).name if self.file and self.file.file else ""


class Dataset(TranslatableModel):
    UPLOAD_TO = "data/files"

    HAS_DATA = "HAS_DATA"
    INVENTORED = "INVENTORED"
    PLANNED = "PLANNED"
    UNASSIGNED = "UNASSIGNED"
    STATUSES = (
        (HAS_DATA, _("Atvertas")),
        (INVENTORED, _("Inventorintas")),
        (PLANNED, _("Planuojamas atverti")),
        (UNASSIGNED, _("Nepriskirta"))
    )
    FILTER_STATUSES = {
        HAS_DATA: _("Atverti duomenys"),
        INVENTORED: _("Tik inventorinti"),
        PLANNED: _("Planuojama atverti"),
        UNASSIGNED: _("Nepriskirta")
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
    HISTORY_MESSAGES = {
        CREATED: _("Sukurta"),
        EDITED: _("Redaguota"),
        STATUS_CHANGED: _("Pakeistas statusas"),
        TRANSFERRED: _("Perkelta"),
        DATA_ADDED: _("Pridėti duomenys"),
        DATA_UPDATED: _("Redaguoti duomenys"),
        DELETED: _("Ištrinta"),
        PROJECT_SET: _("Priskirta projektui"),
        REQUEST_SET: _("Priskirta poreikiui")
    }

    API_ORIGIN = "api"

    translations = TranslatedFields(
        title=models.TextField(_("Title"), blank=True),
        description=models.TextField(_("Description"), blank=True),
    )

    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    soft_deleted = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField(default=1)
    slug = models.CharField(unique=True, max_length=255, blank=False, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    internal_id = models.CharField(max_length=255, blank=True, null=True)

    theme = models.CharField(max_length=255, blank=True, null=True)
    category = models.ManyToManyField(Category, verbose_name=_('Kategorija'))
    category_old = models.CharField(max_length=255, blank=True, null=True)

    catalog = models.ForeignKey(Catalog, models.DO_NOTHING, db_column='catalog', blank=True, null=True)
    origin = models.CharField(max_length=255, blank=True, null=True)

    organization = models.ForeignKey(Organization, models.DO_NOTHING, blank=True, null=True)

    licence = models.ForeignKey(Licence, models.DO_NOTHING, db_column='licence', blank=False, null=True,
                                verbose_name=_('Licenzija'))

    status = models.CharField(max_length=255, choices=STATUSES, default=UNASSIGNED)
    published = models.DateTimeField(blank=True, null=True)
    is_public = models.BooleanField(default=True, verbose_name=_('Duomenų rinkinys viešinamas'))

    language = models.CharField(max_length=255, blank=True, null=True)
    spatial_coverage = models.CharField(max_length=255, blank=True, null=True)
    temporal_coverage = models.CharField(max_length=255, blank=True, null=True)

    update_frequency = models.CharField(max_length=255, blank=True, null=True)
    frequency = models.ForeignKey(Frequency, models.SET_NULL, blank=False, null=True, verbose_name=_('Atnaujinimo dažnumas'))
    last_update = models.DateTimeField(blank=True, null=True)

    access_rights = models.TextField(blank=True, null=True, verbose_name=_('Prieigos teisės'))
    distribution_conditions = models.TextField(blank=True, null=True, verbose_name=_('Platinimo salygos'))

    tags = TagField(
        blank=True,
        force_lowercase=True,
        space_delimiter=False,
        autocomplete_view='autocomplete_tags',
        autocomplete_limit=20,
        verbose_name="Žymės",
        help_text=_("Pateikite kableliu atskirtą sąrašą žymių."),
        autocomplete_settings={"width": "100%"},
        autocomplete_view_fulltext=True
    )

    notes = models.TextField(blank=True, null=True)

    # DCAT 3 fields
    part_of = models.ManyToManyField(
        'DatasetRelation',
        related_name="related_datasets",
        verbose_name=_("Duomenų rinkinio ryšiai")
    )
    type = models.ManyToManyField('Type', verbose_name=_("Tipas"))
    endpoint_url = models.URLField(_("API adresas"), null=True, blank=True)
    endpoint_type = models.ForeignKey(
        'DataServiceType',
        on_delete=models.SET_NULL,
        verbose_name=_("API formatas"),
        null=True,
        blank=True
    )
    endpoint_description = models.URLField(_("API specifikacija"), null=True, blank=True)
    endpoint_description_type = models.ForeignKey(
        'DataServiceSpecType',
        on_delete=models.SET_NULL,
        verbose_name=_("API specifikacijos formatas"),
        null=True,
        blank=True
    )
    service = models.BooleanField(_("DataService rinkinys"), default=False)
    series = models.BooleanField(_("DataSeries rinkinys"), default=False)

    # TODO: To be removed:
    # ---------------------------8<-------------------------------------
    meta = models.TextField(blank=True, null=True)

    # TODO: https://github.com/atviriduomenys/katalogas/issues/9
    priority_score = models.IntegerField(blank=True, null=True)

    # TODO: https://github.com/atviriduomenys/katalogas/issues/14
    structure_data = models.TextField(blank=True, null=True)
    structure_filename = models.CharField(max_length=255, blank=True, null=True)
    current_structure = models.ForeignKey('DatasetStructure', models.DO_NOTHING, related_name='+', blank=True,
                                          null=True)

    # TODO: https://github.com/atviriduomenys/katalogas/issues/26
    financed = models.BooleanField(blank=True, null=True)
    financing_plan_id = models.BigIntegerField(blank=True, null=True)
    financing_priorities = models.TextField(blank=True, null=True)
    financing_received = models.BigIntegerField(blank=True, null=True)
    financing_required = models.BigIntegerField(blank=True, null=True)
    will_be_financed = models.BooleanField(blank=True, default=False)
    # --------------------------->8-------------------------------------

    metadata = GenericRelation('vitrina_structure.Metadata')
    comments = GenericRelation('vitrina_comments.Comment')
    representatives = GenericRelation('vitrina_orgs.Representative')
    request_objects = GenericRelation('vitrina_requests.RequestObject')

    objects = TranslatableManager()
    public = PublicDatasetManager()

    class Meta:
        db_table = 'dataset'
        verbose_name = _('Dataset')
        unique_together = (('internal_id', 'organization_id'),)

    def __str__(self):
        return self.safe_translation_getter('title', language_code=self.get_current_language())

    def lt_title(self):
        return self.safe_translation_getter('title', language_code='lt')

    def en_title(self):
        return self.safe_translation_getter('title', language_code='en')

    def lt_description(self):
        return self.safe_translation_getter('description', language_code='lt')

    def en_description(self):
        return self.safe_translation_getter('description', language_code='en')

    def get_absolute_url(self):
        return reverse('dataset-detail', kwargs={'pk': self.pk})

    def get_tag_object_list(self):
        return list(self.tags.all().values('name', 'pk'))

    def get_tag_list(self):
        return list(self.tags.all().values_list('pk', flat=True))

    def get_tag_title(self, tag_id):
        if tag := self.tags.tag_model.objects.filter(pk=tag_id).first():
            return tag.name
        return ''

    def get_resource_titles(self):
        return list(self.datasetdistribution_set.all().values_list('title', flat=True))

    def get_model_title_list(self):
        return list(model.title for model in self.model_set.all())

    def get_property_title_list(self):
        return list(item.title for item in Property.objects.filter(model__in=self.model_set.all()))

    def get_request_title_list(self):
        return list(self.dataset_request.all().values_list('title', flat=True))

    def get_project_title_list(self):
        return list(self.project_set.all().values_list('title', flat=True))

    def get_resource_description(self):
        return list(self.datasetdistribution_set.all().values_list('description', flat=True))

    def get_model_title_description(self):
        return list(model.description for model in self.model_set.all())

    def get_property_title_description(self):
        return list(item.description for item in Property.objects.filter(model__in=self.model_set.all()))

    def get_request_title_description(self):
        return list(self.dataset_request.all().values_list('description', flat=True))

    def get_project_title_description(self):
        return list(self.project_set.all().values_list('description', flat=True))

    def get_all_groups(self):
        ids = self.category.filter(groups__isnull=False).values_list('groups__pk', flat=True).distinct()
        return DatasetGroup.objects.filter(pk__in=ids)

    def get_group_list(self):
        return list(self.category.filter(groups__isnull=False).values_list('groups__pk', flat=True).distinct())

    def get_parent_organization_title(self):
        if self.organization.is_root():
            return self.organization.title
        else:
            return self.organization.get_root().title

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
            categories = [{'title': cat.title, 'pk': cat.pk} for cat in category.get_ancestors()
                          if cat.dataset_set.exists()]
            categories.append({'title': category.title, 'pk': category.pk})
        return categories

    def get_category_object_list_en(self):
        categories = []
        for category in self.category.all():
            categories = [{'title_en': cat.title_en, 'pk': cat.pk} for cat in category.get_ancestors()
                          if cat.dataset_set.exists()]
            categories.append({'title_en': category.title_en, 'pk': category.pk})
        return categories

    def level(self):
        return randrange(5)

    @property
    def formats(self):
        return [
            obj.get_format()
            for obj in self.datasetdistribution_set.all()
            if obj.get_format()
        ]

    def filter_formats(self):
        return [
            obj.get_format().pk
            for obj in self.datasetdistribution_set.all()
            if obj.get_format()
        ]

    @property
    def distinct_formats(self):
        return sorted(set(self.formats), key=lambda x: x.title)

    def get_acl_parents(self):
        parents = [self]
        if self.organization:
            parents.extend(self.organization.get_acl_parents())
        return parents

    def get_members_url(self):
        return reverse('dataset-members', kwargs={'pk': self.pk})

    def get_managers(self):
        ct = ContentType.objects.get_for_model(Dataset)
        return list(Representative.objects.filter(
            content_type=ct, object_id=self.id
        ).values_list('user_id', flat=True))

    @property
    def language_array(self):
        if self.language:
            return [lang.replace(',', '') for lang in self.language.split(' ')]
        return []

    @property
    def tag_name_array(self):
        return [tag.name.strip() for tag in self.tags.tags]

    @property
    def category_titles(self):
        return self.category.values_list('title', flat=True)

    def jurisdiction(self) -> int | None:
        if self.organization:
            root_org = self.organization.get_root()
            if root_org.get_children_count() > 1:
                return root_org.pk
        return None

    def update_level(self):
        if metadata := self.metadata.first():
            levels = Metadata.objects.filter(
                dataset=self,
                content_type__in=[
                    ContentType.objects.get_for_model(Model),
                    ContentType.objects.get_for_model(Base),
                    ContentType.objects.get_for_model(Property)
                ],
                level__isnull=False,
            ).values_list('level', flat=True)

            if levels:
                metadata.average_level = sum(levels) / len(levels)
                metadata.save()

    def get_level(self):
        if metadata := self.metadata.first():
            return metadata.average_level
        return None

    def published_created_sort(self):
        return self.published or self.created

    def get_icon(self):
        root_category_ids = []
        for cat in self.category.all():
            root_category_ids.append(cat.get_root().pk)

        if root_category_ids:
            category = Category.objects.filter(
                pk__in=root_category_ids,
                icon__isnull=False,
            ).order_by('title').first()
            if category:
                return category.icon
        return None

    @property
    def name(self):
        if metadata := self.metadata.first():
            return metadata.name
        return ""

    def public_types(self):
        return list(self.type.filter(show_filter=True).values_list('pk', flat=True))

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
        return (
            Like.objects.
            filter(
                content_type=content_type,
                object_id=self.pk,
            ).
            count()
        )

    def get_download_count(self):
        from vitrina.statistics.models import ModelDownloadStats
        model_names = Metadata.objects.filter(
            content_type=ContentType.objects.get_for_model(Model),
            dataset__pk=self.pk
        ).values_list('name', flat=True)
        return (
            ModelDownloadStats.objects.
            filter(
                model__in=model_names
            ).
            aggregate(
                Sum('model_requests')
            )
        )["model_requests__sum"] or 0

    def get_metadata_objects_for_version(self):
        meta_objects = []
        models = []
        props = []

        metadata = self.metadata.first()
        if metadata and metadata.draft is True:
            if latest_version := metadata.metadataversion_set.order_by('-version__created').first():
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

        for model in self.model_set.all():
            metadata = model.metadata.first()
            if metadata and metadata.draft is True:
                models.append(model)
                if latest_version := metadata.metadataversion_set.order_by('-version__created').first():
                    label_str = f"<a href='{model.get_absolute_url()}' class='model_metadata'>{model.name}</a>"
                    if latest_version.name != metadata.name:
                        label_str += (
                            f" name: <span class='tag is-danger is-light is-medium'>{latest_version.name}</span> ->"
                            f" <span class='tag is-success is-light is-medium'>{metadata.name}</span>"
                        )
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
                        label_str += (f" level: "
                                      f"<span class='tag is-success is-light is-medium'>{metadata.level_given}</span>")
                    if model.base:
                        label_str += (f" base: "
                                      f"<span class='tag is-success is-light is-medium'>{model.base.model.name}</span>")
                    label = mark_safe(label_str)
                    meta_objects.append((metadata.pk, label))

            for prop in model.model_properties.filter(given=True):
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

                    if latest_version := metadata.metadataversion_set.order_by('-version__created').first():
                        label_str = f"<a href='{prop.get_absolute_url()}' class='prop_metadata'>{prop.name}</a>"
                        if latest_version.name != metadata.name:
                            label_str += (
                                f" name: <span class='tag is-danger is-light is-medium'>"
                                f"{latest_version.name}</span> ->"
                                f" <span class='tag is-success is-light is-medium'>{metadata.name}</span>"
                            )
                        if latest_version.type_repr != metadata.type_repr:
                            label_str += (
                                f" type: <span class='tag is-danger is-light is-medium'>"
                                f"{latest_version.type_repr}</span> -> "
                                f"<span class='tag is-success is-light is-medium'>{metadata.type_repr}</span>"
                            )
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
                                f" type: <span class='tag is-success is-light is-medium'>"
                                f"{metadata.type_repr}</span>"
                            )
                        if metadata.ref:
                            label_str += (
                                f" ref: <span class='tag is-success is-light is-medium'>{metadata.ref}</span>"
                            )
                        if metadata.level_given:
                            label_str += (
                                f" level: "
                                f"<span class='tag is-success is-light is-medium'>{metadata.level_given}</span>"
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

                            if latest_version := metadata.metadataversion_set.order_by('-version__created').first():
                                label_str = f"<a href='{prop.get_absolute_url()}' class='enum_metadata'>{enum_item}</a>"
                                if latest_version.prepare != metadata.prepare:
                                    label_str += (
                                        f" prepare: <span class='tag is-danger is-light is-medium'>"
                                        f"{latest_version.prepare}</span> ->"
                                        f" <span class='tag is-success is-light is-medium'>{metadata.prepare}</span>"
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
                                label_str = (
                                    f"<a href='{prop.get_absolute_url()}' class='enum_metadata'>{enum_item}</a>"
                                )
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

    def save_translation(self, translation, *args, **kwargs):
        if translation.language_code == 'lt':
            if not self.has_translation(language_code='en'):
                lt_title = self.lt_title()
                lt_description = self.lt_description()

                self.create_translation(language_code='en')
                self.set_current_language('en')

                response_title = requests.post(
                    "https://vertimas.vu.lt/ws/service.svc/json/Translate",
                    json={
                        "appId": "",
                        "systemID": "smt-8abc06a7-09dc-405c-bd29-580edc74eb05",
                        "text": lt_title,
                        "options": ""
                    },
                    headers={
                        "client-id": TRANSLATION_CLIENT_ID,
                        "Content-Type": "application/json; charset=utf-8"
                    },
                )
                en_title = response_title.json()
                self.title = en_title

                response_desc = requests.post(
                    "https://vertimas.vu.lt/ws/service.svc/json/Translate",
                    json={
                        "appId": "",
                        "systemID": "smt-8abc06a7-09dc-405c-bd29-580edc74eb05",
                        "text": lt_description,
                        "options": ""
                    },
                    headers={
                        "client-id": TRANSLATION_CLIENT_ID,
                        "Content-Type": "application/json; charset=utf-8"
                    },
                )
                en_description = response_desc.json()
                self.description = en_description

        super(Dataset, self).save_translation(translation, *args, **kwargs)


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
        managed = False
        db_table = 'geoportal_lt_entry'


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
        managed = False
        db_table = 'open_data_gov_lt_entry'


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
    job = models.ForeignKey(HarvestingJob, models.DO_NOTHING, blank=True, null=True)
    description_en = models.TextField(blank=True, null=True)
    keywords = models.TextField(blank=True, null=True)
    organization = models.TextField(blank=True, null=True)
    raw_data = models.TextField(blank=True, null=True)
    title_en = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'harvesting_result'


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
        managed = False
        db_table = 'dataset_migrate'


class DatasetRemark(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    author = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset_remark'


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
        managed = False
        db_table = 'dataset_resource'


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
    user_0 = models.ForeignKey(User, models.DO_NOTHING, db_column='user_id', blank=True,
                               null=True)  # Field renamed because of name conflict.

    class Meta:
        managed = False
        db_table = 'dataset_event'


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
        managed = False
        db_table = 'dataset_resource_migrate'


class DatasetStructureLink(models.Model):
    name = models.CharField(max_length=255, blank=True)
    dataset_id = models.IntegerField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'dataset_structure_link'


# TODO: https://github.com/atviriduomenys/katalogas/issues/14
@reversion.register()
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
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    file = FilerFileField(
        blank=True,
        null=True,
        related_name="file_structure",
        on_delete=models.SET_NULL
    )

    # Deprecatd feilds
    standardized = models.BooleanField(blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    distribution_version = models.IntegerField(blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)

    class Meta:
        db_table = 'dataset_structure'

    def __str__(self):
        if self.dataset.metadata.first():
            if self.dataset.metadata.first().title:
                return self.dataset.metadata.first().title
            else:
                return self.dataset.metadata.first().name
        else:
            return str(_("Struktūra"))

    def get_absolute_url(self):
        return reverse('dataset-structure', kwargs={'pk': self.dataset.pk})

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
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset_structure_field'


# TODO: https://github.com/atviriduomenys/katalogas/issues/60
class DatasetVisit(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    last_visited = models.DateTimeField(blank=True, null=True)
    visit_count = models.IntegerField()
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset_visit'


# TODO: https://github.com/atviriduomenys/katalogas/issues/60
class HarvestedVisit(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    last_visited = models.DateTimeField(blank=True, null=True)
    visit_count = models.IntegerField()
    harvesting_result = models.ForeignKey(HarvestingResult, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'harvested_visit'


# --------------------------->8-------------------------------------


class Attribution(models.Model):
    CREATOR = 'creator'
    CONTRIBUTOR = 'contributor'
    PUBLISHER = 'publisher'

    name = models.CharField(_("Kodinis pavadinimas"), max_length=255)
    uri = models.CharField(_("Ryšio identifikatorius"), max_length=255, blank=True)
    title = models.CharField(_("Pavadinimas"), max_length=255, blank=True)

    class Meta:
        db_table = 'attribution'

    def __str__(self):
        return self.title if self.title else self.name


class DatasetAttribution(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.PROTECT, verbose_name=_("Duomenų rinkinys"))
    attribution = models.ForeignKey(Attribution, on_delete=models.PROTECT, verbose_name=_("Priskyrimo rūšis"))
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Organizacija")
    )
    agent = models.CharField(_("Agentas"), max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'dataset_attribution'

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
        db_table = 'type'
        verbose_name = _("Tipas")
        verbose_name_plural = _("Tipai")

    def __str__(self):
        return self.safe_translation_getter('title', language_code=self.get_current_language())


class Relation(TranslatableModel):
    PART_OF = 'part-of'
    SERIES = "series"
    SERVICE = "service"

    name = models.CharField(_("Kodinis pavadinimas"), max_length=255)
    uri = models.CharField(_("Nuoroda į kontroliuojamą žodyną"), max_length=255, blank=True)
    translations = TranslatedFields(
        title=models.CharField(_("Pavadinimas"), max_length=255),
        inversive_title=models.CharField(_("Atvirkštinio ryšio pavadinimas"), max_length=255)
    )

    class Meta:
        db_table = 'relation'
        verbose_name = _("Ryšys")
        verbose_name_plural = _("Ryšiai")

    def __str__(self):
        return self.safe_translation_getter('title', language_code=self.get_current_language())


class DatasetRelation(models.Model):
    relation = models.ForeignKey(Relation, verbose_name=_("Ryšio tipas"), on_delete=models.PROTECT)
    dataset = models.ForeignKey(
        Dataset,
        verbose_name=_("Duomenų rinkinys"),
        on_delete=models.PROTECT,
        related_name="dataset_relations"
    )
    part_of = models.ForeignKey(
        Dataset,
        verbose_name=_("Priklauso rinkiniui"),
        on_delete=models.PROTECT,
        related_name="related_datasets"
    )

    class Meta:
        db_table = 'dataset_relation'
        verbose_name = _("Duomenų rinkinių ryšys")
        verbose_name_plural = _("Duomenų rinkinių ryšiai")


class DataServiceType(models.Model):
    title = models.CharField(_("Pavadinimas"), max_length=255)

    class Meta:
        db_table = 'data_service_type'

    def __str__(self):
        return self.title


class DataServiceSpecType(models.Model):
    title = models.CharField(_("Pavadinimas"), max_length=255)

    class Meta:
        db_table = 'data_service_spec_type'

    def __str__(self):
        return self.title


class DatasetStructureMapping(models.Model):
    dataset_id = models.IntegerField(blank=False, null=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    org = models.CharField(max_length=255, blank=True, null=True)
    checksum = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'dataset_structure_mapping'

import datetime
import tagulous

from django.db import models
from django.urls import reverse
from tagulous.models import TagField
from parler.managers import TranslatableManager
from parler.models import TranslatedFields, TranslatableModel

from vitrina.users.models import User
from vitrina.orgs.models import Organization
from vitrina.catalogs.models import Catalog, HarvestingJob
from vitrina.classifiers.models import Category, Licence, Frequency
from vitrina.datasets.managers import PublicDatasetManager

from django.utils.translation import gettext_lazy as _


class Dataset(TranslatableModel):
    HAS_DATA = "HAS_DATA"
    INVENTORED = "INVENTORED"
    METADATA = "METADATA"
    PRIORITIZED = "PRIORITIZED"
    FINANCING = "FINANCING"
    HAS_STRUCTURE = "HAS_STRUCTURE"
    STATUSES = {
        (HAS_DATA, _("Atvertas")),
        (INVENTORED, _("Inventorintas")),
        (METADATA, _("Parengti metaduomenys")),
        (PRIORITIZED, _("Įvertinti prioritetai")),
        (FINANCING, _("Įvertintas finansavimas")),
    }
    FILTER_STATUSES = {
        HAS_DATA: _("Atverti duomenys"),
        INVENTORED: _("Tik inventorintas"),
        HAS_STRUCTURE: _("Įkelta duomenų struktūra"),
        METADATA: _("Tik metaduomenys")
    }

    CREATED = "CREATED"
    EDITED = "EDITED"
    STATUS_CHANGED = "STATUS_CHANGED"
    TRANSFERRED = "TRANSFERRED"
    DATA_ADDED = "DATA_ADDED"
    DATA_UPDATED = "DATA_UPDATED"
    DELETED = "DELETED"
    HISTORY_MESSAGES = {
        CREATED: _("Sukurta"),
        EDITED: _("Redaguota"),
        STATUS_CHANGED: _("Pakeistas statusas"),
        TRANSFERRED: _("Perkelta"),
        DATA_ADDED: _("Pridėti duomenys"),
        DATA_UPDATED: _("Redaguoti duomenys"),
        DELETED: _("Ištrinta"),
    }

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
    category = models.ForeignKey(Category, models.DO_NOTHING, blank=False, null=True, verbose_name=_('Kategorija'))
    category_old = models.CharField(max_length=255, blank=True, null=True)

    catalog = models.ForeignKey(Catalog, models.DO_NOTHING, db_column='catalog', blank=True, null=True)
    origin = models.CharField(max_length=255, blank=True, null=True)

    organization = models.ForeignKey(Organization, models.DO_NOTHING, blank=True, null=True)

    licence = models.ForeignKey(Licence, models.DO_NOTHING, db_column='licence', blank=False, null=True, verbose_name=_('Licenzija'))

    status = models.CharField(max_length=255, choices=STATUSES, blank=True, null=True)
    published = models.DateTimeField(blank=True, null=True)
    is_public = models.BooleanField(default=False, verbose_name=_('Duomenų rinkinys viešinamas'))

    language = models.CharField(max_length=255, blank=True, null=True)
    spatial_coverage = models.CharField(max_length=255, blank=True, null=True)
    temporal_coverage = models.CharField(max_length=255, blank=True, null=True)

    update_frequency = models.CharField(max_length=255, blank=True, null=True)
    frequency = models.ForeignKey(Frequency, models.DO_NOTHING, blank=False, null=True, verbose_name=_('Atnaujinimo dažnumas'))
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

    # TODO: To be removed:
    # ---------------------------8<-------------------------------------
    meta = models.TextField(blank=True, null=True)

    # TODO: https://github.com/atviriduomenys/katalogas/issues/9
    priority_score = models.IntegerField(blank=True, null=True)

    # TODO: https://github.com/atviriduomenys/katalogas/issues/14
    structure_data = models.TextField(blank=True, null=True)
    structure_filename = models.CharField(max_length=255, blank=True, null=True)
    current_structure = models.ForeignKey('DatasetStructure', models.DO_NOTHING, related_name='+', blank=True, null=True)

    # TODO: https://github.com/atviriduomenys/katalogas/issues/26
    financed = models.BooleanField(blank=True, null=True)
    financing_plan_id = models.BigIntegerField(blank=True, null=True)
    financing_priorities = models.TextField(blank=True, null=True)
    financing_received = models.BigIntegerField(blank=True, null=True)
    financing_required = models.BigIntegerField(blank=True, null=True)
    will_be_financed = models.BooleanField(blank=True, default=False)
    # --------------------------->8-------------------------------------

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

    def get_absolute_url(self):
        return reverse('dataset-detail', kwargs={'pk': self.pk})

    def get_tag_list(self):
        return list(self.tags.all().values_list('name', flat=True))

    @property
    def filter_status(self):
        if self.datasetstructure_set.exists():
            return self.HAS_STRUCTURE
        if self.status == self.HAS_DATA or self.status == self.INVENTORED or self.status == self.METADATA:
            return self.status
        return None

    @property
    def formats(self):
        return [str(obj.get_format()).upper() for obj in self.datasetdistribution_set.all() if obj.get_format()]

    @property
    def distinct_formats(self):
        return sorted(set(self.formats))

    def get_acl_parents(self):
        parents = [self]
        if self.organization:
            parents.extend(self.organization.get_acl_parents())
        return parents

    def get_members_url(self):
        return reverse('dataset-members', kwargs={'pk': self.pk})


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
    user_0 = models.ForeignKey(User, models.DO_NOTHING, db_column='user_id', blank=True, null=True)  # Field renamed because of name conflict.

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


# TODO: https://github.com/atviriduomenys/katalogas/issues/14
class DatasetStructure(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    filename = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey(
        Dataset,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    file = models.FileField(
        upload_to='manifest/%Y/%m-%d',
        blank=True,
        null=True,
        max_length=512,
    )

    # Deprecatd feilds
    standardized = models.BooleanField(blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    distribution_version = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'dataset_structure'

    def get_absolute_url(self):
        return reverse('dataset-structure', kwargs={'pk': self.dataset.pk})


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

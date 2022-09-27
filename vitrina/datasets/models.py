from django.db import models
from django.urls import reverse
from parler.models import TranslatedFields, TranslatableModel

from vitrina.users.models import User
from vitrina.orgs.models import Organization
from vitrina.catalogs.models import Catalog
from vitrina.catalogs.models import HarvestingJob
from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Licence
from vitrina.classifiers.models import Frequency
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

    translations = TranslatedFields(
        title=models.CharField(_("Title"), blank=True, null=True),
        title_en=models.CharField(_("Title_en"), blank=True, null=True),
        description=models.TextField(_("Description"), blank=True, null=True),
        description_en=models.TextField(_("Description_en"), blank=True, null=True),
    )

    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    soft_deleted = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()

    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    internal_id = models.CharField(max_length=255, blank=True, null=True)

    theme = models.CharField(max_length=255, blank=True, null=True)
    category = models.ForeignKey(Category, models.DO_NOTHING, blank=True, null=True)
    category_old = models.CharField(max_length=255, blank=True, null=True)

    catalog = models.ForeignKey(Catalog, models.DO_NOTHING, db_column='catalog', blank=True, null=True)
    # catalog = models.ForeignKey(Catalog, models.DO_NOTHING, blank=True, null=True)
    origin = models.CharField(max_length=255, blank=True, null=True)

    organization = models.ForeignKey(Organization, models.DO_NOTHING, blank=True, null=True)
    coordinator = models.ForeignKey(User, models.DO_NOTHING, db_column='coordinator', blank=True, null=True)
    # coordinator = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    representative_id = models.BigIntegerField(blank=True, null=True)
    # TODO: Move this to orgs
    #       https://github.com/atviriduomenys/katalogas/issues/30
    manager = models.ForeignKey(User, models.DO_NOTHING, related_name='manager_datasets', blank=True, null=True)

    licence = models.ForeignKey(Licence, models.DO_NOTHING, db_column='licence', blank=True, null=True)
    # licence = models.ForeignKey('Licence', models.DO_NOTHING, blank=True, null=True)

    status = models.CharField(max_length=255, choices=STATUSES, blank=True, null=True)
    published = models.DateTimeField(blank=True, null=True)
    is_public = models.BooleanField(blank=True, null=True)

    language = models.CharField(max_length=255, blank=True, null=True)
    spatial_coverage = models.CharField(max_length=255, blank=True, null=True)
    temporal_coverage = models.CharField(max_length=255, blank=True, null=True)

    update_frequency = models.CharField(max_length=255, blank=True, null=True)
    frequency = models.ForeignKey(Frequency, models.DO_NOTHING, blank=True, null=True)
    last_update = models.DateTimeField(blank=True, null=True)

    access_rights = models.TextField(blank=True, null=True)
    distribution_conditions = models.TextField(blank=True, null=True)

    tags = models.TextField(blank=True, null=True)

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
    will_be_financed = models.BooleanField()
    # --------------------------->8-------------------------------------

    objects = models.Manager()
    public = PublicDatasetManager()

    class Meta:
        managed = True
        db_table = 'dataset'
        unique_together = (('internal_id', 'organization_id'),)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('dataset-detail', kwargs={'pk': self.pk})

    def get_tag_list(self):
        return str(self.tags).replace(" ", "").split(',') if self.tags else []


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
        managed = True
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
        managed = True
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
        managed = True
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
        managed = True
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
        managed = True
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
        managed = True
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
        managed = True
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
        managed = True
        db_table = 'dataset_resource_migrate'


# TODO: https://github.com/atviriduomenys/katalogas/issues/14
class DatasetStructure(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    distribution_version = models.IntegerField(blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)
    standardized = models.BooleanField(blank=True, null=True)
    file = models.FileField(upload_to="files/datasets/%Y/%m/%d/", blank=True, null=True)

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
        managed = True
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
        managed = True
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
        managed = True
        db_table = 'harvested_visit'
# --------------------------->8-------------------------------------

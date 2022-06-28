# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class ApiDescription(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    api_version = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.CharField(max_length=255, blank=True, null=True)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    contact_url = models.CharField(max_length=255, blank=True, null=True)
    desription_html = models.TextField(blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    licence = models.CharField(max_length=255, blank=True, null=True)
    licence_url = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'api_description'


class ApiKey(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    api_key = models.CharField(unique=True, max_length=255, blank=True, null=True)
    enabled = models.TextField(blank=True, null=True)  # This field type is a guess.
    expires = models.DateTimeField(blank=True, null=True)
    organization = models.ForeignKey('Organization', models.DO_NOTHING, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'api_key'


class ApplicationSetting(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    name = models.CharField(max_length=255, blank=True, null=True)
    value = models.TextField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'application_setting'


class ApplicationUsecase(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    author = models.CharField(max_length=255, blank=True, null=True)
    beneficiary = models.CharField(max_length=255, blank=True, null=True)
    platform = models.CharField(max_length=255, blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'application_usecase'


class ApplicationUsecaseDatasetIds(models.Model):
    application_usecase = models.ForeignKey(ApplicationUsecase, models.DO_NOTHING)
    dataset_ids = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'application_usecase_dataset_ids'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class Catalog(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    identifier = models.CharField(unique=True, max_length=255, blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    organization = models.ForeignKey('Licence', models.DO_NOTHING, blank=True, null=True)
    licence = models.ForeignKey('Licence', models.DO_NOTHING, blank=True, null=True, related_name = "licenses")
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    title_en = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'catalog'


class Category(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    description = models.CharField(max_length=255, blank=True, null=True)
    featured = models.TextField()  # This field type is a guess.
    icon = models.CharField(max_length=255, blank=True, null=True)
    parent_id = models.BigIntegerField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    edp_title = models.CharField(max_length=255, blank=True, null=True)
    title_en = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'category'


class CmsMenuItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'cms_menu_item'


class CmsPage(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    page_order = models.IntegerField(blank=True, null=True)
    published = models.TextField()  # This field type is a guess.
    slug = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    type = models.IntegerField(blank=True, null=True)
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    language = models.CharField(max_length=255, blank=True, null=True)
    list_children = models.TextField()  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'cms_page'


class Comment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    author_id = models.BigIntegerField(blank=True, null=True)
    author_name = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    dataset_id = models.BigIntegerField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_date = models.DateTimeField(blank=True, null=True)
    ip_address = models.CharField(max_length=255, blank=True, null=True)
    parent_id = models.BigIntegerField(blank=True, null=True)
    request_id = models.BigIntegerField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    dataset_uuid = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'comment'


class CssRuleOverride(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    active = models.TextField(blank=True, null=True)  # This field type is a guess.
    css_order = models.IntegerField(blank=True, null=True)
    css_override = models.TextField(blank=True, null=True)
    expires = models.DateTimeField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'css_rule_override'


class Dataset(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    # catalog_id = models.BigIntegerField(blank=True, null=True)
    category_old = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    financing_plan_id = models.BigIntegerField(blank=True, null=True)
    financing_priorities = models.TextField(blank=True, null=True)
    financing_required = models.BigIntegerField(blank=True, null=True)
    internal_id = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.TextField(blank=True, null=True)  # This field type is a guess.
    language = models.CharField(max_length=255, blank=True, null=True)
    # licence_id = models.BigIntegerField(blank=True, null=True)
    meta = models.TextField(blank=True, null=True)
    organization_id = models.BigIntegerField(blank=True, null=True)
    origin = models.CharField(max_length=255, blank=True, null=True)
    priority_score = models.IntegerField(blank=True, null=True)
    published = models.DateTimeField(blank=True, null=True)
    representative_id = models.BigIntegerField(blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    spatial_coverage = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    tags = models.TextField(blank=True, null=True)
    temporal_coverage = models.CharField(max_length=255, blank=True, null=True)
    theme = models.CharField(max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    update_frequency = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    # coordinator_id = models.BigIntegerField(blank=True, null=True)
    soft_deleted = models.DateTimeField(blank=True, null=True)
    financed = models.TextField(blank=True, null=True)  # This field type is a guess.
    financing_received = models.BigIntegerField(blank=True, null=True)
    will_be_financed = models.TextField()  # This field type is a guess.
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    catalog = models.ForeignKey(Catalog, models.DO_NOTHING, db_column='catalog', blank=True, null=True)
    licence = models.ForeignKey('Licence', models.DO_NOTHING, db_column='licence', blank=True, null=True)
    access_rights = models.TextField(blank=True, null=True)
    coordinator = models.ForeignKey('User', models.DO_NOTHING, db_column='coordinator', blank=True, null=True, related_name = "coordinators")
    manager = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    category = models.ForeignKey(Category, models.DO_NOTHING, blank=True, null=True)
    distribution_conditions = models.TextField(blank=True, null=True)
    description_en = models.TextField(blank=True, null=True)
    title_en = models.TextField(blank=True, null=True)
    last_update = models.DateTimeField(blank=True, null=True)
    structure_data = models.TextField(blank=True, null=True)
    structure_filename = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    frequency = models.ForeignKey('Frequency', models.DO_NOTHING, blank=True, null=True)
    current_structure = models.ForeignKey('DatasetStructure', models.DO_NOTHING, blank=True, null=True, related_name = "currentStructure")
    access_url = models.CharField(max_length=255, blank=True, null=True)
    download_url = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset'
        unique_together = (('internal_id', 'organization_id'),)


class DatasetDistribution(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    distribution_version = models.IntegerField(blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    issued = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    municipality = models.CharField(max_length=255, blank=True, null=True)
    period_end = models.CharField(max_length=255, blank=True, null=True)
    period_start = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    url_format = models.ForeignKey('Format', models.DO_NOTHING, blank=True, null=True)
    access_url = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset_distribution'


class DatasetEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    dataset_id = models.BigIntegerField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    details = models.CharField(max_length=255, blank=True, null=True)
    user = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    user_0 = models.ForeignKey('User', models.DO_NOTHING, db_column='user_id', blank=True, null=True)  # Field renamed because of name conflict.

    class Meta:
        managed = False
        db_table = 'dataset_event'


class DatasetMigrate(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset_migrate'


class DatasetRemark(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    author = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset_remark'


class DatasetResource(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    data = models.TextField(blank=True, null=True)
    dataset_id = models.BigIntegerField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
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
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset_resource'


class DatasetResourceMigrate(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    data = models.TextField(blank=True, null=True)
    dataset_id = models.BigIntegerField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
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
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset_resource_migrate'


class DatasetStructure(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    distribution_version = models.IntegerField(blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)
    standardized = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'dataset_structure'


class DatasetStructureField(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
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


class DatasetVisit(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    last_visited = models.DateTimeField(blank=True, null=True)
    visit_count = models.IntegerField()
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dataset_visit'


class DistributionFormat(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    title = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'distribution_format'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSite(models.Model):
    domain = models.CharField(max_length=100)
    name = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'django_site'


class DmkauthenticationEntry(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    admin_email = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dmkauthentication_entry'


class Dmkevent(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    sender = models.CharField(max_length=255, blank=True, null=True)
    attachment = models.CharField(max_length=255, blank=True, null=True)
    method = models.CharField(max_length=255, blank=True, null=True)
    receiver = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dmkevent'


class EmailTemplate(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    identifier = models.CharField(unique=True, max_length=255, blank=True, null=True)
    template = models.TextField(blank=True, null=True)
    variables = models.TextField(blank=True, null=True)
    subject = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'email_template'


class ExternalSite(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    imageuuid = models.CharField(max_length=36, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'external_site'


class Faq(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    answer = models.TextField(blank=True, null=True)
    question = models.TextField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'faq'


class FileResource(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    filename = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=36, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    obj_class = models.CharField(max_length=255, blank=True, null=True)
    obj_id = models.BigIntegerField(blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    type = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'file_resource'


class FinancingPlan(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    financed_datasets = models.IntegerField(blank=True, null=True)
    financing_plan_state_id = models.BigIntegerField(blank=True, null=True)
    projected_cost = models.IntegerField(blank=True, null=True)
    projected_datasets = models.IntegerField(blank=True, null=True)
    received_financing = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by', blank=True, null=True)
    organization = models.ForeignKey('Organization', models.DO_NOTHING, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'financing_plan'
        unique_together = (('organization', 'year'),)


class FinancingPlanState(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    details = models.TextField(blank=True, null=True)
    financing_plan_id = models.BigIntegerField(blank=True, null=True)
    status = models.IntegerField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'financing_plan_state'


class Format(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    extension = models.TextField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    mimetype = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'format'


class Frequency(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    title = models.TextField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    title_en = models.TextField(blank=True, null=True)
    uri = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'frequency'


class GeoportalLtEntry(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    raw_data = models.TextField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'geoportal_lt_entry'


class GlobalEmail(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'global_email'


class HarvestedVisit(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    last_visited = models.DateTimeField(blank=True, null=True)
    visit_count = models.IntegerField()
    harvesting_result = models.ForeignKey('HarvestingResult', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'harvested_visit'


class HarvestingJob(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    indexed = models.TextField(blank=True, null=True)  # This field type is a guess.
    schedule = models.CharField(max_length=255, blank=True, null=True)
    started = models.DateTimeField(blank=True, null=True)
    stopped = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    translated = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    organization = models.ForeignKey('Organization', models.DO_NOTHING, db_column='organization', blank=True, null=True)
    active = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'harvesting_job'


class HarvestingResult(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
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
    published = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'harvesting_result'


class LearningMaterial(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    learning_material_id = models.BigIntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    topic = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    video_url = models.CharField(max_length=255, blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    author_name = models.TextField(blank=True, null=True)
    published = models.DateField(blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    requested = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'learning_material'


class Licence(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    identifier = models.CharField(unique=True, max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'licence'


class Municipality(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    title = models.TextField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'municipality'


class NationalFinancingPlan(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    confirmation_date = models.DateTimeField(blank=True, null=True)
    confirmed = models.TextField(blank=True, null=True)  # This field type is a guess.
    confirmed_budget = models.BigIntegerField(blank=True, null=True)
    confirmed_by = models.BigIntegerField(blank=True, null=True)
    estimated_budget = models.BigIntegerField(blank=True, null=True)
    year = models.IntegerField(unique=True, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'national_financing_plan'


class NewsItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    author_id = models.BigIntegerField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    author = models.TextField(blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    published = models.DateTimeField(blank=True, null=True)
    author_name = models.TextField(blank=True, null=True)
    is_public = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'news_item'


class NewsletterSubscription(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    email = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    is_active = models.TextField()  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'newsletter_subscription'


class OldPassword(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    password = models.CharField(max_length=60, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'old_password'


class OpenDataGovLtEntry(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
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
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'open_data_gov_lt_entry'


class Organization(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    municipality = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    company_code = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.TextField(blank=True, null=True)  # This field type is a guess.
    phone = models.CharField(max_length=255, blank=True, null=True)
    jurisdiction = models.CharField(max_length=255, blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'organization'


class PartnerApplication(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    email = models.TextField(blank=True, null=True)
    letter = models.TextField(blank=True, null=True)
    organization_title = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    filename = models.TextField(blank=True, null=True)
    viisp_first_name = models.CharField(max_length=255, blank=True, null=True)
    viisp_email = models.CharField(max_length=255, blank=True, null=True)
    viisp_last_name = models.CharField(max_length=255, blank=True, null=True)
    viisp_phone = models.CharField(max_length=255, blank=True, null=True)
    viisp_dob = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'partner_application'


class PasswordResetToken(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    expiry_date = models.DateTimeField(blank=True, null=True)
    token = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING)
    used_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'password_reset_token'


class PublishedReport(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    data = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'published_report'


class Region(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'region'


class Report(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    body = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'report'


class Representative(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    email = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    organization_id = models.BigIntegerField(blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'representative'


class Request(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    dataset_id = models.BigIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    format = models.CharField(max_length=255, blank=True, null=True)
    is_existing = models.TextField()  # This field type is a guess.
    notes = models.CharField(max_length=255, blank=True, null=True)
    organization_id = models.BigIntegerField(blank=True, null=True)
    periodicity = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True, null=True)
    planned_opening_date = models.DateField(blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    changes = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.TextField()  # This field type is a guess.
    structure_data = models.TextField(blank=True, null=True)
    structure_filename = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'request'


class RequestEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    meta = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    request = models.ForeignKey(Request, models.DO_NOTHING, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'request_event'


class RequestStructure(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    data_notes = models.CharField(max_length=255, blank=True, null=True)
    data_title = models.CharField(max_length=255, blank=True, null=True)
    data_type = models.CharField(max_length=255, blank=True, null=True)
    dictionary_title = models.CharField(max_length=255, blank=True, null=True)
    request_id = models.BigIntegerField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'request_structure'


class SentMail(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    recipient = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sent_mail'


class SsoToken(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    ip = models.CharField(max_length=255, blank=True, null=True)
    token = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sso_token'


class Suggestion(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    body = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'suggestion'


class TermsOfUse(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    description = models.CharField(max_length=255, blank=True, null=True)
    file = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)
    published = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'terms_of_use'


class Usecase(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    beneficiary_group = models.CharField(max_length=255, blank=True, null=True)
    benefit = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    extra_information = models.TextField(blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usecase'


class UsecaseDatasetIds(models.Model):
    usecase = models.ForeignKey(Usecase, models.DO_NOTHING)
    dataset_ids = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usecase_dataset_ids'


class UsecaseLike(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    usecase_id = models.CharField(max_length=255, blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)
    usecase_uuid = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usecase_like'


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    email = models.CharField(unique=True, max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=60, blank=True, null=True)
    role = models.CharField(max_length=255, blank=True, null=True)
    organization = models.ForeignKey(Organization, models.DO_NOTHING, blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    needs_password_change = models.TextField()  # This field type is a guess.
    year_of_birth = models.IntegerField(blank=True, null=True)
    disabled = models.TextField()  # This field type is a guess.
    suspended = models.TextField()  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'user'


class UserDatasetSubscription(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    # dataset_id = models.BigIntegerField(blank=True, null=True)
    # user_id = models.BigIntegerField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, db_column='dataset', blank=True, null=True, related_name = "datasets")
    user = models.ForeignKey(User, models.DO_NOTHING, db_column='user', blank=True, null=True, related_name = "userId")
    active = models.TextField()  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'user_dataset_subscription'


class UserLike(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    request_id = models.BigIntegerField(blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_like'


class UserTablePreferences(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    table_column_string = models.TextField(blank=True, null=True)
    table_id = models.CharField(max_length=255, blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_table_preferences'


class UserVote(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(blank=True, null=True)
    deleted = models.TextField(blank=True, null=True)  # This field type is a guess.
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField()
    rating = models.IntegerField()
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    harvested = models.ForeignKey(HarvestingResult, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_vote'

from django.db import models

from vitrina.users.models import User


class CmsAttachment(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    file_data = models.TextField(blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    cms_page = models.ForeignKey('CmsPage', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'cms_attachment'


class CmsMenuItem(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'cms_menu_item'


class CmsPage(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    page_order = models.IntegerField(blank=True, null=True)
    published = models.BooleanField()
    slug = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    type = models.IntegerField(blank=True, null=True)
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    language = models.CharField(max_length=255, blank=True, null=True)
    list_children = models.BooleanField()

    class Meta:
        managed = True
        # XXX: Original table is name is `cms_page`, but it clashes with django-cms.
        db_table = 'adp_cms_page'


class CssRuleOverride(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    active = models.BooleanField(blank=True, null=True)
    css_order = models.IntegerField(blank=True, null=True)
    css_override = models.TextField(blank=True, null=True)
    expires = models.DateTimeField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'css_rule_override'


class ExternalSite(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    imageuuid = models.CharField(max_length=36, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'external_site'


class Faq(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    answer = models.TextField(blank=True, null=True)
    question = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'faq'


class FileResource(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    filename = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=36, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    obj_class = models.CharField(max_length=255, blank=True, null=True)
    obj_id = models.BigIntegerField(blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    type = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'file_resource'


class LearningMaterial(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    learning_material_id = models.BigIntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    topic = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    video_url = models.CharField(max_length=255, blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    author_name = models.TextField(blank=True, null=True)
    published = models.DateField(blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    requested = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'learning_material'


class NewsItem(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    author = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    author_name = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(blank=True, null=True)
    published = models.DateField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'news_item'


class TermsOfUse(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    file = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    imageuuid = models.CharField(max_length=36, blank=True, null=True)
    published = models.DateField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'terms_of_use'

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField

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
        managed = False
        db_table = 'cms_attachment'


class CmsMenuItem(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()

    class Meta:
        managed = False
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
        managed = False
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
        managed = False
        db_table = 'css_rule_override'


class ExternalSite(models.Model):
    EU_COMISSION_PORTAL = "EU_COMISSION_PORTAL"
    EU_LAND = "EU_LAND"
    OTHER_LAND = "OTHER_LAND"

    TYPE_CHOICES = (
        (EU_COMISSION_PORTAL, _("Europos komisijos portalai")),
        (EU_LAND, _("EU šalys")),
        (OTHER_LAND, _("Kitos šalys"))
    )

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    title = models.TextField(blank=True, null=True, verbose_name=_("Pavadinimas"))
    type = models.CharField(max_length=255, blank=True, null=True, choices=TYPE_CHOICES, verbose_name=_("Tipas"))
    url = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Nuoroda"))
    image = FilerImageField(
        null=True,
        blank=True,
        related_name="image_site",
        on_delete=models.SET_NULL,
        verbose_name=_("Paveikslėlis")
    )

    # Deprecated fields bellow
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        db_table = 'external_site'
        verbose_name = _("Portalas")
        verbose_name_plural = _("Portalai")

    def __str__(self):
        return self.title


class Faq(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    answer = models.TextField(blank=True, null=True, verbose_name=_('Atsakymas'))
    question = models.TextField(blank=True, null=True, verbose_name=_("Klausimas"))
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'faq'
        verbose_name = _("Dažnai užduodamas klausimas")
        verbose_name_plural = _("Dažnai užduodami klausimai")

    def __str__(self):
        return self.question


class FileResource(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()

    file = FilerFileField(
        null=True,
        blank=True,
        related_name="file_object",
        on_delete=models.CASCADE
    )
    content_type = models.ForeignKey(
        to=ContentType,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='content_type_files'
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Deprecated fields bellow
    filename = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=36, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    type = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'file_resource'


class LearningMaterial(models.Model):
    UPLOAD_TO = "data"
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True, verbose_name=_("Aprašymas"))
    learning_material_id = models.BigIntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    topic = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Pavadinimas"))
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    video_url = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Vaizdo įrašo nuoroda"))
    summary = models.TextField(blank=True, null=True, verbose_name=_("Santrauka"))
    author_name = models.TextField(blank=True, null=True, verbose_name=_("Autorius"))
    published = models.DateField(blank=True, null=True, verbose_name=_("Publikavimo data"))
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    requested = models.IntegerField(blank=True, null=True)
    image = FilerImageField(
        null=True,
        blank=True,
        related_name="image_learning_material",
        on_delete=models.SET_NULL,
        verbose_name=_("Paveikslėlis")
    )

    # Deprecated fields bellow
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        db_table = 'learning_material'
        verbose_name = _("Mokymosi medžiaga")
        verbose_name_plural = _("Mokymosi medžiaga")

    def __str__(self):
        return self.topic


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
    summary = models.TextField(blank=True, null=True)
    author_name = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(blank=True, null=True)
    published = models.DateField(blank=True, null=True)
    image = FilerImageField(null=True, blank=True, related_name="image_news_item", on_delete=models.SET_NULL)

    # Deprecated fields bellow
    imageuuid = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
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
        managed = False
        db_table = 'terms_of_use'

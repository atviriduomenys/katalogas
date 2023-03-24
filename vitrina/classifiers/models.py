from django.db import models
from treebeard.mp_tree import MP_Node, MP_NodeManager

from django.utils.translation import gettext_lazy as _
from parler.models import TranslatedFields, TranslatableModel

class Category(MP_Node, TranslatableModel):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1, blank=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    edp_title = models.CharField(max_length=255, blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        related_name='children_set',
        null=True,
        db_index=True,
        on_delete=models.SET_NULL,
        editable=False,
    )
    featured = models.BooleanField()
    icon = models.CharField(max_length=255,
                            blank=True,
                            help_text='Pasirinkite kategorijos paveikslėlį iš šios nuorodos: https://fontawesome.com/search')

    node_order_by = ['title']

    translations = TranslatedFields(
        title=models.TextField(_("Title"), blank=True),
        description=models.TextField(_("Description"), blank=True),
    )

    class Meta:
        verbose_name = _('Category')
        db_table = 'category'

    def __str__(self):
        return self.safe_translation_getter('title', language_code=self.get_current_language())

    def get_family_objects(self):
        yield from self.get_ancestors()
        yield from self.get_descendants()

    objects = MP_NodeManager()


class Licence(TranslatableModel):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    identifier = models.CharField(unique=True, max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)

    is_default = models.BooleanField(default=False)

    translations = TranslatedFields(
        title=models.TextField(_("Title"), blank=True),
        description=models.TextField(_("Description"), blank=True),
    )

    class Meta:
        verbose_name = _('License')
        db_table = 'licence'

    def __str__(self):
        return self.safe_translation_getter('title', language_code=self.get_current_language())


class Frequency(TranslatableModel):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    uri = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    hours = models.IntegerField(verbose_name=_('Valandos'), blank=True, null=True)

    translations = TranslatedFields(
        title=models.TextField(_("Title"), blank=True),
    )

    class Meta:
        verbose_name = _('Frequency')
        db_table = 'frequency'
        ordering = ['hours']

    def __str__(self):
        return self.safe_translation_getter('title', language_code=self.get_current_language())
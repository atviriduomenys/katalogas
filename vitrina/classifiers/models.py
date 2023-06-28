from django.db import models
from treebeard.mp_tree import MP_Node, MP_NodeManager

from django.utils.translation import gettext_lazy as _


class Category(MP_Node):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1, blank=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    title_en = models.CharField(max_length=255, blank=True, null=True)
    edp_title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
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
                            help_text='Naudokite "glyph" pavadinimą iš icomoon.svg failo')
    groups = models.ManyToManyField(to='vitrina_datasets.DatasetGroup')

    node_order_by = ['title']

    class Meta:
        db_table = 'category'

    def __str__(self):
        return self.title

    def get_family_objects(self):
        yield from self.get_ancestors()
        yield from self.get_descendants()

    objects = MP_NodeManager()


class Licence(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    identifier = models.CharField(unique=True, max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)

    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'licence'

    def __str__(self):
        return self.title


class Frequency(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    title = models.TextField(blank=True, null=True)
    title_en = models.TextField(blank=True, null=True)
    uri = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    hours = models.IntegerField(verbose_name=_('Valandos'), blank=True, null=True)

    class Meta:
        db_table = 'frequency'
        ordering = ['hours']

    def __str__(self):
        return self.title

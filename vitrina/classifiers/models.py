from django.core.exceptions import ObjectDoesNotExist
from django.db import models


class Category(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    title = models.CharField(max_length=255, blank=True, null=True)
    title_en = models.CharField(max_length=255, blank=True, null=True)
    edp_title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    parent_id = models.BigIntegerField(blank=True, null=True)

    featured = models.BooleanField()

    icon = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'category'

    def __str__(self):
        return self.title

    def get_parents(self, include_self=False):
        parents = []
        if include_self:
            parents.append(self)
        if self.parent_id:
            try:
                parent = Category.objects.get(pk=self.parent_id)
            except ObjectDoesNotExist:
                parent = None
            if parent:
                parents.extend(parent.get_parents(include_self=True))
        return parents

    def get_children(self, include_self=False):
        all_children = []
        children = Category.objects.filter(parent_id=self.pk)
        if include_self:
            all_children.append(self)
        for child in children:
            all_children.extend(child.get_children(include_self=True))
        return all_children

    def get_family_objects(self):
        parents = self.get_parents()
        children = self.get_children()
        parents.extend(children)
        return parents


class Licence(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    identifier = models.CharField(unique=True, max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)

    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'licence'

    def __str__(self):
        return self.title


class Frequency(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    title = models.TextField(blank=True, null=True)
    title_en = models.TextField(blank=True, null=True)
    uri = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'frequency'

    def __str__(self):
        return self.title

from haystack.fields import CharField, IntegerField, MultiValueField, DateTimeField, EdgeNgramField
from django.db import models

from haystack import signals
from haystack.exceptions import NotHandled
from haystack.indexes import SearchIndex, Indexable

from vitrina.datasets.models import Dataset


class DatasetIndex(SearchIndex, Indexable):
    text = EdgeNgramField(document=True, use_template=True)
    lt_title = CharField(model_attr='lt_title')
    lt_title_s = CharField(model_attr='lt_title', indexed=False, stored=True)
    en_title = CharField(model_attr='en_title')
    en_title_s = CharField(model_attr='en_title', indexed=False, stored=True)
    jurisdiction = MultiValueField(model_attr='jurisdiction', faceted=True, null=True)
    organization = MultiValueField(model_attr='organization__pk', faceted=True, null=True)
    groups = MultiValueField(model_attr='get_group_list', faceted=True)
    category = MultiValueField(model_attr='category__pk', faceted=True)
    parent_category = MultiValueField(model_attr='parent_category', faceted=True, null=True)
    tags = MultiValueField(model_attr='get_tag_list', faceted=True)
    formats = MultiValueField(model_attr='filter_formats', faceted=True)
    frequency = IntegerField(model_attr='frequency__pk', faceted=True)
    published = DateTimeField(model_attr='published', null=True, faceted=True)
    status = CharField(model_attr='filter_status', faceted=True, null=True)
    level = IntegerField(model_attr='get_level', faceted=True, null=True)
    type = MultiValueField(model_attr='public_types', faceted=True)
    type_order = IntegerField(model_attr='type_order')

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        return self.get_model().objects.all().filter(translations__title__isnull=False).distinct()

    def prepare_category(self, obj):
        categories = []
        for category in obj.category.all():
            categories = [cat.pk for cat in category.get_ancestors() if cat.dataset_set.exists()]
            categories.append(category.pk)
        return categories

    def prepare_organization(self, obj):
        if obj.organization.pk != obj.jurisdiction:
            return obj.organization.pk


class CustomSignalProcessor(signals.BaseSignalProcessor):
    def setup(self):
        models.signals.post_save.connect(self.handle_save)
        models.signals.post_delete.connect(self.handle_delete)

    def teardown(self):
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.post_delete.disconnect(self.handle_delete)

    def handle_save(self, sender, instance, **kwargs):
        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            try:
                index = self.connections[using].get_unified_index().get_index(sender)
                if index.index_queryset().filter(pk=instance.pk):
                    index.update_object(instance, using=using)
                else:
                    index.remove_object(instance, using=using)

            except NotHandled:
                pass

from haystack.constants import Indexable
from haystack.fields import CharField, IntegerField, MultiValueField, DateTimeField
from haystack.indexes import SearchIndex

from vitrina.datasets.models import Dataset


class DatasetIndex(SearchIndex, Indexable):
    text = CharField(document=True, use_template=True)
    lt_title = CharField(model_attr='lt_title')
    en_title = CharField(model_attr='en_title')
    organization = IntegerField(model_attr='organization__pk', faceted=True)
    category = MultiValueField(model_attr='category__pk', faceted=True)
    tags = MultiValueField(model_attr='get_tag_list', faceted=True)
    formats = MultiValueField(model_attr='formats', faceted=True)
    frequency = IntegerField(model_attr='frequency__pk', faceted=True)
    published = DateTimeField(model_attr='published', null=True)
    filter_status = CharField(model_attr='filter_status', faceted=True, null=True)

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        return self.get_model().public.filter(translations__title__isnull=False).distinct()

    def prepare_category(self, obj):
        categories = []
        if obj.category:
            categories = [cat.pk for cat in obj.category.get_ancestors() if cat.dataset_set.exists()]
            categories.append(obj.category.pk)
        return categories


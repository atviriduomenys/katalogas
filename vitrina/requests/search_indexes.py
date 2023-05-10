from haystack.fields import CharField, IntegerField, MultiValueField, DateTimeField
from django.db import models

from haystack import signals
from haystack.exceptions import NotHandled
from haystack.indexes import SearchIndex, Indexable

from vitrina.requests.models import Request




class RequestIndex(SearchIndex, Indexable):
    text = CharField(document=True, use_template=True)
    title = CharField(model_attr='title')
    filter_status = CharField(model_attr='dataset__status',  faceted=True, null=True)
    organization = IntegerField(model_attr='dataset__organization__pk', faceted=True)
    category = MultiValueField(model_attr='dataset__category__pk', faceted=True)
    parent_category = MultiValueField(model_attr='dataset__parent_category', faceted=True, null=True)
    groups = MultiValueField(model_attr='dataset__get_group_list', faceted=True)
    tags = MultiValueField(model_attr='dataset__get_tag_list', faceted=True)
    created = DateTimeField(model_attr='created', null=True)


    def get_model(self):
        return Request

    def index_queryset(self, using=None):
        return self.get_model().public.filter().distinct()

    def prepare_category(self, obj):
        categories = []
        if obj.dataset and obj.dataset.category:
            categories = [cat.pk for cat in obj.dataset.category.get_ancestors() if cat.dataset_set.exists()]
            categories.append(obj.dataset.category.pk)
        return categories
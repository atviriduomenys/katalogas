from haystack.fields import CharField, IntegerField, MultiValueField, DateTimeField
from haystack.indexes import SearchIndex, Indexable
from vitrina.requests.models import Request


class RequestIndex(SearchIndex, Indexable):
    text = CharField(document=True, use_template=True)
    title = CharField(model_attr='title')
    status = CharField(model_attr='status', faceted=True, null=True)
    dataset_status = MultiValueField(model_attr='dataset_statuses',  faceted=True, default="UNASSIGNED")
    organization = MultiValueField(model_attr='organizations__pk', faceted=True, default=-1)
    jurisdiction = MultiValueField(model_attr='jurisdiction', faceted=True)
    category = MultiValueField(model_attr='dataset_categories', faceted=True)
    parent_category = MultiValueField(model_attr='dataset_parent_categories', faceted=True, null=True)
    groups = MultiValueField(model_attr='dataset_group_list', faceted=True)
    tags = MultiValueField(model_attr='dataset_get_tag_list', faceted=True)
    created = DateTimeField(model_attr='created', null=True)


    def get_model(self):
        return Request

    def index_queryset(self, using=None):
        return self.get_model().public.filter().distinct()

    def prepare_category(self, obj):
        categories = []
        if obj.dataset and obj.dataset.category:
            for category in obj.dataset.category.all():
                categories = [cat.pk for cat in category.get_ancestors() if cat.dataset_set.exists()]
                categories.append(category.pk)
        return categories
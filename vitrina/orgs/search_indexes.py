from haystack.fields import CharField, IntegerField, MultiValueField, DateTimeField
from haystack.indexes import SearchIndex, Indexable
from vitrina.orgs.models import Organization




class OrganizationIndex(SearchIndex, Indexable):
    text = CharField(document=True, use_template=True)
    title = CharField(model_attr='title')
    dataset_tags = MultiValueField(model_attr='dataset_tags', faceted=True)

    def get_model(self):
        return Organization

    def index_queryset(self, using=None):
        return self.get_model().public.filter().distinct()
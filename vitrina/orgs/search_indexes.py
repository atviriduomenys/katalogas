from haystack.fields import CharField, EdgeNgramField, MultiValueField
from haystack.indexes import SearchIndex, Indexable
from vitrina.orgs.models import Organization


class OrganizationIndex(SearchIndex, Indexable):
    text = EdgeNgramField(document=True, use_template=True)
    title = CharField(model_attr='title')
    title_s = CharField(model_attr='title', indexed=False, stored=True)
    jurisdiction = MultiValueField(model_attr='jurisdiction__pk', null=True)

    def get_model(self):
        return Organization

    def index_queryset(self, using=None):
        return self.get_model().objects.all().filter().distinct()

    def prepare_title_s(self, obj):
        return obj.title

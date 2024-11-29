from haystack.constants import Indexable
from haystack.fields import EdgeNgramField, CharField, DateTimeField, IntegerField
from haystack.indexes import SearchIndex

from vitrina.tasks.models import Task


class TaskIndex(SearchIndex, Indexable):
    text = EdgeNgramField(document=True, use_template=True)
    due_date = DateTimeField(model_attr='due_date', null=True)
    user = IntegerField(model_attr='get_user_id', null=True)
    type = CharField(model_attr='get_type', faceted=True)
    status = CharField(model_attr='status', faceted=True)

    def get_model(self):
        return Task

from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.forms import CharField
from haystack.backends import SQ
from haystack.forms import FacetedSearchForm

from vitrina.tasks.models import Task


class TaskSearchForm(FacetedSearchForm):
    owner = CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", [])
        super().__init__(*args, **kwargs)

    def search(self):
        sqs = super().search()
        sqs = sqs.models(Task)
        if not self.is_valid():
            return self.no_query_found()
        if self.cleaned_data.get('q'):
            keyword = self.cleaned_data.get('q')

            if len(keyword) >= 5:
                task_ids = Task.objects.annotate(
                    user_name=Concat('user__first_name', Value(' '), 'user__last_name')
                ).filter(
                    Q(title__icontains=keyword) |
                    Q(description__icontains=keyword) |
                    Q(organization__title__icontains=keyword) |
                    Q(user_name__icontains=keyword)
                ).values_list('pk', flat=True)
            elif len(keyword) >= 2:
                task_ids = Task.objects.annotate(
                    user_name=Concat('user__first_name', Value(' '), 'user__last_name')
                ).filter(
                    Q(title__istartswith=keyword) |
                    Q(description__istartswith=keyword) |
                    Q(organization__title__istartswith=keyword) |
                    Q(user_name__istartswith=keyword)
                ).values_list('pk', flat=True)
            else:
                task_ids = []

            sqs_ids = sqs.values_list('pk', flat=True)
            sqs = self.searchqueryset.models(Task).filter(SQ(id__in=task_ids) | SQ(id__in=sqs_ids))

            for facet in self.selected_facets:
                if ":" not in facet:
                    continue

                field, value = facet.split(":", 1)
                if value:
                    sqs = sqs.narrow('%s:"%s"' % (field, sqs.query.clean(value)))

            owner = self.cleaned_data.get('owner', 'all')
            if owner == 'user':
                sqs = sqs.filter(user__pk=self.user.pk)

        return sqs

    def no_query_found(self):
        return self.searchqueryset.all()

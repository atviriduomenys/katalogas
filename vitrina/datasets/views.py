from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.db.models import Q

from vitrina.datasets.models import Dataset
from vitrina.datasets.services import filter_by_status, get_related_categories
from vitrina.orgs.models import Organization
from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Frequency


class DatasetListView(ListView):
    model = Dataset
    queryset = Dataset.public.order_by('-published')
    template_name = 'vitrina/datasets/list.html'
    paginate_by = 20


class DatasetDetailView(DetailView):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'


class DatasetSearchResultsView(ListView):
    model = Dataset
    template_name = 'vitrina/datasets/list.html'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        status = self.request.GET.get('status')
        tags = self.request.GET.getlist('tags')
        categories = self.request.GET.getlist('category')
        filter_dict = self.request.GET.dict()
        filter_dict.pop('q', None)
        filter_dict.pop('date_from', None)
        filter_dict.pop('date_to', None)
        filter_dict.pop('status', None)
        filter_dict.pop('tags', None)
        filter_dict.pop('category', None)
        datasets = Dataset.public.order_by('-published')

        if query:
            datasets = datasets.filter(
                Q(title__icontains=query) | Q(title_en__icontains=query)
            )
        if date_from and date_to:
            datasets = datasets.filter(Q(published__gt=date_from) & Q(published__lt=date_to))
        elif date_from:
            datasets = datasets.filter(published__gt=date_from)
        elif date_to:
            datasets = datasets.filter(published__lt=date_to)
        if status:
            datasets = filter_by_status(datasets, status)
        if tags:
            for tag in tags:
                datasets = datasets.filter(tags__icontains=tag)
        if categories:
            related_categories = get_related_categories(categories, only_children=True)
            datasets = datasets.filter(category__pk__in=related_categories)
        if filter_dict:
            datasets = datasets.filter(**filter_dict)
        return datasets

    def get_selected_value(self, title, multiple=False, is_int=True):
        selected_value = [] if multiple else None
        value = self.request.GET.getlist(title) if multiple else self.request.GET.get(title)
        if value:
            selected_value = value
            if is_int:
                try:
                    selected_value = [int(val) for val in value] if multiple else int(value)
                except ValueError:
                    pass
        return selected_value

    def get_context_data(self, **kwargs):
        context = super(DatasetSearchResultsView, self).get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()
        query = self.request.GET.urlencode()

        selected_status = self.get_selected_value('status', is_int=False)
        selected_organization = self.get_selected_value('organization')
        selected_categories = self.get_selected_value('category', multiple=True)
        selected_frequency = self.get_selected_value('frequency')
        selected_tags = self.get_selected_value('tags', multiple=True, is_int=False)
        selected_date_from = self.get_selected_value('date_from', is_int=False)
        selected_date_to = self.get_selected_value('date_to', is_int=False)

        related_categories = get_related_categories(selected_categories)

        # after task #118 tags filter should be redone
        tags = Dataset.public.exclude(tags="").exclude(tags__isnull=True).values_list('tags', flat=True)
        tag_list = []
        for dataset_tags in tags:
            dataset_tags = dataset_tags.replace(" ", "").split(",")
            tag_list.extend(dataset_tags)
        tag_list = list(set(tag_list))

        related_tag_list = []
        if selected_tags:
            related_tags = filtered_queryset.exclude(tags="").exclude(tags__isnull=True).values_list('tags', flat=True)
            related_tag_list = []
            for dataset_tags in related_tags:
                dataset_tags = dataset_tags.replace(" ", "").split(",")
                related_tag_list.extend(dataset_tags)
            related_tag_list = list(set(related_tag_list))
            related_tag_list.sort()

        status_counts = {}
        for status in Dataset.FILTER_STATUSES.keys():
            status_counts[status] = filter_by_status(filtered_queryset, status).count()

        category_counts = {}
        if selected_categories:
            for category in related_categories:
                try:
                    category = Category.objects.get(pk=category)
                except ObjectDoesNotExist:
                    category_counts[category] = 0
                    continue
                count = filtered_queryset.filter(category=category).count()
                children = category.get_descendants()
                for ch in children:
                    count += filtered_queryset.filter(category=ch).count()
                category_counts[category.pk] = count
        else:
            for category in Category.objects.all():
                count = filtered_queryset.filter(category=category).count()
                children = category.get_descendants()
                for ch in children:
                    count += filtered_queryset.filter(category=ch).count()
                category_counts[category.pk] = count

        extra_context = {
            'num_found': filtered_queryset.count(),
            'status_filters': [{
                'key': key,
                'title': value,
                'query': "?%s%sstatus=%s" % (query, "&" if query else "", key),
                'count': status_counts.get(key, 0)
            } for key, value in Dataset.FILTER_STATUSES.items() if status_counts.get(key, 0) > 0],
            'selected_status': selected_status,

            'organization_filters': [{
                'id': org.pk,
                'title': org.title,
                'query': "?%s%sorganization=%s" % (query, "&" if query else "", org.pk),
                'count': filtered_queryset.filter(organization=org).count()
            } for org in Organization.objects.order_by('title')
                if filtered_queryset.filter(organization=org).count() > 0],
            'selected_organization': selected_organization,

            'category_filters': [{
                'id': category.pk,
                'title': category.title,
                'query': "?%s%scategory=%s" % (query, "&" if query else "", category.pk),
                'count': category_counts.get(category.pk, 0)
            } for category in Category.objects.order_by('title') if category_counts.get(category.pk, 0) > 0],
            'selected_categories': selected_categories,
            'related_categories': related_categories,

            'frequency_filters': [{
                'id': frequency.pk,
                'title': frequency.title,
                'query': "?%s%sfrequency=%s" % (query, "&" if query else "", frequency.pk),
                'count': filtered_queryset.filter(frequency=frequency).count()
            } for frequency in Frequency.objects.order_by('title')
                if filtered_queryset.filter(frequency=frequency).count() > 0],
            'selected_frequency': selected_frequency,

            'tag_filters': [{
                'title': tag,
                'query': "?%s%stags=%s" % (query, "&" if query else "", tag) if "tags=%s" % tag not in query else "?%s" % query,
                'count': filtered_queryset.filter(tags__icontains=tag).count()
            } for tag in tag_list if filtered_queryset.filter(tags__icontains=tag).count() > 0],
            'selected_tags': selected_tags,
            'related_tags': related_tag_list,

            'selected_date_from': selected_date_from,
            'selected_date_to': selected_date_to,
        }
        context.update(extra_context)
        return context

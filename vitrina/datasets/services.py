from vitrina.classifiers.models import Category
from vitrina.datasets.models import Dataset


def filter_by_status(queryset, status):
    if status == Dataset.HAS_STRUCTURE:
        return queryset.filter(datasetstructure__isnull=False)
    else:
        return queryset.filter(status=status)


def get_related_categories(selected_categories, only_children=False):
    related_categories = []
    selected_category_objects = Category.objects.filter(pk__in=selected_categories)
    for selected in selected_category_objects:
        related_categories.append(selected.pk)
        if only_children:
            family_objects = [obj.pk for obj in selected.get_descendants()]
        else:
            family_objects = [obj.pk for obj in selected.get_family_objects()]
        related_categories.extend(family_objects)
    if len(selected_category_objects) > 1:
        related_categories = [category for category in related_categories
                              if related_categories.count(category) == len(selected_category_objects)]
    related_categories = list(set(related_categories))
    related_categories.sort()
    return related_categories

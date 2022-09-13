from typing import List, Any, Dict

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

from vitrina.classifiers.models import Category
from vitrina.datasets.models import Dataset


def filter_by_status(queryset: QuerySet, status: str) -> QuerySet:
    if status == Dataset.HAS_STRUCTURE:
        return queryset.filter(datasetstructure__isnull=False)
    else:
        return queryset.filter(status=status)


def get_related_categories(selected_categories: List[Any], only_children: bool = False) -> List[Any]:
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


def get_tag_list() -> List[Any]:
    # after task #118 tags filter should be redone
    tags = Dataset.public.exclude(tags="").exclude(tags__isnull=True).values_list('tags', flat=True)
    tag_list = []
    for dataset_tags in tags:
        dataset_tags = dataset_tags.replace(" ", "").split(",")
        tag_list.extend(dataset_tags)
    tag_list = list(set(tag_list))
    return tag_list


def get_related_tag_list(selected_tags: List[Any], queryset: QuerySet) -> List[Any]:
    related_tag_list = []
    if selected_tags:
        related_tags = queryset.exclude(tags="").exclude(tags__isnull=True).values_list('tags', flat=True)
        related_tag_list = []
        for dataset_tags in related_tags:
            dataset_tags = dataset_tags.replace(" ", "").split(",")
            related_tag_list.extend(dataset_tags)
        related_tag_list = list(set(related_tag_list))
        related_tag_list.sort()
    return related_tag_list


def get_category_counts(selected_categories: List[Any], related_categories: List[Any],
                        queryset: QuerySet) -> Dict[str, Any]:
    category_counts = {}
    if selected_categories:
        for category in related_categories:
            try:
                category = Category.objects.get(pk=category)
            except ObjectDoesNotExist:
                category_counts[category] = 0
                continue
            count = queryset.filter(category=category).count()
            children = category.get_descendants()
            for ch in children:
                count += queryset.filter(category=ch).count()
            category_counts[category.pk] = count
    else:
        for category in Category.objects.all():
            count = queryset.filter(category=category).count()
            children = category.get_descendants()
            for ch in children:
                count += queryset.filter(category=ch).count()
            category_counts[category.pk] = count
    return category_counts

from django.db.models import Case, IntegerField, Value, When, QuerySet
from django_select2.forms import ModelSelect2MultipleWidget, ModelSelect2Widget

from vitrina.classifiers.models import Category
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization

EU_DATA_THEME_URI_PREFIX = "http://publications.europa.eu/resource/authority/data-theme"


class OrganizationWidgetMixin:
    model = Organization
    search_fields = ["title__icontains"]
    max_results = 10

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("attrs", {}).setdefault("data-minimum-input-length", 0)
        super().__init__(*args, **kwargs)


class OrganizationSingleWidget(OrganizationWidgetMixin, ModelSelect2Widget):
    pass


class OrganizationMultipleWidget(OrganizationWidgetMixin, ModelSelect2MultipleWidget):
    pass


class CategoryMultipleWidget(ModelSelect2MultipleWidget):
    model = Category
    search_fields = ["title__icontains"]
    max_results = 10

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("attrs", {}).setdefault("data-minimum-input-length", 0)
        super().__init__(*args, **kwargs)

    def get_queryset(self) -> QuerySet[Category]:
        return Category.objects.annotate(
            is_eu_theme=Case(
                When(uri__startswith=EU_DATA_THEME_URI_PREFIX, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("is_eu_theme", "title")


class DatasetMultipleWidget(ModelSelect2MultipleWidget):
    model = Dataset
    search_fields = ["translations__title__icontains"]
    max_results = 10

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("attrs", {}).setdefault("data-minimum-input-length", 0)
        super().__init__(*args, **kwargs)

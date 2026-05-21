from django_select2.forms import ModelSelect2MultipleWidget, ModelSelect2Widget

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization


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


class DatasetMultipleWidget(ModelSelect2MultipleWidget):
    model = Dataset
    search_fields = ["translations__title__icontains"]
    max_results = 10

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("attrs", {}).setdefault("data-minimum-input-length", 0)
        super().__init__(*args, **kwargs)

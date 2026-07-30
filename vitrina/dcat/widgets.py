from typing import Any

from django.db.models import Case, IntegerField, Value, When, QuerySet
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2MultipleWidget, ModelSelect2Widget, Select2Widget

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


class AccessRightsSelectWidget(Select2Widget):
    """Adds icon/description data attributes per option, rendered by formatSelect2Option() in wizard.html."""

    icon_paths: dict[str, str] = {
        Dataset.PUBLIC: "img/access-rights/public.svg",
        Dataset.RESTRICTED: "img/access-rights/restricted.svg",
        Dataset.NON_PUBLIC: "img/access-rights/non_public.svg",
        Dataset.CONFIDENTIAL: "img/access-rights/confidential.svg",
    }
    descriptions: dict[str, str] = {
        Dataset.PUBLIC: _("Metaduomenys publikuojami viešai visiems vartotojams"),
        Dataset.RESTRICTED: _("Metaduomenys publikuojami viešai visiems vartotojams"),
        Dataset.NON_PUBLIC: _(
            "Metaduomenys publikuojami tik visiems registruotiems viešojo sektoriaus duomenų tvarkytojams"
        ),
        Dataset.CONFIDENTIAL: _("Metaduomenys publikuojami tik institucijos metaduomenų tvarkytojui"),
    }

    def create_option(
        self,
        name: str,
        value: Any,
        label: int | str,
        selected: bool,
        index: int,
        subindex: int | None = None,
        attrs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        icon_path = self.icon_paths.get(value)
        description = self.descriptions.get(value)
        if icon_path:
            option["attrs"]["data-icon"] = static(icon_path)
        if description:
            option["attrs"]["data-description"] = description
        return option

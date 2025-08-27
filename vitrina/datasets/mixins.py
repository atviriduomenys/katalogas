from dataclasses import dataclass
from typing import List, Optional

from django.utils.translation import gettext_lazy as _
from django.urls import reverse


@dataclass(frozen=True)
class Crumb:
    title: str
    url: str | None
    is_current: bool = False


class BaseBreadcrumbsMixin:
    include_home_in_breadcrumbs: bool = True
    breadcrumb_title: Optional[str] = None
    breadcrumb_url: Optional[str] = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = self.get_breadcrumbs()
        return context

    def breadcrumbs_home(self):
        return [Crumb(title=_("Pradžia"), url=reverse("home"))]

    def get_breadcrumb_title(self) -> Optional[str]:
        """Get custom breadcrumb title - override in subclasses"""
        return self.breadcrumb_title

    def get_breadcrumb_url(self) -> Optional[str]:
        """Get custom breadcrumb URL - override in subclasses"""
        return self.breadcrumb_url

    def append_current_crumb(self, crumbs: List[Crumb]) -> List[Crumb]:
        """Add current page crumb to breadcrumbs"""
        title = self.get_breadcrumb_title()
        if title:
            crumbs.append(Crumb(title=title, url=self.get_breadcrumb_url(), is_current=True))
        return crumbs

    def get_breadcrumbs(self) -> List[Crumb]:
        """Default breadcrumb generation - override in subclasses"""
        if self.include_home_in_breadcrumbs:
            return self.breadcrumbs_home()
        return []

    def breadcrumbs_organization(self, organization) -> List[Crumb]:
        """Generate breadcrumbs up to organization level"""
        crumbs = []
        if self.include_home_in_breadcrumbs:
            crumbs.extend(self.breadcrumbs_home())
        crumbs.append(Crumb(title=organization.title, url=organization.get_absolute_url()))
        return crumbs


class DatasetBreadcrumbsMixin(BaseBreadcrumbsMixin):
    def _org_for_dataset(self, dataset):
        ancestors = dataset.get_ancestors()
        if ancestors.exists():
            return ancestors.first().organization
        return dataset.organization

    def dataset_hierarchy(self, dataset, include_home=True, make_current=False) -> List[Crumb]:
        """Generate full dataset hierarchy breadcrumbs"""
        crumbs: List[Crumb] = []

        if include_home:
            crumbs.extend(self.breadcrumbs_home())

        organization = self._org_for_dataset(dataset)
        if organization:
            crumbs.append(Crumb(title=organization.title, url=organization.get_absolute_url()))

        for node in dataset.get_ancestors():
            crumbs.append(Crumb(title=node.title, url=node.get_absolute_url()))

        crumbs.append(
            Crumb(
                title=dataset.title,
                url=None if make_current else dataset.get_absolute_url(),
                is_current=make_current,
            )
        )
        return crumbs

    def get_dataset(self):
        if hasattr(self, "object") and hasattr(self.object, "get_ancestors"):
            return self.object
        elif hasattr(self, "get_object"):
            obj = self.get_object()
            if hasattr(obj, "get_ancestors"):
                return obj
            elif hasattr(obj, "dataset"):
                return obj.dataset
        return None

    def get_breadcrumbs(self) -> List[Crumb]:
        dataset = self.get_dataset()
        if not dataset:
            return super().get_breadcrumbs()

        crumbs = self.dataset_hierarchy(
            dataset, include_home=self.include_home_in_breadcrumbs, make_current=not self.get_breadcrumb_title()
        )
        return self.append_current_crumb(crumbs)

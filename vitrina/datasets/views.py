import itertools
import secrets
import json
import uuid
from datetime import datetime, date
from functools import cached_property
from typing import List, Any, Type as TypingType
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import QuerySet, Count, Max, Q, Avg, Sum, Func, F, Value, TextField
from django.forms import BaseForm
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.http.response import HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import date as _date
from django.urls import reverse, reverse_lazy, resolve
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from haystack.backends import SQ
from haystack.generic_views import FacetedSearchView
from haystack.query import SearchQuerySet
from itsdangerous import URLSafeSerializer
from parler.utils.context import switch_language
from parler.utils.i18n import get_language
from parler.views import (
    TranslatableUpdateView,
    TranslatableCreateView,
    LanguageChoiceMixin,
    ViewUrlMixin,
)
from reversion import add_to_revision
from reversion.models import Version

from vitrina.structure.models import Version as _Version
from vitrina.api.helpers import get_datasets_for_rdf
from vitrina.api.models import ApiKey
from vitrina.comments.models import Comment
from vitrina.datasets.forms import (
    DatasetStructureImportForm,
    ResourceForm,
    DatasetSearchForm,
    AddProjectForm,
    DatasetAttributionForm,
    DatasetCategoryForm,
    DatasetMemberCreateForm,
    DatasetMemberUpdateForm,
    DatasetRelationForm,
    DatasetPlanForm,
    PlanForm,
    AddRequestForm,
    ResourceSubclassForm,
    ServiceResourceForm,
    InformationSystemResourceForm,
    DatasetResourceForm,
    CatalogResourceForm,
)
from vitrina.datasets.helpers import is_manager_dataset_list, generate_unique_dataset_name, is_child_resources_list
from vitrina.structure import VersionStatus
from vitrina.structure.views import DatasetStructureMixin

from vitrina.tasks.models import Task
from vitrina.uapi.models import Agent
from vitrina.views import HistoryView, HistoryMixin, PlanMixin
from vitrina.datasets.mixins import DatasetBreadcrumbsMixin, Crumb
from vitrina.datasets.services import (
    update_facet_data,
    get_frequency_and_format,
    get_requests,
    get_datasets_for_user,
    sort_publication_stats,
    sort_publication_stats_reversed,
    get_total_by_indicator_from_stats,
    has_remove_from_request_perm,
    get_values_for_frequency,
    get_query_for_frequency,
    DynamicResourceService,
    manage_subscriptions_for_representative,
    RepresentativeCreationError,
    DatasetRepresentativeService,
)
from vitrina.datasets.models import (
    Dataset,
    DatasetStructure,
    DatasetGroup,
    DatasetAttribution,
    DatasetRelation,
    Relation,
    DatasetFile,
    Contact,
    DatasetExcludedGroups,
    DCATResourceSubclass,
)
from vitrina.classifiers.models import (
    Category,
    Frequency,
    AreaOfManagement,
)
from vitrina.identifiers.models import Agency, Identifier
from vitrina.helpers import (
    email,
    get_selected_value,
    Filter,
    DateFilter,
    get_stats_filter_options_based_on_model,
    get_current_domain,
    build_page_title_context,
)
from vitrina.messages.models import Subscription
from vitrina.orgs.helpers import is_org_dataset_list
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action, hash_api_key
from vitrina.plans.models import Plan, PlanDataset
from vitrina.projects.models import Project
from vitrina.requests.models import RequestObject, RequestAssignment, Request
from vitrina.resources.models import DatasetDistribution, Format
from vitrina.settings import ELASTIC_FACET_SIZE, SPINTA_SERVER_URL
from vitrina.statistics.helpers import get_start_date_based_on_frequency
from vitrina.statistics.models import DatasetStats, ModelDownloadStats
from vitrina.statistics.views import StatsMixin
from vitrina.structure.models import Metadata, Property, Model
from vitrina.structure.services import (
    create_structure_objects,
    get_model_name,
    get_allowed_visibilities,
)
from vitrina.projects.services import get_projects, get_projects_linkable_to_dataset, can_manage_datasets


class DatasetListView(PermissionRequiredMixin, PlanMixin, FacetedSearchView):
    template_name = "vitrina/datasets/list.html"
    facet_fields = [
        "status",
        "organization",
        "publisher",
        "jurisdiction",
        "category",
        "parent_category",
        "groups",
        "frequency",
        "tags",
        "formats",
        "published",
        "level",
        "type",
        "access_rights",
        "subclass",
    ]
    form_class = DatasetSearchForm
    max_num_facets = 20
    paginate_by = 20
    date_facet_fields = [
        {
            "field": "published",
            "start_date": date(2019, 1, 1),
            "end_date": date.today(),
            "gap_by": "month",
        },
    ]

    @property
    def page_title(self) -> str:
        return _("Duomenų ištekliai")

    def has_permission(self):
        if is_org_dataset_list(self.request):
            self.organization = get_object_or_404(Organization, pk=self.kwargs["pk"])
            if self.organization.is_public:
                return True
            else:
                return has_perm(self.request.user, Action.VIEW, self.organization)
        return True

    def get(self, request, **kwargs):
        legacy_org_redirect = self.request.GET.get("organization_id")
        if legacy_org_redirect:
            new_query_dict = {"selected_facets": "organization_exact:{}".format(legacy_org_redirect)}
            return HttpResponsePermanentRedirect("?" + urlencode(new_query_dict, True))
        return super().get(request)

    def get_queryset(self):
        queryset: SearchQuerySet = get_datasets_for_user(self.request, super().get_queryset())
        sorting = self.request.GET.get("sort", None)
        queryset = queryset.models(Dataset)
        if self.request.GET.get("q") and not sorting:
            sorting = "sort-by-relevance"

        options = {"size": ELASTIC_FACET_SIZE}
        for field in self.facet_fields:
            queryset = queryset.facet(field, **options)

        if is_manager_dataset_list(self.request):
            # Get dataset IDs where user is a direct representative
            dataset_ids = [
                rep.object_id
                for rep in self.request.user.representative_set.filter(role__in=Representative.MANAGER_ROLES)
            ]

            # Get organization IDs where user is a representative
            org_ids = [
                rep.object_id
                for rep in self.request.user.representative_set.filter(role__in=Representative.MANAGER_ROLES)
            ]

            query = SQ()
            for dataset_id in dataset_ids:
                query |= SQ(id=dataset_id)
            for org_id in org_ids:
                query |= SQ(organization=org_id)

            queryset = queryset.filter(query)

        if is_org_dataset_list(self.request):
            queryset = queryset.filter(organization=self.organization.pk)

        if not sorting or sorting == "sort-by-date-newest":
            queryset = queryset.order_by("-published_created_s")
        elif sorting == "sort-by-date-oldest":
            queryset = queryset.order_by("published_created_s")
        elif sorting == "sort-by-title":
            if self.request.LANGUAGE_CODE == "lt":
                queryset = queryset.order_by("lt_title_s", "-type_order")
            else:
                queryset = queryset.order_by("en_title_s", "-type_order")
        elif sorting == "sort-by-relevance":
            queryset = queryset.order_by("-type_order")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facet_fields = context.get("facets").get("fields")
        date_facets = context.get("facets").get("dates")
        form = context.get("form")
        sorting = self.request.GET.get("sort", None)
        filter_args = (self.request, form, facet_fields)
        extra_context = {
            "filters": [
                Filter(
                    *filter_args,
                    "status",
                    _("Duomenų ištekliaus būsena"),
                    choices=Dataset.FILTER_STATUSES,
                    multiple=True,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    "level",
                    _("Brandos lygis"),
                    multiple=False,
                    is_int=True,
                ),
                Filter(
                    *filter_args,
                    "organization",
                    _("Organizacija"),
                    Organization,
                    multiple=True,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    "publisher",
                    _("Duomenų atvėrimo paslaugų teikėjas"),
                    Organization,
                    multiple=True,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    "jurisdiction",
                    _("Valdymo sritis"),
                    AreaOfManagement,
                    multiple=True,
                    is_int=False,
                    use_str=True,
                ),
                Filter(
                    *filter_args,
                    "category",
                    _("Kategorija"),
                    Category,
                    multiple=True,
                    is_int=False,
                    parent="parent_category",
                    use_str=True,
                ),
                Filter(
                    *filter_args,
                    "groups",
                    _("Grupė"),
                    DatasetGroup,
                    multiple=True,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    "access_rights",
                    _("Prieigos teisės"),
                    choices=Dataset.FILTER_ACCESS_RIGHTS,
                    is_int=False,
                    expand=False,
                ),
                Filter(
                    *filter_args,
                    "tags",
                    _("Žymė"),
                    Dataset,
                    multiple=True,
                    is_int=False,
                    display_method="get_tag_title",
                ),
                Filter(
                    *filter_args,
                    "frequency",
                    _("Atnaujinama"),
                    Frequency,
                    multiple=False,
                    is_int=True,
                    use_str=True,
                ),
                Filter(
                    *filter_args,
                    "subclass",
                    _("Duomenų ištekliaus rūšis"),
                    choices=Dataset.FILTER_SUBCLASSES,
                    is_int=False,
                    stats=False,
                ),
                Filter(
                    *filter_args,
                    "formats",
                    _("Formatas"),
                    Format,
                    multiple=True,
                    is_int=False,
                ),
                DateFilter(
                    self.request,
                    form,
                    date_facets,
                    "published",
                    _("Įkėlimo data"),
                    multiple=False,
                    is_int=False,
                ),
            ],
            "group_facet": update_facet_data(self.request, facet_fields, "groups", DatasetGroup),
            "selected_groups": get_selected_value(form, "groups", True, False),
            "q": form.cleaned_data.get("q", ""),
        }
        search_query_dict = dict(self.request.GET.copy())
        if "query" in search_query_dict:
            search_query_dict.pop("query")
        context["search_query"] = search_query_dict

        sort_query_dict = dict(self.request.GET.copy())
        if "sort" in sort_query_dict:
            sort_query_dict.pop("sort")
        sort_query = urlencode(sort_query_dict, True)

        if is_org_dataset_list(self.request):
            url = reverse("organization-datasets", args=[self.organization.pk])
            extra_context["organization"] = self.organization
            extra_context["can_view_members"] = has_perm(
                self.request.user, Action.VIEW, Representative, self.organization
            )
            extra_context["can_view_contacts"] = has_perm(
                self.request.user,
                Action.VIEW,
                Contact,
                self.organization,
            )
            extra_context["can_create_dataset"] = has_perm(
                self.request.user,
                Action.CREATE,
                Dataset,
                self.organization,
            )
            extra_context["can_view_agents"] = has_perm(self.request.user, Action.VIEW, Agent, self.organization)
            extra_context["can_view_keys"] = has_perm(
                self.request.user, Action.MANAGE_KEYS, Organization, self.organization
            )
            context["organization_id"] = self.organization.pk
            if not form.selected_facets:
                form.selected_facets.append("organization_exact:{0}".format(self.organization.id))
        else:
            url = reverse("dataset-list")

        context["search_url"] = url
        context["page_title"] = self.page_title
        context["sort_options"] = [
            {
                "title": _("Naujausi"),
                "url": f"{url}?{sort_query}&sort=sort-by-date-newest"
                if sort_query
                else f"{url}?sort=sort-by-date-newest",
                "icon": "fas fa-sort-amount-down-alt",
                "key": "sort-by-date-newest",
            },
            {
                "title": _("Seniausi"),
                "url": f"{url}?{sort_query}&sort=sort-by-date-oldest"
                if sort_query
                else f"{url}?sort=sort-by-date-oldest",
                "icon": "fas fa-sort-amount-up-alt",
                "key": "sort-by-date-oldest",
            },
            {
                "title": _("Pagal pavadinimą"),
                "url": f"{url}?{sort_query}&sort=sort-by-title" if sort_query else f"{url}?sort=sort-by-title",
                "icon": "fas fa-sort-amount-down-alt",
                "key": "sort-by-title",
            },
            {
                "title": _("Tinkamiausi"),
                "url": f"{url}?{sort_query}&sort=sort-by-relevance" if sort_query else f"{url}?sort=sort-by-relevance",
                "icon": "fas fa-sort-amount-down-alt",
                "key": "sort-by-relevance",
            },
        ]

        context.update(extra_context)

        if self.request.GET.get("q") and not sorting:
            sorting = "sort-by-relevance"
        context["sort"] = sorting
        return context

    def get_plan_url(self) -> str | None:
        if is_org_dataset_list(self.request):
            return reverse("organization-plans", args=[self.organization.pk])
        if is_child_resources_list(self.request):
            return reverse("dataset-plans", args=[self.dataset.pk])
        return None


class DatasetRedirectView(View):
    def get(self, request, **kwargs):
        slug = kwargs.get("slug")
        dataset = get_object_or_404(Dataset, slug=slug)
        return HttpResponsePermanentRedirect(reverse("dataset-detail", kwargs={"pk": dataset.pk}))


class DatasetDetailView(
    DatasetBreadcrumbsMixin,
    LanguageChoiceMixin,
    HistoryMixin,
    DatasetStructureMixin,
    PermissionRequiredMixin,
    PlanMixin,
    DetailView,
):
    model = Dataset
    template_name = "vitrina/datasets/detail.html"
    context_object_name = "dataset"
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"

    def has_permission(self):
        dataset = get_object_or_404(Dataset, id=self.kwargs["pk"])
        return has_perm(self.request.user, Action.VIEW, dataset)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not request.GET.get("resource_version"):
            if metadata_version := _Version.objects.filter(dataset=self.object).order_by("version").last():
                url = (
                    f"{reverse('dataset-detail', kwargs={'pk': self.object.pk})}?resource_version={metadata_version.pk}"
                )
                return redirect(url)

        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Dataset]:
        return (
            super()
            .get_queryset()
            .select_related("subclass", "information_system_type")
            .prefetch_related("documentation", "applicable_legislation")
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        dataset = context_data.get("dataset")
        context_data["versions"] = _Version.objects.filter(dataset=dataset).order_by("version")
        metadata_version = None
        if metadata_version_id := self.request.GET.get("resource_version"):
            metadata_version = _Version.objects.filter(id=metadata_version_id).first()
            context_data["selected_version"] = metadata_version
        organization = dataset.organization

        related_datasets = dataset.related_datasets.all()
        paginator = Paginator(related_datasets, 10)  # Show 10 relations per page
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        subclass = dataset.subclass
        extra_context_data = {
            "tags": dataset.get_tag_object_list(),
            "subscription": [],
            "status": dataset.get_status_display(),
            "public_status": dataset.is_public,
            # TODO: harvested functionality needs to be implemented
            "harvested": "",
            "can_add_resource": has_perm(
                self.request.user,
                Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.CREATE,
                Dataset,
                organization,
            ),
            "can_update_dataset": has_perm(
                self.request.user,
                Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.UPDATE,
                dataset,
            ),
            "can_view_members": has_perm(self.request.user, Action.VIEW, Representative, dataset),
            "org_logo": organization.image if organization else None,
            "attributions": dataset.datasetattribution_set.order_by("attribution"),
            "data_maturity": dataset.metadata_set.average_level(),
            "json_ld": self.get_json_ld_from_dataset(dataset),
            "page_obj": page_obj,
            "child_resources_url": reverse("dataset-child-resources", kwargs={"pk": dataset.pk}),
            "licences": set([dist.licence for dist in dataset.datasetdistribution_set.filter(licence__isnull=False)]),
        }

        if metadata_version and metadata_version.status == VersionStatus.DRAFT:
            extra_context_data["resources"] = dataset.datasetdistribution_set.filter(
                Q(metadata_version=metadata_version) | Q(metadata_version__isnull=True) | Q(format__extension="UAPI")
            ).order_by("-period_start")
        else:
            extra_context_data["resources"] = dataset.datasetdistribution_set.filter(
                Q(metadata_version=metadata_version) | Q(format__extension="UAPI")
            ).order_by("-period_start")

        part_of = dataset.part_of.order_by("relation")
        part_of = itertools.groupby(part_of, lambda x: x.relation)
        extra_context_data["part_of"] = [(relation, list(values)) for relation, values in part_of]

        dynamic_resource = DynamicResourceService(dataset, metadata_version)
        generated_resources = dynamic_resource.generate_resources()
        extra_context_data["dynamic_resources"] = generated_resources

        related_datasets = itertools.groupby(related_datasets, lambda x: x.relation)
        extra_context_data["related_datasets"] = [(relation, list(values)) for relation, values in related_datasets]

        context_data.update(extra_context_data)
        context_data["page_title"] = build_page_title_context(
            dataset=dataset,
            language_code=self.request.LANGUAGE_CODE,
        )
        return context_data

    def get_json_ld_from_dataset(self, dataset):
        data_url = self.get_data_url()
        if not data_url:
            return dataset.get_json_ld(None)

        model_name = data_url.rstrip("/").split("/")[-1]
        model_exists = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=dataset)
            .exists()
        )

        if not model_exists:
            return dataset.get_json_ld(None)

        model = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=dataset)
            .first()
        )

        return dataset.get_json_ld(f"{SPINTA_SERVER_URL}/{model}")


class DatasetDeleteView(PermissionRequiredMixin, DeleteView):
    model = Dataset
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("dataset-list")

    def has_permission(self):
        dataset = get_object_or_404(Dataset, id=self.kwargs["pk"])
        return has_perm(self.request.user, Action.DELETE, dataset)


class DatasetRDFDownloadView(PermissionRequiredMixin, View):
    def has_permission(self):
        dataset = get_object_or_404(Dataset, id=self.kwargs["pk"])
        return has_perm(self.request.user, Action.VIEW, dataset)

    def get(self, request, **kwargs):
        dataset = Dataset.objects.filter(pk=kwargs.get("pk"))
        return render(
            request,
            "vitrina/api/edp/dcat_ap_rdf.html",
            {
                "datasets": get_datasets_for_rdf(dataset),
            },
            content_type="application/rdf+xml",
        )


class OpenDataPortalDatasetDetailView(View):
    def get(self, request):
        dataset = Dataset.objects.filter(translations__title__icontains="Open data catalog").first()
        return HttpResponseRedirect(
            reverse(
                "dataset-detail",
                kwargs={
                    "pk": dataset.pk,
                },
            )
        )


class DatasetDistributionPreviewView(ListView):
    def get(self, request, dataset_id, distribution_id):
        distribution = get_object_or_404(DatasetDistribution, dataset__pk=dataset_id, pk=distribution_id)
        data = []
        if distribution.is_previewable():
            if "xlsx" in distribution.file.path:
                read_data = pd.ExcelFile(distribution.file.path)
                read_data = {sheet_name: read_data.parse(sheet_name) for sheet_name in read_data.sheet_names}
                if len(read_data.keys()) > 1:
                    data = [["Only one sheet is allowed in file"]]
                else:
                    read_data = read_data[next(iter(read_data))]
                    headers = read_data.columns.values
                    first_5_values = read_data.values.tolist()
                    data.append(list(headers))
                    data.extend(first_5_values[:5])

            elif "csv" in distribution.file.path:
                read_data = None

                try:
                    read_data = pd.read_csv(distribution.file.path, delimiter=";")
                except ValueError:
                    try:
                        read_data = pd.read_csv(distribution.file.path, encoding="cp1257", delimiter=";")
                    except ValueError:
                        pass
                if read_data is not None:
                    headers = read_data.columns.values
                    first_5_values = read_data.values.tolist()
                    data.append(list(headers))
                    data.extend(first_5_values[:5])
                else:
                    data = [[_("Nepavyko nuskaityti failo")]]
            else:
                data = [["Only xlsx or csv files are available"]]
        return JsonResponse({"data": data})


class DatasetCreateView(
    DatasetBreadcrumbsMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    TranslatableCreateView,
    LanguageChoiceMixin,
    PlanMixin,
):
    model = Dataset
    template_name = "vitrina/datasets/resource_form.html"
    context_object_name = "dataset"
    plan_url_name = "organization-plans"

    def get_initial(self):
        initial = super().get_initial()
        if subclass_uuid := self.kwargs.get("subclass_uuid"):
            initial["subclass_uuid"] = subclass_uuid
        return initial

    @property
    def organization_id(self) -> int | str | None:
        return self.kwargs.get("pk")

    @cached_property
    def organization(self) -> Organization:
        return get_object_or_404(Organization, id=self.organization_id)

    @property
    def parent_id(self) -> str | None:
        return self.kwargs.get("parent_id")

    def has_permission(self):
        next_url = self.request.GET.get("next")
        if next_url:
            match = resolve(next_url)
            if match.url_name == "request-datasets":
                if request_id := match.kwargs.get("pk"):
                    request_obj = get_object_or_404(Request, pk=request_id)
                    return has_perm(self.request.user, Action.ASSIGN, request_obj)

        return has_perm(self.request.user, Action.CREATE, Dataset, self.organization)

    def get_breadcrumbs(self) -> list[Crumb]:
        """Generate hierarchical breadcrumbs for the dataset"""

        ACCUSATIVE_FORMS = {
            "dataset": _("Pridėti duomenų rinkinį"),
            "service": _("Pridėti duomenų publikavimo paslaugą"),
            "series": _("Pridėti duomenų rinkinio seriją"),
            "information_system": _("Pridėti informacinę sistemą"),
            "catalog": _("Pridėti metaduomenų katalogą"),
        }
        subclass = get_object_or_404(DCATResourceSubclass, pk=self.kwargs.get("subclass_uuid"))
        if parent_id := self.kwargs.get("parent_id"):
            parent_dataset = get_object_or_404(Dataset, pk=parent_id)
            crumbs = self.dataset_hierarchy(parent_dataset, include_home=True)
            crumbs.append(
                Crumb(
                    title=_("Pridėti vaikinį duomenų išteklių"),
                    url=reverse("child-resource-subclass-add", args=[self.organization.pk, parent_id]),
                )
            )
            crumbs.append(Crumb(title=ACCUSATIVE_FORMS.get(subclass.name, subclass.name), url=None, is_current=True))
            return crumbs

        return self.breadcrumbs_organization(self.organization) + [
            Crumb(title=_("Duomenų ištekliai"), url=reverse("dataset-list")),
            Crumb(
                title=_("Pridėti duomenų išteklių"), url=reverse("resource-subclass-add", args=[self.organization.pk])
            ),
            Crumb(title=ACCUSATIVE_FORMS.get(subclass.name, subclass.name), url=None, is_current=True),
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subclass_uuid = self.kwargs.get("subclass_uuid")
        subclass = DCATResourceSubclass.objects.get(pk=subclass_uuid)
        context.update(
            {
                "can_view_members": has_perm(
                    self.request.user,
                    Action.VIEW,
                    Representative,
                    self.object,
                ),
                "can_view_contacts": has_perm(
                    self.request.user,
                    Action.VIEW,
                    Contact,
                    self.object,
                ),
                "organization": self.organization,
                "organization_id": self.organization.pk,
                "current_title": _("Pridėti vaikinių duomenų išteklių")
                if self.parent_id
                else _("Pridėti duomenų išteklių"),
                "form_title": subclass.translated_title,
                "information_title": subclass.translated_title,
                "information_description": subclass.translated_description,
                "button": _("Sukurti"),
                "current_step": 2,
                "current_percentage": 100,
                "selected_subclass_uuid": str(subclass_uuid),
                "service_subclass": str(DCATResourceSubclass.objects.get(name=DCATResourceSubclass.SERVICE).pk),
            }
        )
        return context

    def get_form_class(self):
        subclass = get_object_or_404(DCATResourceSubclass, pk=self.kwargs.get("subclass_uuid"))
        if subclass.name == DCATResourceSubclass.SERVICE:
            return ServiceResourceForm
        if subclass.name == DCATResourceSubclass.INFORMATION_SYSTEM:
            return InformationSystemResourceForm
        if subclass.name == DCATResourceSubclass.DATASET:
            return DatasetResourceForm
        if subclass.name == DCATResourceSubclass.CATALOG:
            return CatalogResourceForm

        return ResourceForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["organization"] = get_object_or_404(Organization, id=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        lang = self.request.GET.get("language", get_language())
        self.object.set_current_language(lang)
        self.object.organization_id = self.kwargs.get("pk")
        subclass = DCATResourceSubclass.objects.get(pk=self.kwargs.get("subclass_uuid"))
        self.object.subclass = subclass

        parent: Dataset | None
        if parent := form.cleaned_data.pop("parent", None):
            parent.add_child(instance=self.object)
        else:
            Dataset.add_root(instance=self.object)

        if subclass.name == DCATResourceSubclass.SERVICE:
            self.object.service = True
        else:
            self.object.endpoint_url = None
            self.object.endpoint_type = None
            self.object.endpoint_description = None
            self.object.endpoint_description_type = None
            self.object.service = False
        if subclass.name == DCATResourceSubclass.SERIES:
            self.object.series = True
        else:
            self.object.series = False

        if self.object.is_public:
            self.object.published = timezone.now()
            if self.object.service and self.object.endpoint_url:
                self.object.status = Dataset.HAS_DATA
            else:
                self.object.status = Dataset.INVENTORED
        if subclass.name == DCATResourceSubclass.INFORMATION_SYSTEM and (
            identifier := form.cleaned_data.get("identifier")
        ):
            agency = get_object_or_404(Agency, code="risr")
            Identifier.objects.create(
                resource=self.object,
                notation=identifier,
                scheme_agency=agency,
                identifier_type=Identifier.IdentifierType.OTHER,
            )

        self.object.save()
        tags = form.cleaned_data.get("tags")
        self.object.tags.set(tags)
        self.object.save()
        if not form.cleaned_data.get("creator"):
            role = Representative.OPEN_DATA_MANAGER
            if self.organization:
                user_rep = self.request.user.representative_set.filter(
                    content_type=ContentType.objects.get_for_model(self.organization),
                    object_id=self.organization.pk,
                ).first()
                role = user_rep.role if user_rep else Representative.OPEN_DATA_MANAGER
            Representative.objects.create(
                content_type=ContentType.objects.get_for_model(self.object),
                object_id=self.object.pk,
                user=self.request.user,
                email=self.request.user.email,
                role=role,
            )

        for file in form.cleaned_data.get("files", []):
            DatasetFile.objects.get_or_create(
                dataset=self.object,
                file=file,
            )
        dataset_name = form.cleaned_data.get("name", "") or generate_unique_dataset_name(
            self.object.organization, self.object
        )
        draft_metadata_version = _Version.objects.create(
            dataset=self.object,
            version=1,
            status=VersionStatus.DRAFT,
        )
        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=self.object,
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.pk,
            name=dataset_name,
            title=self.object.title,
            description=self.object.description,
            prepare_ast={},
            version=1,
            metadata_version=draft_metadata_version,
        )
        if self.object.organization:
            org_id = self.object.organization.id
            sub_ct = get_content_type_for_model(Organization)

            subs = Subscription.objects.filter(
                (Q(object_id=org_id) | Q(object_id=None)),
                sub_type=Subscription.ORGANIZATION,
                content_type=sub_ct,
                dataset_update_sub=True,
            )

            sub_email_list = []
            for sub in subs:
                Task.objects.create(
                    title=f"Duomenų rinkinys organizacijai: {self.object.organization}",
                    description=f"Sukurtas naujas duomenų rinkinys organizacijai: {self.object.organization}.",
                    content_type=ContentType.objects.get_for_model(self.object),
                    object_id=self.object.pk,
                    organization=self.object.organization,
                    status=Task.CREATED,
                    type=Task.DATASET,
                    user=sub.user,
                )
                if sub.user.email and sub.email_subscribed:
                    if sub.user.organization:
                        orgs = [sub.user.organization] + list(sub.user.organization.get_descendants())
                        sub_email_list = [org.email for org in orgs]
                    sub_email_list.append(sub.user.email)
                dataset_url = "%s%s" % (
                    get_current_domain(self.request),
                    reverse("dataset-detail", args=[self.object.id]),
                )
                email(
                    sub_email_list,
                    "dataset-created-sub",
                    "vitrina/datasets/emails/sub/created.md",
                    {"dataset": self.object.title, "link": dataset_url},
                )

        next_url = self.request.GET.get("next")
        if next_url:
            match = resolve(next_url)
            if match.url_name == "request-datasets":
                if request_id := match.kwargs.get("pk"):
                    RequestObject.objects.create(
                        request_id=request_id,
                        object_id=self.object.pk,
                        content_type=ContentType.objects.get_for_model(self.object),
                    )

        creator = form.cleaned_data.get("creator")
        if creator:
            if self.object.organization:
                Representative.objects.create(
                    content_type=ContentType.objects.get_for_model(self.object),
                    object_id=self.object.pk,
                    organization=self.object.organization,
                    role=Representative.OPEN_DATA_MANAGER,
                )

                self.object.publisher = self.object.organization if self.object.organization != creator else None
            self.object.organization = creator
            self.object.save()

        publisher = form.cleaned_data.get("publisher")
        if publisher:
            self.object.publisher = publisher
            rep = Representative.objects.create(
                object_id=self.object.pk,
                content_type=ContentType.objects.get_for_model(Dataset),
                organization=publisher,
                role=Representative.OPEN_DATA_MANAGER,
            )
            rep.save()
            self.object.save()

        if applicable_legislation_urls := form.cleaned_data.get("applicable_legislation"):
            self.object.update_applicable_legislation(applicable_legislation_urls)

        if documentation_urls := form.cleaned_data.get("documentation"):
            self.object.update_documentation(documentation_urls)

        if service_type := form.cleaned_data.get("service_type"):
            self.object.service_type.set(service_type)

        messages.success(self.request, _("Duomenų išteklius sukurtas sėkmingai"))

        return HttpResponseRedirect(self.get_success_url())


class ResourceSubclassCreateView(
    DatasetBreadcrumbsMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Dataset
    template_name = "vitrina/datasets/resource_subclass_form.html"
    context_object_name = "dataset"
    form_class = ResourceSubclassForm

    def has_permission(self):
        next_url = self.request.GET.get("next")
        if next_url:
            match = resolve(next_url)
            if match.url_name == "request-datasets":
                if request_id := match.kwargs.get("pk"):
                    request_obj = get_object_or_404(Request, pk=request_id)
                    return has_perm(self.request.user, Action.ASSIGN, request_obj)
        organization = get_object_or_404(Organization, id=self.kwargs.get("pk"))
        if parent_id := self.kwargs.get("parent_id"):
            parent_dataset = get_object_or_404(Dataset, pk=parent_id)
            return has_perm(self.request.user, Action.CREATE, Dataset, parent_dataset)
        return has_perm(self.request.user, Action.CREATE, Dataset, organization)

    def get_breadcrumbs(self) -> list[Crumb]:
        if parent_id := self.kwargs.get("parent_id"):
            parent_dataset = get_object_or_404(Dataset, pk=parent_id)
            crumbs = self.dataset_hierarchy(parent_dataset, include_home=True, make_current=False)
            crumbs.append(Crumb(title=_("Pridėti vaikinį duomenų išteklių"), url=None, is_current=True))
            return crumbs

        org = get_object_or_404(Organization, id=self.kwargs["pk"])
        return self.breadcrumbs_organization(org) + [
            Crumb(title=_("Duomenų ištekliai"), url=reverse("dataset-list")),
            Crumb(title=_("Pridėti duomenų išteklių"), url=None, is_current=True),
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        organization = get_object_or_404(Organization, id=self.kwargs.get("pk"))

        context.update(
            {
                "organization": organization,
                "organization_id": organization.pk,
                "information_title": _("Pasirinkite duomenų ištekliaus rūšį"),
                "current_title": _("Pridėti duomenų išteklių"),
                "form_title": _("Duomenų ištekliaus rūšis"),
                "form_description": _("Pasirinkite duomenų ištekliaus rūšį"),
                "use_custom_radio": True,
                "can_view_members": has_perm(
                    self.request.user,
                    Action.VIEW,
                    Representative,
                    self.object,
                ),
                "can_view_contacts": has_perm(
                    self.request.user,
                    Action.VIEW,
                    Contact,
                    self.object,
                ),
                "current_step": 1,
                "current_percentage": 50,
            }
        )

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["organization"] = get_object_or_404(Organization, id=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        pk = self.kwargs.get("pk")
        subclass = form.cleaned_data.get("subclass")
        if parent_id := self.kwargs.get("parent_id"):
            return redirect(
                reverse("child-dataset-add", kwargs={"pk": pk, "parent_id": parent_id, "subclass_uuid": subclass.uuid})
            )
        return redirect(reverse("dataset-add", kwargs={"pk": pk, "subclass_uuid": subclass.uuid}))


class DatasetUpdateView(
    DatasetBreadcrumbsMixin,
    DatasetStructureMixin,
    PlanMixin,
    HistoryView,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    TranslatableUpdateView,
    ViewUrlMixin,
):
    model = Dataset
    template_name = "vitrina/datasets/resource_form.html"
    view_url_name = "dataset:edit"
    context_object_name = "dataset"

    object: Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"
    tabs_template_name = "vitrina/datasets/tabs.html"
    breadcrumb_title = _("Redaguoti")

    def has_permission(self):
        dataset = get_object_or_404(Dataset, id=self.kwargs["pk"])
        subclass = self.dataset.subclass
        return has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.UPDATE,
            dataset,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subclass_uuid = self.object.subclass.uuid
        switch_language(self.object, get_language())
        context["page_title"] = build_page_title_context(
            dataset=self.object,
            language_code=self.request.LANGUAGE_CODE,
        )
        context.update(
            {
                "current_title": _("Duomenų ištekliaus redagavimas"),
                "form_title": self.object.subclass.translated_title,
                "information_title": self.object.subclass.translated_title,
                "information_description": self.object.subclass.translated_description,
                "selected_subclass_uuid": str(subclass_uuid),
                "service_subclass": str(DCATResourceSubclass.objects.get(name=DCATResourceSubclass.SERVICE).pk),
                "button": _("Redaguoti"),
                "request_user": (self.request.user if self.request.user.is_authenticated else None),
                "can_view_members": has_perm(
                    self.request.user,
                    Action.VIEW,
                    Representative,
                    self.object,
                ),
            }
        )
        return context

    def get_form_class(self):
        subclass = self.get_object().subclass

        if subclass.name == DCATResourceSubclass.SERVICE:
            return ServiceResourceForm
        if subclass.name == DCATResourceSubclass.INFORMATION_SYSTEM:
            return InformationSystemResourceForm
        if subclass.name == DCATResourceSubclass.DATASET:
            return DatasetResourceForm
        if subclass.name == DCATResourceSubclass.CATALOG:
            return CatalogResourceForm

        return ResourceForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        lang = self.request.GET.get("language", get_language())
        obj.set_current_language(lang)
        return obj

    def form_valid(self, form):
        self.object: Dataset = form.save(commit=False)
        tags = form.cleaned_data["tags"]
        self.object.tags.set(tags)

        if ("endpoint_url" in form.changed_data) or (self.object.is_public and not self.object.published):
            if self.object.is_public and not self.object.published:
                self.object.published = timezone.now()

            if self.object.datasetdistribution_set.exists() or (self.object.service and self.object.endpoint_url):
                self.object.status = Dataset.HAS_DATA
            elif self.object.plandataset_set.exists():
                self.object.status = Dataset.PLANNED
            else:
                self.object.status = Dataset.INVENTORED

        elif not self.object.is_public and self.object.published:
            self.object.published = None
            self.object.status = Dataset.UNASSIGNED

        if self.object.subclass.name == DCATResourceSubclass.INFORMATION_SYSTEM and (
            identifier := form.cleaned_data.get("identifier")
        ):
            agency = get_object_or_404(Agency, code="risr")
            Identifier.objects.update_or_create(
                resource=self.object,
                scheme_agency=agency,
                defaults={
                    "notation": identifier,
                    "identifier_type": Identifier.IdentifierType.OTHER,
                    "resource": self.object,
                    "scheme_agency": agency,
                },
            )
        if "applicable_legislation" in form.changed_data:
            self.object.update_applicable_legislation(form.cleaned_data["applicable_legislation"])

        if "documentation" in form.changed_data:
            self.object.update_documentation(form.cleaned_data["documentation"])

        if "service_type" in form.changed_data:
            self.object.service_type.set(form.cleaned_data["service_type"])

        self.object.save()

        if "files" in form.changed_data:
            for file in form.cleaned_data.get("files", []):
                DatasetFile.objects.get_or_create(
                    dataset=self.object,
                    file=file,
                )

        if metadata := self.object.metadata.first():
            metadata.title = self.object.title
            metadata.description = self.object.description
            metadata.save()
        else:
            metadata = Metadata.objects.create(
                uuid=str(uuid.uuid4()),
                dataset=self.object,
                content_type=ContentType.objects.get_for_model(self.object),
                object_id=self.object.pk,
                title=self.object.title,
                description=self.object.description,
                prepare_ast={},
                version=1,
            )
        dataset_name = form.cleaned_data.get("name", "") or generate_unique_dataset_name(
            self.object.organization, self.object
        )
        if not metadata.name or metadata.name != dataset_name:
            metadata.name = dataset_name
            metadata.draft = True
            metadata.save()

            # Update model names
            for model in self.object.model_set.all():
                if model_meta := model.metadata.first():
                    model_meta.name = get_model_name(self.object, model.name)
                    model_meta.save()

        queries = []

        org_subs = Subscription.objects.none()
        if self.object.organization:
            org_subs = Subscription.objects.filter(
                Q(object_id=self.object.organization.pk) | Q(object_id=None),
                sub_type=Subscription.ORGANIZATION,
                content_type=get_content_type_for_model(Organization),
                dataset_update_sub=True,
            )

        subs = Subscription.objects.filter(
            sub_type=Subscription.DATASET,
            content_type=get_content_type_for_model(Dataset),
            object_id=self.object.id,
            dataset_update_sub=True,
        )

        if org_subs:
            subs = org_subs | subs

        for sub in subs:
            queries.append(
                Subscription.objects.filter(
                    Q(object_id=self.object.organization.pk) | Q(object_id=None),
                    sub_type=Subscription.ORGANIZATION,
                    content_type=get_content_type_for_model(Organization),
                    dataset_update_sub=True,
                )
            )
        queries.append(
            Subscription.objects.filter(
                sub_type=Subscription.DATASET,
                content_type=get_content_type_for_model(Dataset),
                object_id=self.object.id,
                dataset_update_sub=True,
            )
        )
        sub_list = [item for query in queries for item in query]
        sorted_list = sorted(sub_list, key=lambda x: x.sub_type != Subscription.ORGANIZATION)

        sub_email_list = []
        for sub in sorted_list:
            Task.objects.create(
                title=f"Duomenų rinkinys: {self.object}",
                description=f"Atnaujintas duomenų rinkinys: {self.object}",
                content_type=get_content_type_for_model(Dataset),
                object_id=self.object.pk,
                organization=self.object.organization,
                status=Task.CREATED,
                type=Task.DATASET,
                user=sub.user,
            )
            if sub.user.email and sub.email_subscribed:
                if sub.user.email not in sub_email_list:
                    sub_email_list.append(sub.user.email)
        if sub_email_list:
            email(
                sub_email_list,
                "dataset-updated",
                "vitrina/datasets/emails/sub/updated.md",
                {
                    "title": self.object,
                    "link": "%s%s"
                    % (
                        get_current_domain(self.request),
                        self.object.get_absolute_url(),
                    ),
                },
            )

        if "creator" in form.changed_data and self.request.user.organization:
            creator = form.cleaned_data.get("creator")
            if creator:
                if self.request.user.organization.publisher:
                    Representative.objects.create(
                        content_type=ContentType.objects.get_for_model(self.object),
                        object_id=self.object.pk,
                        organization=self.request.user.organization,
                        role=Representative.OPEN_DATA_MANAGER,
                    )

                    self.object.publisher = self.request.user.organization
                self.object.organization = creator

                if creator == self.request.user.organization and self.request.user.organization.publisher:
                    self.object.publisher = None
                    Representative.objects.filter(
                        object_id=self.object.pk,
                        content_type=ContentType.objects.get_for_model(Dataset),
                        role=Representative.OPEN_DATA_MANAGER,
                        organization__isnull=False,
                    ).delete()

            self.object.save()

        if "managed_by_publisher" in form.changed_data and self.request.user.organization:
            managed_by_publisher = form.cleaned_data.get("managed_by_publisher")
            if managed_by_publisher and self.request.user.organization.publisher:
                self.object.publisher = self.request.user.organization
                rep = Representative.objects.create(
                    object_id=self.object.pk,
                    content_type=ContentType.objects.get_for_model(Dataset),
                    organization=self.request.user.organization,
                    role=Representative.OPEN_DATA_MANAGER,
                )
                rep.save()
            else:
                self.object.publisher = None
                Representative.objects.filter(
                    object_id=self.object.pk,
                    content_type=ContentType.objects.get_for_model(Dataset),
                    role=Representative.OPEN_DATA_MANAGER,
                    organization__isnull=False,
                ).delete()
            self.object.save()

        if "publisher" in form.changed_data:
            publisher = form.cleaned_data.get("publisher")
            if publisher:
                self.object.publisher = publisher
                rep = Representative.objects.create(
                    object_id=self.object.pk,
                    content_type=ContentType.objects.get_for_model(Dataset),
                    organization=publisher,
                    role=Representative.OPEN_DATA_MANAGER,
                )
                rep.save()
            else:
                self.object.publisher = None
                Representative.objects.filter(
                    object_id=self.object.pk,
                    content_type=ContentType.objects.get_for_model(Dataset),
                    role=Representative.OPEN_DATA_MANAGER,
                    organization__isnull=False,
                ).delete()
            self.object.save()

        self.object.save()

        selected_parent: Dataset | None = form.cleaned_data.get("parent")
        if self.object.get_parent() != selected_parent:
            if not selected_parent:
                self.object.add_self_as_root()
            else:
                self.object.move(selected_parent, "sorted-child")
        return HttpResponseRedirect(self.get_success_url())


class DatasetHistoryView(DatasetStructureMixin, PlanMixin, HistoryView):
    model = Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"
    tabs_template_name = "vitrina/datasets/tabs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.object.pk]): self.object.title,
        }
        return context

    def get_history_objects(self):
        allowed_model_visibilities = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_prop_visibilities = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        visibility_filter_model = Q(metadata__visibility__in=allowed_model_visibilities) | Q(
            metadata__visibility__isnull=True
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_prop_visibilities) | Q(
            metadata__visibility__isnull=True
        )
        model_ids = self.models.filter(visibility_filter_model).values_list("pk", flat=True)
        if self.can_manage_structure:
            property_ids = (
                Property.objects.filter(model__pk__in=model_ids, given=True)
                .filter(visibility_filter_property)
                .values_list("pk", flat=True)
            )
        else:
            property_ids = (
                Property.objects.filter(
                    model__pk__in=model_ids,
                    given=True,
                    metadata__access__gte=Metadata.PUBLIC,
                )
                .filter(visibility_filter_property)
                .values_list("pk", flat=True)
            )

        property_history_objects = Version.objects.get_for_model(Property).filter(object_id__in=list(property_ids))
        model_history_objects = Version.objects.get_for_model(Model).filter(object_id__in=list(model_ids))
        dataset_history_objects = Version.objects.get_for_object(self.object)

        dataset_plan_ids = PlanDataset.objects.filter(dataset=self.object).values_list("plan_id", flat=True)
        plan_history_objects = Version.objects.get_for_model(Plan).filter(object_id__in=list(dataset_plan_ids))
        dataset_distribution_history_objects = self._get_history_objects_for_model(DatasetDistribution)
        attribution_history_objects = self._get_history_objects_for_model(DatasetAttribution)
        relation_history_objects = self._get_history_objects_for_model(DatasetRelation)

        history_objects = (
            property_history_objects
            | model_history_objects
            | dataset_history_objects
            | plan_history_objects
            | dataset_distribution_history_objects
            | attribution_history_objects
            | relation_history_objects
        )
        return history_objects.order_by("-revision__date_created")

    def _get_history_objects_for_model(self, model: TypingType[models.Model]) -> QuerySet[Version]:
        all_versions = Version.objects.get_for_model(model)
        filtered_versions_ids = [
            version.pk for version in all_versions if version.field_dict.get("dataset_id") == self.object.id
        ]
        if model == DatasetRelation:
            filtered_versions_ids += [
                version.pk for version in all_versions if version.field_dict.get("part_of_id") == self.object.id
            ]

        return all_versions.filter(pk__in=filtered_versions_ids)


class DatasetStructureImportView(
    HistoryMixin,
    DatasetStructureMixin,
    PlanMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = DatasetStructure
    form_class = DatasetStructureImportForm
    template_name = "base_form.html"

    detail_url_name = "dataset-detail"
    history_url_name = "dataset-structure-history"
    plan_url_name = "dataset-plans"

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        if not self.has_permission():
            return self.handle_no_permission()
        if not (version_id := kwargs.get("version_id")):
            return super().dispatch(request, *args, **kwargs)
        self.metadata_version = get_object_or_404(_Version, pk=version_id, dataset=self.dataset)
        if not self.metadata_version.is_draft():
            messages.error(request, _("Negalima importuoti struktūros, kai versijos būsena nėra juodraštis."))
            return redirect(self.dataset.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        subclass = self.dataset.subclass
        return has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.CREATE,
            DatasetStructure,
            self.dataset,
        )

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "current_title": _("Struktūros importas"),
            "parent_links": {
                reverse("home"): _("Pradžia"),
                reverse("dataset-list"): _("Duomenų ištekliai"),
                reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
            },
            "parent_title": self.dataset.title,
            "parent_url": self.dataset.get_absolute_url(),
            "tabs": "vitrina/datasets/tabs.html",
            "can_view_members": has_perm(
                self.request.user,
                Action.VIEW,
                Representative,
                self.dataset,
            ),
        }

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.dataset = self.dataset
        self.object.save()
        self.object.dataset.current_structure = self.object
        self.object.dataset.save()
        if self.metadata_version and not self.metadata_version.is_draft():
            form.add_error("file", _("Negalima importuoti struktūros, kai versijos būsena nėra juodraštis."))
            return self.form_invalid(form)

        self.metadata_version = create_structure_objects(self.object, self.metadata_version)
        self.object.dataset.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_plan_object(self):
        return self.dataset

    def get_detail_object(self):
        return self.dataset

    def get_history_object(self):
        return self.dataset

    def get_success_url(self) -> str:
        if self.metadata_version.pk:
            return reverse(
                "dataset-structure",
                kwargs={"pk": self.dataset.pk, "version_id": self.metadata_version.pk},
            )
        return reverse("dataset-structure-no-version", kwargs={"pk": self.dataset.pk})

    def get_history_url(self) -> str:
        if self.metadata_version:
            return reverse(
                "dataset-structure-history",
                kwargs={"pk": self.dataset.pk, "version_id": self.metadata_version.pk},
            )
        else:
            return reverse(
                "dataset-structure-history-no-version",
                kwargs={
                    "pk": self.dataset.pk,
                },
            )


class DatasetMembersView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    HistoryMixin,
    PlanMixin,
    DatasetStructureMixin,
    ListView,
):
    model = Representative
    template_name = "vitrina/datasets/members_list.html"
    context_object_name = "members"
    paginate_by = 20

    # HistoryMixin
    object: Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )

    def get_queryset(self):
        return Representative.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id=self.object.pk,
        ).order_by("role", "first_name", "last_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.object
        subclass = self.object.subclass
        context["has_permission"] = has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_REPRESENTATIVE_CREATE if subclass.is_information_system else Action.CREATE,
            Representative,
            self.object,
        )
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.VIEW,
            Representative,
            self.object,
        )
        context["can_delete_publishers"] = self.request.user.is_superuser
        return context


class CreateMemberView(
    DatasetStructureMixin,
    HistoryMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    PlanMixin,
    CreateView,
):
    model = Representative
    form_class = DatasetMemberCreateForm
    template_name = "base_form.html"

    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"

    def has_permission(self):
        subclass = self.dataset.subclass
        return has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_REPRESENTATIVE_CREATE if subclass.is_information_system else Action.CREATE,
            Representative,
            self.dataset,
        )

    def get_success_url(self):
        return reverse(
            "dataset-members",
            kwargs={
                "pk": self.dataset.pk,
            },
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["object"] = self.dataset
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tabs"] = "vitrina/datasets/tabs.html"
        context["can_view_members"] = self.has_permission()
        context["representative_url"] = reverse("dataset-members", args=[self.dataset.pk])
        context["current_title"] = _("Tvarkytojo pridėjimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def get_detail_object(self):
        return self.dataset

    def get_history_object(self):
        return self.dataset

    def get_plan_object(self) -> Dataset:
        return self.dataset

    def form_valid(self, form):
        service = DatasetRepresentativeService(self.dataset, self.request)

        try:
            self.object, api_key_token = service.create_from_form(form)
        except RepresentativeCreationError as e:
            form.add_error(e.field, e.message)
            return self.form_invalid(form)

        if api_key_token:
            return HttpResponseRedirect(
                reverse(
                    "dataset-representative-api-key",
                    args=[self.dataset.pk, self.object.pk, api_key_token],
                )
            )

        return HttpResponseRedirect(self.get_success_url())


@login_required
def autocomplete_tags(request, tag_model):
    if isinstance(tag_model, QuerySet):
        queryset = tag_model
        tag_model = queryset.model
    else:
        queryset = tag_model.objects
    options = tag_model.tag_options

    query = request.GET.get("q", "")
    page = int(request.GET.get("p", 1))

    if query:
        if options.force_lowercase:
            query = query.lower()

        if options.autocomplete_view_fulltext:
            lookup = "contains"
        else:
            lookup = "startswith"

        if not options.case_sensitive:
            lookup = f"i{lookup}"

        results = queryset.filter(**{f"name__{lookup}": query})

    else:
        results = queryset.all()

    if options.autocomplete_limit:
        start = options.autocomplete_limit * (page - 1)
        end = options.autocomplete_limit * page
        more = results.count() > end
        results = results.order_by("-count")[start:end]

    response = {"results": [tag.name for tag in results], "more": more}
    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder), content_type="application/json")


class UpdateMemberView(
    DatasetStructureMixin,
    HistoryMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    PlanMixin,
    UpdateView,
):
    model = Representative
    form_class = DatasetMemberUpdateForm
    template_name = "base_form.html"
    pk_url_kwarg = "representative_id"

    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"

    def has_permission(self):
        subclass = self.dataset.subclass
        representative = get_object_or_404(
            Representative,
            pk=self.kwargs.get("representative_id"),
        )
        return has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_REPRESENTATIVE_CREATE if subclass.is_information_system else Action.UPDATE,
            representative,
        )

    def get_success_url(self):
        return reverse(
            "dataset-members",
            kwargs={
                "pk": self.kwargs.get("pk"),
            },
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["object"] = self.dataset
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tabs"] = "vitrina/datasets/tabs.html"
        context["can_view_members"] = self.has_permission()
        context["representative_url"] = reverse("dataset-members", args=[self.dataset.pk])
        context["current_title"] = _("Tvarkytojo redagavimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def get_detail_object(self):
        return self.dataset

    def get_history_object(self):
        return self.dataset

    def get_plan_object(self) -> Dataset:
        return self.dataset

    def form_valid(self, form):
        self.object: Representative = form.save()

        self.dataset.save()
        link = "%s%s" % (
            get_current_domain(self.request),
            reverse("dataset-detail", kwargs={"pk": self.dataset.pk}),
        )
        manage_subscriptions_for_representative(
            form.cleaned_data.get("subscribe"), self.object.user, self.dataset, link
        )

        if self.object.has_api_access:
            if not self.object.apikey_set.exists():
                api_key = secrets.token_urlsafe()
                ApiKey.objects.create(
                    api_key=hash_api_key(api_key),
                    enabled=True,
                    representative=self.object,
                )
                serializer = URLSafeSerializer(settings.SECRET_KEY)
                api_key = serializer.dumps({"api_key": api_key})
                return HttpResponseRedirect(
                    reverse(
                        "dataset-representative-api-key",
                        args=[self.dataset.pk, self.object.pk, api_key],
                    )
                )
            elif form.cleaned_data.get("regenerate_api_key"):
                api_key = secrets.token_urlsafe()
                api_key_obj = self.object.apikey_set.first()
                api_key_obj.api_key = hash_api_key(api_key)
                api_key_obj.enabled = True
                api_key_obj.save()

                serializer = URLSafeSerializer(settings.SECRET_KEY)
                api_key = serializer.dumps({"api_key": api_key})
                return HttpResponseRedirect(
                    reverse(
                        "dataset-representative-api-key",
                        args=[self.dataset.pk, self.object.pk, api_key],
                    )
                )
        else:
            self.object.apikey_set.all().delete()

        phone = form.cleaned_data.get("phone")
        if phone:
            self.object.phone = phone
            self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class DeleteMemberView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DeleteView,
):
    model = Representative
    template_name = "confirm_delete.html"

    def has_permission(self):
        representative = get_object_or_404(
            Representative,
            pk=self.kwargs.get("pk"),
        )
        dataset = get_object_or_404(
            Dataset,
            pk=self.kwargs.get("dataset_id"),
        )
        subclass = dataset.subclass
        return has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_REPRESENTATIVE_CREATE if subclass.is_information_system else Action.DELETE,
            representative,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        role = (
            "koordinatorių"
            if obj.role in Representative.COORDINATOR_ROLES
            else "tvarkytojų"
            if obj.organization
            else "tvarkytoją"
        )
        context["delete_text"] = (
            _(f'Ar tikrai norite pašalinti "{obj.organization.title}" iš {role}?')
            if obj.organization
            else _(f'Ar tikrai norite ištrinti "{obj}" {role}?')
        )
        return context

    def get_success_url(self):
        return reverse(
            "dataset-members",
            kwargs={
                "pk": self.kwargs.get("dataset_id"),
            },
        )

    def form_valid(self, form: BaseForm) -> HttpResponse:
        if self.object.content_type != ContentType.objects.get_for_model(Dataset):
            return super().form_valid(form)

        dataset = Dataset.objects.filter(id=self.object.object_id, publisher=self.object.organization).first()
        if dataset:
            dataset.publisher = None
            dataset.save(update_fields=["publisher"])

        return super().form_valid(form)


class DatasetProjectsView(DatasetStructureMixin, PermissionRequiredMixin, HistoryMixin, PlanMixin, ListView):
    model = Project
    template_name = "vitrina/datasets/project_list.html"
    context_object_name = "projects"
    paginate_by = 20

    # HistoryMixin
    object: Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object)

    def get_queryset(self):
        return get_projects(self.request.user).filter(datasets=self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.object
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context["available_projects"] = get_projects_linkable_to_dataset(self.request.user).exclude(
            datasets=self.object
        )
        context["removable_project_ids"] = set(
            get_projects_linkable_to_dataset(self.request.user)
            .filter(datasets=self.object)
            .values_list("pk", flat=True)
        )
        return context


class DatasetRequestsView(DatasetStructureMixin, PermissionRequiredMixin, HistoryMixin, PlanMixin, ListView):
    model = RequestObject
    template_name = "vitrina/datasets/request_list.html"
    context_object_name = "requests"
    paginate_by = 20

    # HistoryMixin
    object: Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object)

    def get_queryset(self):
        model_ids = Model.objects.filter(dataset=self.object).values_list("pk", flat=True)
        property_ids = Property.objects.filter(model__pk__in=model_ids).values_list("pk", flat=True)
        return RequestObject.objects.filter(
            Q(
                content_type=ContentType.objects.get_for_model(self.object),
                object_id=self.object.pk,
            )
            | Q(
                content_type=ContentType.objects.get_for_model(Model),
                object_id__in=model_ids,
            )
            | Q(
                content_type=ContentType.objects.get_for_model(Property),
                object_id__in=property_ids,
            )
        ).order_by("-request__created", "request__status")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.object
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        if self.request.user.is_authenticated:
            context["user_requests"] = get_requests(self.request.user, self.dataset)
        else:
            context["user_requests"] = []
        return context


class AddRequestView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Dataset
    form_class = AddRequestForm
    template_name = "base_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.dataset) and get_requests(self.request.user, self.dataset)

    def get_form_kwargs(self):
        kwargs = super(AddRequestView, self).get_form_kwargs()
        kwargs.update({"user": self.request.user})
        kwargs.update({"dataset": self.dataset})
        return kwargs

    def form_valid(self, form):
        super().form_valid(form)
        for request in form.cleaned_data["requests"]:
            RequestObject.objects.create(
                request=request,
                object_id=self.object.pk,
                content_type=ContentType.objects.get_for_model(self.object),
            )
            ra_object_exists = RequestAssignment.objects.filter(
                organization=self.dataset.organization,
                request=request,
            )
            if not ra_object_exists:
                RequestAssignment.objects.create(
                    organization=self.dataset.organization,
                    request=request,
                    status=request.status,
                )
        Task.objects.create(
            title=f"Poreikis duomenų rinkiniui: {self.dataset}",
            description=f"Sukurtas naujas poreikis duomenų rinkiniui: {self.dataset}.",
            content_type=ContentType.objects.get_for_model(self.dataset),
            object_id=self.dataset.pk,
            organization=Organization.objects.get(pk=self.dataset.organization_id),
            status=Task.CREATED,
            type=Task.REQUEST,
        )
        self.object.save()
        return HttpResponseRedirect(reverse("dataset-requests", kwargs={"pk": self.object.pk}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent_title"] = self.dataset
        context["parent_url"] = self.dataset.get_absolute_url()
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.object.pk]): self.object.title,
        }
        context["current_title"] = _("Poreikių pridėjimas")
        return context


class RemoveRequestView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Dataset
    template_name = "confirm_remove.html"

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get("pk"))
        self.request_object = get_object_or_404(RequestObject, pk=self.kwargs.get("request_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_remove_from_request_perm(self.dataset, self.request_object.request, self.request.user)

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse("dataset-requests", kwargs={"pk": self.dataset.pk}))

    def form_valid(self, form: BaseForm) -> HttpResponse:
        Comment.objects.filter(
            rel_object_id=self.request_object.request.pk,
            rel_content_type=ContentType.objects.get_for_model(self.request_object.request),
        ).delete()
        self.request_object.delete()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("dataset-requests", kwargs={"pk": self.dataset.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["request_title"] = self.request_object
        return context


class AddProjectView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Dataset
    form_class = AddProjectForm
    template_name = "base_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return get_projects_linkable_to_dataset(self.request.user).exclude(datasets=self.dataset).exists()

    def handle_no_permission(self):
        messages.error(
            self.request,
            _("Neturite panaudojimo atvejų, prie kurių galėtumėte pridėti išteklius."),
        )
        return redirect(reverse("dataset-projects", kwargs={"pk": self.dataset.pk}))

    def get_form_kwargs(self):
        kwargs = super(AddProjectView, self).get_form_kwargs()
        kwargs.update({"user": self.request.user})
        kwargs.update({"dataset": self.dataset})
        return kwargs

    def form_valid(self, form):
        super().form_valid(form)
        self.object = form.save()
        for project in form.cleaned_data["projects"]:
            temp_proj = get_object_or_404(Project, pk=project.pk)
            temp_proj.datasets.add(self.object)
        self.object.save()
        return HttpResponseRedirect(reverse("dataset-projects", kwargs={"pk": self.object.pk}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent_title"] = self.dataset
        context["parent_url"] = self.dataset.get_absolute_url()
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.object.pk]): self.object.title,
        }
        context["current_title"] = _("Panaudojimo atvejų pridėjimas")
        return context


class RemoveProjectView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Dataset
    template_name = "confirm_remove.html"

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get("pk"))
        self.project = get_object_or_404(Project, pk=self.kwargs.get("project_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return can_manage_datasets(self.request.user, self.project)

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse("dataset-projects", kwargs={"pk": self.dataset.pk}))

    def form_valid(self, form: BaseForm) -> HttpResponse:
        if self.project.agreements.exists():
            messages.error(
                self.request, _("Negalima pašalinti išteklių iš panaudojimo atvejo, kuris turi sugeneruotų sutarčių.")
            )
            return redirect(reverse("dataset-projects", args=[self.dataset.pk]))
        self.project.datasets.remove(self.dataset.pk)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("dataset-projects", kwargs={"pk": self.dataset.pk})


Y_TITLES = {
    "download-request-count": _("Atsisiuntimų (užklausų) skaičius"),
    "download-object-count": _("Atsisiuntimų (objektų) skaičius"),
    "object-count": _("Objektų skaičius"),
    "field-count": _("Savybių (duomenų laukų) skaičius"),
    "model-count": _("Esybių (modelių) skaičius"),
    "distribution-count": _("Duomenų šaltinių (distribucijų) skaičius"),
    "dataset-count": _("Duomenų rinkinių skaičius"),
    "request-count": _("Poreikių skaičius"),
    "project-count": _("Projektų skaičius"),
    "level-average": _("Brandos lygis"),
}

DATASET_INDICATOR_FIELDS = {
    "object-count": "object_count",
    "field-count": "field_count",
    "model-count": "model_count",
    "distribution-count": "distribution_count",
    "request-count": "request_count",
    "project-count": "project_count",
    "level-average": "maturity_level",
}

MODEL_INDICATOR_FIELDS = {
    "download-request-count": "model_requests",
    "download-object-count": "model_objects",
}


class DatasetStatsMixin(StatsMixin):
    model = Dataset
    filters_template_name = "vitrina/datasets/filters.html"
    parameter_select_template_name = "vitrina/datasets/stats_parameter_select.html"
    default_indicator = "dataset-count"
    list_url = reverse_lazy("dataset-list")

    def get_data_for_indicator(self, indicator, values, filter_queryset):
        if field := DATASET_INDICATOR_FIELDS.get(indicator):
            data = DatasetStats.objects.filter(dataset_id__in=filter_queryset.values_list("pk", flat=True)).values(
                *values
            )
            if indicator == "level-average":
                data = data.annotate(count=Avg(field))
            else:
                data = data.annotate(count=Sum(field))
        elif field := MODEL_INDICATOR_FIELDS.get(indicator):
            model_names = Metadata.objects.filter(
                content_type=ContentType.objects.get_for_model(Model),
                dataset__pk__in=filter_queryset.values_list("pk", flat=True),
            ).values_list("name", flat=True)
            data = ModelDownloadStats.objects.filter(model__in=model_names).values(*values).annotate(count=Sum(field))
        else:
            data = filter_queryset.values(*values).annotate(count=Count("pk"))
        return data

    def get_count(self, label, indicator, frequency, data, count):
        if data:
            if indicator == "object-count" or indicator == "level-average":
                count = data[0].get("count") or 0
            else:
                count += data[0].get("count") or 0
        return count

    def get_item_count(self, data, indicator):
        count = super().get_item_count(data, indicator)
        if indicator == "object-count":
            count = sum([x["y"] for x in data])
        elif indicator == "level-average":
            data = [x["y"] for x in data if x["y"]]
            if data:
                count = int(sum(data) / len(data))
            else:
                count = 0
        return count

    def get_title_for_indicator(self, indicator):
        return Y_TITLES.get(indicator) or indicator

    def get_parent_links(self):
        return {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
        }

    def get_time_axis_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _("Duomenų rinkinio įkėlimo data")
        else:
            return _("Laikas")


class DatasetStatsView(DatasetStatsMixin, DatasetListView):
    title = _("Būsena")
    current_title = _("Duomenų rinkinių būsenos")
    filter = "status"
    filter_choices = Dataset.FILTER_STATUSES

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio būseną rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio būseną laike")

    def update_context_data(self, context):
        facet_fields = context.get("facets").get("fields")
        statuses = self.get_filter_data(facet_fields)
        datasets = context["object_list"]

        indicator = self.request.GET.get("indicator", None) or "dataset-count"
        sorting = self.request.GET.get("sort", None) or "sort-desc"
        duration = self.request.GET.get("duration", None) or "duration-yearly"

        time_chart_data = []
        bar_chart_data = []

        most_recent_comments = (
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Dataset),
                object_id__in=datasets.exclude(status=Dataset.UNASSIGNED).values_list("pk", flat=True),
                status__isnull=False,
            )
            .values("object_id")
            .annotate(latest_status_change=Max("created"))
            .values("object_id", "latest_status_change")
            .order_by("latest_status_change")
        )

        dataset_status = Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id__in=most_recent_comments.values("object_id"),
            created__in=most_recent_comments.values("latest_status_change"),
        ).values(
            "object_id",
            "status",
            "created",
            "created__year",
            "created__quarter",
            "created__month",
            "created__week",
            "created__day",
        )

        frequency, ff = get_frequency_and_format(duration)
        end_date = datetime.now()
        start_date = get_start_date_based_on_frequency(frequency, end_date)
        labels = pd.period_range(start=start_date, end=end_date, freq=frequency).tolist()

        date_field = self.get_date_field()
        values = get_values_for_frequency(frequency, date_field)

        for status in statuses:
            bar_count = 0
            time_data = []
            bar_data = []
            status_dataset_ids = datasets.filter(status=status["filter_value"]).values_list("pk", flat=True)
            status_datasets = Dataset.objects.filter(pk__in=status_dataset_ids)

            count_data = self.get_data_for_indicator(indicator, values, status_datasets)

            for label in labels:
                time_count = 0
                label_query = get_query_for_frequency(frequency, date_field, label)
                if status["filter_value"] == Dataset.UNASSIGNED or indicator != "dataset-count":
                    label_count_data = count_data.filter(**label_query)
                    time_count = self.get_count(label, indicator, frequency, label_count_data, time_count)
                    bar_count += time_count
                else:
                    if status["filter_value"] == "HAS_DATA":
                        comm_val = "OPENED"
                    elif status["filter_value"] == "INVENTORED":
                        comm_val = "INVENTORED"
                    else:
                        comm_val = status["filter_value"]

                    time_count += dataset_status.filter(status=comm_val, **label_query).count()
                    bar_count += time_count

                if frequency == "W":
                    time_data.append({"x": _date(label.start_time, ff), "y": time_count})
                    bar_data.append({"x": _date(label.start_time, ff), "y": bar_count})
                else:
                    time_data.append({"x": _date(label, ff), "y": time_count})
                    bar_data.append({"x": _date(label, ff), "y": bar_count})

            dt = {
                "label": str(status["display_value"]),
                "data": time_data,
                "borderWidth": 1,
                "fill": True,
            }
            time_chart_data.append(dt)

            status["count"] = self.get_item_count(bar_data, indicator)
            bar_chart_data.append(status)

        if sorting == "sort-desc":
            time_chart_data = sorted(time_chart_data, key=lambda x: x["data"][-1]["y"], reverse=True)
            bar_chart_data = sorted(bar_chart_data, key=lambda x: x["count"], reverse=True)
        else:
            time_chart_data = sorted(time_chart_data, key=lambda x: x["data"][-1]["y"])
            bar_chart_data = sorted(bar_chart_data, key=lambda x: x["count"])

        max_count = max([x["count"] for x in bar_chart_data]) if bar_chart_data else 0

        context["title"] = self.title
        context["current_title"] = self.current_title
        context["tabs_template_name"] = self.tabs_template_name
        context["filters_template_name"] = self.filters_template_name
        context["parameter_select_template_name"] = self.parameter_select_template_name
        context["list_url"] = self.list_url
        context["has_time_graph"] = self.has_time_graph

        context["active_filter"] = self.filter
        context["active_indicator"] = indicator
        context["duration"] = duration

        context["graph_title"] = self.get_graph_title(indicator)
        context["xAxis_title"] = self.get_time_axis_title(indicator)
        context["yAxis_title"] = self.get_title_for_indicator(indicator)
        context["time_chart_data"] = json.dumps(time_chart_data)

        context["bar_chart_data"] = bar_chart_data
        context["max_count"] = max_count

        context["options"] = get_stats_filter_options_based_on_model(
            Dataset, duration, sorting, indicator, filter=self.filter
        )
        return context


class DatasetManagementsView(DatasetStatsMixin, DatasetListView):
    title = _("Valdymo sritis")
    current_title = _("Duomenų rinkinių valdymo sritys")
    filter = "jurisdiction"
    filter_model = AreaOfManagement
    use_str = True

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio valdymo sritį rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio valdymo sritį laike")


class DatasetsLevelView(DatasetStatsMixin, DatasetListView):
    title = _("Brandos lygis")
    current_title = _("Duomenų rinkinių brandos lygiai")
    filter = "level"

    def get_display_value(self, item):
        return "★" * item["filter_value"]

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio brandos lygį rinkinio įkėlimo datai")
        else:
            return _(f"{Y_TITLES.get(indicator, '')} pagal rinkinio brandos lygį laike")


class DatasetsOrganizationsView(DatasetStatsMixin, DatasetListView):
    title = _("Organizacija")
    current_title = _("Duomenų rinkinių organizacijos")
    filter = "organization"
    filter_model = Organization

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio organizaciją rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio organizaciją laike")


class DatasetsPublishersView(DatasetStatsMixin, DatasetListView):
    title = _("Duomenų atvėrimo paslaugų teikėjas")
    current_title = _("Duomenų atvėrimo paslaugų teikėjas")
    filter = "publisher"
    filter_model = Organization

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio organizaciją rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio organizaciją laike")


class DatasetsTagsView(DatasetStatsMixin, DatasetListView):
    title = _("Žymė")
    current_title = _("Duomenų rinkinių žymės")
    filter = "tags"

    def get_display_value(self, item):
        if tag := Dataset.tags.tag_model.objects.filter(pk=item["filter_value"]).first():
            return tag.name
        return item["display_value"]

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio žymes rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio žymes laike")


class DatasetsFormatView(DatasetStatsMixin, DatasetListView):
    title = _("Formatas")
    current_title = _("Duomenų rinkinių formatai")
    filter = "formats"
    filter_model = Format

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio formatą rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio formatą laike")


class DatasetsFrequencyView(DatasetStatsMixin, DatasetListView):
    title = _("Atnaujinama")
    current_title = _("Duomenų rinkinių atnaujinimo dažnumas")
    filter = "frequency"
    filter_model = Frequency
    use_str = True

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio atnaujinimą rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio atnaujinimą laike")


class DatasetsGroupView(DatasetStatsMixin, DatasetListView):
    title = _("Grupė")
    current_title = _("Duomenų rinkinių grupės")
    filter = "groups"
    filter_model = DatasetGroup

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio grupes rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio grupes laike")


class DatasetsAccessRightsView(DatasetStatsMixin, DatasetListView):
    title = _("Prieigos teisės")
    current_title = _("Duomenų rinkinių prieigos teisės")
    filter = "access_rights"
    filter_choices = Dataset.FILTER_ACCESS_RIGHTS

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio prieigos teises rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio prieigos teises laike")

    def get_display_value(self, item):
        value = super().get_display_value(item)
        return str(value)


class DatasetsCategoriesView(DatasetStatsMixin, DatasetListView):
    title = _("Kategorija")
    current_title = _("Duomenų išteklių kategorijos")
    filter = "category"
    filter_model = Category
    use_str = True

    def get_graph_title(self, indicator):
        if indicator == "level-average" or indicator == "object-count":
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio kategoriją rinkinio įkėlimo datai")
        else:
            return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio kategoriją laike")

    def update_item_data(self, item):
        obj = get_object_or_404(Category, pk=item["filter_value"])
        children = obj.get_children()
        if len(children) > 0:
            item.update({"full_url": reverse("dataset-stats-category-children", args=[obj.pk])})
        return item


class OrganizationStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = "vitrina/datasets/organizations.html"
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        indicator = self.request.GET.get("indicator", None)
        orgs = {}
        keys = list(orgs.keys())
        values = list(orgs.values())
        for v in values:
            if max_count < v:
                max_count = v
        sorted_value_index = np.flip(np.argsort(values))
        sorted_orgs = {keys[i]: values[i] for i in sorted_value_index}
        context["organization_data"] = sorted_orgs
        context["max_count"] = max_count
        context["active_filter"] = "organizations"
        context["active_indicator"] = indicator
        context["yAxis_title"] = Y_TITLES[indicator]
        return context


class JurisdictionStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = "vitrina/datasets/jurisdictions.html"
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        current_org = Organization.objects.get(id=self.kwargs.get("pk"))
        child_orgs = current_org.get_children()
        indicator = self.request.GET.get("indicator", None) or "dataset-count"
        sorting = self.request.GET.get("sort", None) or "sort-desc"
        filtered_orgs = []

        for org in child_orgs:
            modified = {}
            id_list = []
            datasets = Dataset.objects.filter(organization=org).values_list("id", flat=True)
            if len(datasets) > 0:
                for d in datasets:
                    id_list.append(d)
            modified[org] = id_list
            filtered_orgs.append(modified)
        result = []
        for single in filtered_orgs:
            single_dict = {}
            for k, v in single.items():
                single_dict["id"] = k.pk
                single_dict["title"] = k.title
                single_dict["url"] = "?selected_facets=jurisdiction_exact:" + str(k.pk)
                if len(k.get_children()) > 0:
                    single_dict["has_orgs"] = True
                else:
                    single_dict["has_orgs"] = False
                if indicator == "dataset-count":
                    single_dict["count"] = len(v)
                    if max_count < len(v):
                        max_count = len(v)
                if sorting == "sort-asc":
                    single_dict = sorted(single_dict, key=lambda dd: dd["count"], reverse=False)
                elif indicator != "dataset-count":
                    if indicator == "download-request-count" or indicator == "download-object-count":
                        models = Model.objects.filter(dataset_id__in=v).values_list("metadata__name", flat=True)
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == "download-request-count":
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == "download-object-count":
                                            if m_st is not None:
                                                total += m_st.model_objects
                        single_dict["count"] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=v)
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                total = get_total_by_indicator_from_stats(st, indicator, total)
                            single_dict["count"] = total
                            if max_count < single_dict.get("count"):
                                max_count = single_dict.get("count")
                        else:
                            single_dict["count"] = 0
            result.append(single_dict)
            if sorting == "sort-desc":
                result = sorted(result, key=lambda dd: dd["count"], reverse=True)
            else:
                result = sorted(result, key=lambda dd: dd["count"], reverse=False)
            # result = sorted(result, key=lambda dd: dd['count'], reverse=True)
        context["single_org"] = True
        context["jurisdiction_data"] = result
        context["max_count"] = max_count
        context["current_object"] = self.kwargs.get("pk")
        context["active_filter"] = "jurisdiction"
        context["active_indicator"] = indicator
        context["sort"] = sorting
        return context


class CategoryStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = "vitrina/datasets/categories.html"
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        facet_fields = context.get("facets").get("fields")
        all_cats = update_facet_data(self.request, facet_fields, "category", Category)
        child_titles = []
        cat_titles = []
        indicator = self.request.GET.get("indicator", None) or "dataset-count"
        sorting = self.request.GET.get("sort", None) or "sort-desc"
        for cat in all_cats:
            cat_titles.append(cat["display_value"])
        filtered_cats = []
        parent_category = Category.objects.get(id=self.kwargs.get("pk"))
        children = Category.get_children(parent_category)
        for child in children:
            child_titles.append(child.title)
        for single_cat in all_cats:
            if single_cat["display_value"] in child_titles:
                cat_object = Category.objects.get(title=single_cat["display_value"])
                subcategories = Category.get_children(cat_object)
                if len(subcategories) > 0:
                    exists = 0
                    for ss in subcategories:
                        if ss.title in cat_titles:
                            exists += 1
                    if exists == 0:
                        single_cat["has_cats"] = False
                else:
                    single_cat["has_cats"] = False
                if max_count < single_cat.get("count"):
                    max_count = single_cat.get("count")
                filtered_cats.append(single_cat)
        if sorting == "sort-asc":
            filtered_cats = sorted(filtered_cats, key=lambda dd: dd["count"], reverse=False)
        if indicator != "dataset-count":
            for k in filtered_cats:
                id_list = []
                c_cat = Category.objects.get(title=k.get("display_value"))
                cat_datasets = Dataset.objects.filter(category=c_cat.pk)
                if len(cat_datasets) > 0:
                    for dd in cat_datasets:
                        id_list.append(dd.pk)
                    if indicator == "download-request-count" or indicator == "download-object-count":
                        models = Model.objects.filter(dataset_id__in=id_list).values_list("metadata__name", flat=True)
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == "download-request-count":
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == "download-object-count":
                                            if m_st is not None:
                                                total += m_st.model_objects
                        k["stats"] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=id_list)
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                if indicator == "request-count":
                                    if st.request_count is not None:
                                        total += st.request_count
                                    k["stats"] = total
                                elif indicator == "project-count":
                                    if st.project_count is not None:
                                        total += st.project_count
                                    k["stats"] = total
                                elif indicator == "distribution-count":
                                    if st.distribution_count is not None:
                                        total += st.distribution_count
                                    k["stats"] = total
                                elif indicator == "object-count":
                                    if st.object_count is not None:
                                        total += st.object_count
                                    k["stats"] = total
                                elif indicator == "field-count":
                                    if st.field_count is not None:
                                        total += st.field_count
                                    k["stats"] = total
                                elif indicator == "model-count":
                                    if st.model_count is not None:
                                        total += st.model_count
                                    k["stats"] = total
                                elif indicator == "level-average":
                                    lev = []
                                    if st.maturity_level is not None:
                                        lev.append(st.maturity_level)
                                    level_avg = int(sum(lev) / len(lev))
                                    k["stats"] = level_avg
                                if max_count < k.get("stats"):
                                    max_count = k.get("stats")
                        else:
                            k["stats"] = 0
            if sorting is None or sorting == "sort-desc":
                filtered_cats = sorted(filtered_cats, key=lambda d: d["stats"], reverse=True)
            else:
                filtered_cats = sorted(filtered_cats, key=lambda d: d["stats"], reverse=False)
            # filtered_cats = sorted(filtered_cats, key=lambda d: d['stats'], reverse=True)
        context["max_count"] = max_count
        context["category_data"] = filtered_cats
        context["current_object"] = self.kwargs.get("pk")
        context["active_filter"] = "category"
        context["active_indicator"] = indicator
        context["sort"] = sorting
        context["yAxis_title"] = Y_TITLES[indicator]
        return context


class PublicationStatsView(DatasetStatsMixin, DatasetListView):
    title = _("Įkėlimo data")
    current_title = _("Duomenų rinkinių kiekis metuose")
    facet_fields = DatasetListView.facet_fields
    template_name = "vitrina/datasets/published_dates.html"
    filter = "published"
    filter_model = Category
    paginate_by = 0

    def get_graph_title(self, indicator):
        return _(f"{self.get_title_for_indicator(indicator)} pagal rinkinio įkėlimo datą laike")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        datasets = self.get_queryset()
        indicator = self.request.GET.get("indicator", None) or "dataset-count"
        sorting = self.request.GET.get("sort", None) or "sort-desc"
        duration = self.request.GET.get("duration", None) or "duration-yearly"
        start_date = Dataset.objects.order_by("created").first().created
        max_count = 0
        stats_for_period = {}
        year_stats = {}
        chart_data = []

        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(start=start_date, end=datetime.now(), freq=frequency).tolist()

        for dataset in datasets:
            published = dataset.published
            if published is not None:
                year_published = published.year
                year_stats[str(year_published)] = year_stats.get(str(year_published), 0) + 1
                period = str(pd.to_datetime(published).to_period(frequency))
                stats_for_period[period] = stats_for_period.get(period, 0) + 1

        if indicator != "dataset-count":
            for yr in year_stats.keys():
                start_date = datetime.strptime(str(yr) + "-1-1", "%Y-%m-%d")
                end_date = datetime.strptime(str(yr) + "-12-31", "%Y-%m-%d")
                tz = pytz.timezone("Europe/Vilnius")
                filtered_datasets = datasets.filter(published__range=[tz.localize(start_date), tz.localize(end_date)])
                dataset_ids = []
                for fd in filtered_datasets:
                    dataset_ids.append(fd.pk)
                if indicator == "download-request-count" or indicator == "download-object-count":
                    models = Model.objects.filter(dataset_id__in=dataset_ids).values_list("metadata__name", flat=True)
                    total = 0
                    if len(models) > 0:
                        for m in models:
                            model_stats = ModelDownloadStats.objects.filter(model=m)
                            if len(model_stats) > 0:
                                for m_st in model_stats:
                                    if indicator == "download-request-count":
                                        if m_st is not None:
                                            total += m_st.model_requests
                                    elif indicator == "download-object-count":
                                        if m_st is not None:
                                            total += m_st.model_objects
                    year_stats[yr] = total
                else:
                    stats = DatasetStats.objects.filter(dataset_id__in=dataset_ids)
                    if len(stats) > 0:
                        total = 0
                        for st in stats:
                            total = get_total_by_indicator_from_stats(st, indicator, total)
                        year_stats[yr] = total
                    else:
                        year_stats[yr] = 0
        if year_stats:
            keys = list(year_stats.keys())
            values = list(year_stats.values())
            sorted_value_index = np.argsort(values)
            year_stats = sort_publication_stats(sorting, values, keys, year_stats, sorted_value_index)
            max_count = year_stats[max(year_stats, key=lambda key: year_stats[key], default=0)]

        data = []
        total = 0
        for label in labels:
            dataset_count = stats_for_period.get(str(label), 0)
            if indicator == "dataset-count":
                total += dataset_count
            else:
                dataset_ids = Dataset.objects.filter(created__year=label.year).values_list("pk", flat=True)
                stat = DatasetStats.objects.filter(dataset_id__in=dataset_ids)
                per_datasets = 0
                if len(stat) > 0:
                    for st in stat:
                        per_datasets = get_total_by_indicator_from_stats(st, indicator, per_datasets)
                total += per_datasets

            if frequency == "W":
                data.append({"x": _date(label.start_time, ff), "y": total})
            else:
                data.append({"x": _date(label, ff), "y": total})

        dt = {
            "label": "Duomenų rinkinių kiekis",
            "data": data,
            "borderWidth": 1,
            "fill": True,
        }
        chart_data.append(dt)

        context["title"] = self.title
        context["current_title"] = self.current_title
        context["data"] = json.dumps(chart_data)
        context["year_stats"] = year_stats
        context["max_count"] = max_count

        context["graph_title"] = self.get_graph_title(indicator)
        context["yAxis_title"] = self.get_title_for_indicator(indicator)
        context["xAxis_title"] = _("Laikas")

        context["active_filter"] = self.filter
        context["active_indicator"] = indicator
        context["sort"] = sorting
        context["duration"] = duration

        context["has_time_graph"] = True
        return context


class YearStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = "vitrina/datasets/publications.html"
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get("indicator", None) or "dataset-count"
        sorting = self.request.GET.get("sort", None) or "sort-desc"
        year_stats = {}
        quarter_stats = {}
        selected_year = str(self.kwargs["year"])

        for dataset in datasets:
            published = dataset.published
            if published is not None:
                year_published = published.year
                year_stats[year_published] = year_stats.get(year_published, 0) + 1
                quarter = str(year_published) + "-Q" + str(pd.Timestamp(published).quarter)
                quarter_stats[quarter] = quarter_stats.get(quarter, 0) + 1
        if indicator != "dataset-count":
            for k in quarter_stats.keys():
                tz = pytz.timezone("Europe/Vilnius")
                if selected_year in k:
                    if "-Q1" in k:
                        start = datetime.strptime(str(selected_year) + "-1-1", "%Y-%m-%d")
                        end = datetime.strptime(str(selected_year) + "-3-31", "%Y-%m-%d")
                    elif "-Q2" in k:
                        start = datetime.strptime(str(selected_year) + "-4-1", "%Y-%m-%d")
                        end = datetime.strptime(str(selected_year) + "-6-30", "%Y-%m-%d")
                    elif "-Q3" in k:
                        start = datetime.strptime(str(selected_year) + "-7-1", "%Y-%m-%d")
                        end = datetime.strptime(str(selected_year) + "-9-30", "%Y-%m-%d")
                    else:
                        start = datetime.strptime(str(selected_year) + "-10-1", "%Y-%m-%d")
                        end = datetime.strptime(str(selected_year) + "-12-31", "%Y-%m-%d")
                    filtered_datasets = datasets.filter(published__range=[tz.localize(start), tz.localize(end)])
                    dataset_ids = []
                    for fd in filtered_datasets:
                        dataset_ids.append(fd.pk)
                    if indicator == "download-request-count" or indicator == "download-object-count":
                        models = Model.objects.filter(dataset_id__in=dataset_ids).values_list(
                            "metadata__name", flat=True
                        )
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == "download-request-count":
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == "download-object-count":
                                            if m_st is not None:
                                                total += m_st.model_objects
                        quarter_stats[k] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=dataset_ids)
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                total += get_total_by_indicator_from_stats(st, indicator, total)
                            quarter_stats[k] = total
                        else:
                            quarter_stats[k] = 0
        for key, value in quarter_stats.items():
            if max_count < value:
                max_count = value
        keys = list(quarter_stats.keys())
        values = list(quarter_stats.values())
        sorted_value_index = np.argsort(values)
        quarter_stats = sort_publication_stats_reversed(sorting, values, keys, quarter_stats, sorted_value_index)
        context["selected_year"] = selected_year
        context["year_stats"] = quarter_stats
        context["max_count"] = max_count
        context["current_object"] = str("year/" + selected_year)
        context["active_filter"] = "publication"
        context["active_indicator"] = indicator
        context["sort"] = sorting
        context["yAxis_title"] = Y_TITLES[indicator]
        return context


class QuarterStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = "vitrina/datasets/publications.html"
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get("indicator", None) or "dataset-count"
        sorting = self.request.GET.get("sort", None) or "sort-desc"
        monthly_stats = {}
        selected_quarter = str(self.kwargs["quarter"])

        for dataset in datasets:
            published = dataset.published
            if published is not None:
                year_published = published.year
                if str(year_published) in selected_quarter:
                    quarter = str(year_published) + "-Q" + str(pd.Timestamp(published).quarter)
                    if quarter == selected_quarter:
                        month = str(year_published) + "-" + str("%02d" % published.month)
                        monthly_stats[month] = monthly_stats.get(month, 0) + 1
        if indicator != "dataset-count":
            for k in monthly_stats.keys():
                tz = pytz.timezone("Europe/Vilnius")
                start = datetime.strptime(str(k) + "-1", "%Y-%m-%d")
                end = datetime.strptime(str(k) + "-28", "%Y-%m-%d")
                filtered_datasets = datasets.filter(published__range=[tz.localize(start), tz.localize(end)])
                dataset_ids = []
                for fd in filtered_datasets:
                    dataset_ids.append(fd.pk)
                if indicator == "download-request-count" or indicator == "download-object-count":
                    models = Model.objects.filter(dataset_id__in=dataset_ids).values_list("metadata__name", flat=True)
                    total = 0
                    if len(models) > 0:
                        for m in models:
                            model_stats = ModelDownloadStats.objects.filter(model=m)
                            if len(model_stats) > 0:
                                for m_st in model_stats:
                                    if indicator == "download-request-count":
                                        if m_st is not None:
                                            total += m_st.model_requests
                                    elif indicator == "download-object-count":
                                        if m_st is not None:
                                            total += m_st.model_objects
                    monthly_stats[k] = total
                else:
                    stats = DatasetStats.objects.filter(dataset_id__in=dataset_ids)
                    if len(stats) > 0:
                        total = 0
                        for st in stats:
                            total += get_total_by_indicator_from_stats(st, indicator, total)
                        monthly_stats[k] = total
                    else:
                        monthly_stats[k] = 0
        for m, mv in monthly_stats.items():
            if max_count < mv:
                max_count = mv
        keys = list(monthly_stats.keys())
        values = list(monthly_stats.values())
        sorted_value_index = np.argsort(values)
        monthly_stats = sort_publication_stats_reversed(sorting, values, keys, monthly_stats, sorted_value_index)
        context["selected_quarter"] = self.kwargs["quarter"]
        context["year_stats"] = monthly_stats
        context["max_count"] = max_count
        context["current_object"] = str("quarter/" + selected_quarter)
        context["active_filter"] = "publication"
        context["active_indicator"] = indicator
        context["sort"] = sorting
        context["yAxis_title"] = Y_TITLES[indicator]
        return context


class DatasetCategoryView(PermissionRequiredMixin, TemplateView):
    template_name = "vitrina/datasets/dataset_categories.html"

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("dataset_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = DatasetCategoryForm(self.dataset)
        context["dataset"] = self.dataset
        return context

    def post(self, request, *args, **kwargs):
        form = DatasetCategoryForm(self.dataset, request.POST)
        if form.is_valid():
            self.dataset.category.clear()
            for category in form.cleaned_data.get("category"):
                self.dataset.category.add(category)
            self.dataset.save()

            DatasetExcludedGroups.objects.filter(dataset=self.dataset).delete()
            for group in DatasetGroup.objects.filter(
                datasetgroupcategoryuri__category__in=form.cleaned_data.get("category")
            ).distinct():
                if group not in form.cleaned_data.get("group"):
                    DatasetExcludedGroups.objects.create(dataset=self.dataset, group=group)
        else:
            messages.error(request, "\n".join([error[0] for error in form.errors.values()]))
        return redirect(self.dataset.get_absolute_url())


class FilterGroupsView(LoginRequiredMixin, View):
    @staticmethod
    def get(request, *args, **kwargs):
        dataset_id = kwargs.get("dataset_id")
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        category_ids = request.GET.get("category_ids", "").split(",") if request.GET.get("category_ids") else []

        groups = DatasetGroup.objects.filter(datasetgroupcategoryuri__category__in=category_ids).distinct()
        excluded_groups = dataset.get_excluded_groups()
        group_data = {group.pk: {"title": group.title, "checked": group.pk not in excluded_groups} for group in groups}
        return JsonResponse({"groups": group_data})


class FilterCategoryView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        category_data = {}
        group_categories = []

        if group_id := request.GET.get("group_id"):
            group = get_object_or_404(DatasetGroup, pk=int(group_id))
            group_categories = group.category_set.all()
            categories = group_categories

        if ids := request.GET.get("category_ids"):
            ids = [int(i) for i in ids.split(",")]
            categories = categories.filter(pk__in=ids)

        if term := request.GET.get("term"):
            lang = get_language()
            if lang == "en":
                categories = categories.filter(title_en__icontains=term)
            else:
                categories = categories.filter(title__icontains=term)

        for cat in categories:
            category_data[cat.pk] = {
                "show_checkbox": True,
            }
            for ancestor in cat.get_ancestors():
                if ancestor not in categories:
                    category_data[ancestor.pk] = {
                        "show_checkbox": True if ancestor in group_categories or not group_id else False,
                    }
        return JsonResponse({"categories": category_data})


class DatasetAttributionCreateView(PermissionRequiredMixin, CreateView):
    model = DatasetAttribution
    form_class = DatasetAttributionForm
    template_name = "vitrina/datasets/attribution_form.html"

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("dataset_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.dataset
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        return context

    def form_valid(self, form):
        self.object: DatasetAttribution = form.save(commit=False)
        self.object.dataset = self.dataset
        self.object.save()
        return redirect(self.dataset.get_absolute_url())


class DatasetAttributionDeleteView(PermissionRequiredMixin, DeleteView):
    model = DatasetAttribution

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("dataset_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def form_valid(self, form: BaseForm) -> HttpResponse:
        self.object = self.get_object()
        add_to_revision(self.object)

        return super().form_valid(form)

    def get_success_url(self):
        return self.dataset.get_absolute_url()


class DatasetRelationCreateView(PermissionRequiredMixin, CreateView):
    model = DatasetRelation
    form_class = DatasetRelationForm
    template_name = "vitrina/datasets/relation_form.html"

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.dataset
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        return context

    def form_valid(self, form):
        self.object: DatasetRelation = form.save(commit=False)

        if relation := form.cleaned_data.get("relation_type"):
            inverse = False
            if relation.endswith("_inv"):
                relation = relation.replace("_inv", "")
                inverse = True
            try:
                relation = Relation.objects.get(pk=int(relation))
            except (ValueError, ObjectDoesNotExist) as e:
                messages.error(self.request, e)
                return redirect(self.dataset.get_absolute_url())

            self.object.relation = relation
            if inverse:
                self.object.dataset = self.object.part_of
                self.object.part_of = self.dataset
            else:
                self.object.dataset = self.dataset
            self.object.save()
            self.object.dataset.part_of.add(self.object)

            # need to save to update search index
            self.object.dataset.save()
            self.object.part_of.save()

        return redirect(self.dataset.get_absolute_url())


class DatasetRelationDeleteView(PermissionRequiredMixin, DeleteView):
    model = DatasetRelation

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("dataset_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def form_valid(self, form: BaseForm) -> HttpResponse:
        self.object = self.get_object()
        add_to_revision(self.object)
        return super().form_valid(form)

    def get_success_url(self):
        return self.dataset.get_absolute_url()


class DatasetPlanView(
    HistoryMixin,
    DatasetStructureMixin,
    PermissionRequiredMixin,
    PlanMixin,
    TemplateView,
):
    template_name = "vitrina/datasets/plans.html"
    context_object_name = "dataset"
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-plans-history"
    plan_url_name = "dataset-plans"

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get("status", "opened")
        context["dataset"] = self.dataset
        if status == "closed":
            context["plans"] = self.dataset.plandataset_set.filter(plan__is_closed=True)
        else:
            context["plans"] = self.dataset.plandataset_set.filter(plan__is_closed=False)
        subclass = self.dataset.subclass
        context["can_manage_plans"] = has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.UPDATE,
            self.dataset,
        )
        context["can_view_members"] = has_perm(self.request.user, Action.VIEW, Representative, self.dataset)
        context["selected_tab"] = status
        return context

    def get_history_object(self):
        return self.dataset

    def get_detail_object(self):
        return self.dataset

    def get_plan_object(self):
        return self.dataset


class DatasetCreatePlanView(PermissionRequiredMixin, TemplateView):
    template_name = "vitrina/plans/plan_form.html"

    dataset: Dataset
    organizations: List[Organization]

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.organizations = [self.dataset.organization]
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["obj"] = self.dataset
        context["create_form"] = PlanForm(self.dataset, self.organizations, self.request.user)
        context["include_form"] = DatasetPlanForm(self.dataset)
        context["current_title"] = _("Įtraukti į planą")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
            reverse("dataset-plans", args=[self.dataset.pk]): _("Planas"),
        }
        return context

    def post(self, request, *args, **kwargs):
        form_type = request.POST.get("form_type")
        if form_type == "create_form":
            form = PlanForm(self.dataset, self.organizations, request.user, request.POST)
        else:
            form = DatasetPlanForm(self.dataset, request.POST)

        if form.is_valid():
            if form_type == "create_form":
                plan = form.save()
                PlanDataset.objects.create(plan=plan, dataset=self.dataset)

            else:
                plan_dataset = form.save(commit=False)
                plan_dataset.dataset = self.dataset
                plan_dataset.save()
                plan = plan_dataset.plan
                plan.save()

            Comment.objects.create(
                content_type=ContentType.objects.get_for_model(self.dataset),
                object_id=self.dataset.pk,
                user=self.request.user,
                type=Comment.PLAN,
                rel_content_type=ContentType.objects.get_for_model(plan),
                rel_object_id=plan.pk,
            )

            if (
                self.dataset.is_public
                and self.dataset.status != Dataset.HAS_DATA
                and self.dataset.status != Dataset.PLANNED
            ):
                self.dataset.status = Dataset.PLANNED
                self.dataset.save(update_fields=["status"])

            return redirect(reverse("dataset-plans", args=[self.dataset.pk]))
        else:
            context = self.get_context_data(**kwargs)
            context[form_type] = form
            return render(request=request, template_name=self.template_name, context=context)


class DatasetDeletePlanView(PermissionRequiredMixin, DeleteView):
    model = PlanDataset
    template_name = "confirm_delete.html"

    def has_permission(self):
        dataset = self.get_object().dataset
        return has_perm(self.request.user, Action.UPDATE, dataset)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        plan = self.object.plan
        dataset = self.object.dataset
        self.object.delete()

        plan.save()

        if dataset.is_public and dataset.status == Dataset.PLANNED and not dataset.plandataset_set.exists():
            dataset.status = Dataset.INVENTORED
            dataset.save(update_fields=["status"])

        return redirect(reverse("dataset-plans", args=[dataset.pk]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = self.get_object().dataset
        context["current_title"] = _("Termino pašalinimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[dataset.pk]): dataset.title,
        }
        return context


class DatasetDeletePlanDetailView(DatasetDeletePlanView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object().plan.receiver
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("organization-list"): _("Organizacijos"),
            reverse("organization-detail", args=[organization.pk]): organization.title,
        }
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        plan = self.object.plan
        dataset = self.object.dataset
        self.object.delete()

        plan.save()

        if dataset.is_public and dataset.status == Dataset.PLANNED and not dataset.plandataset_set.exists():
            dataset.status = Dataset.INVENTORED
            dataset.save(update_fields=["status"])

        return redirect(reverse("plan-detail", args=[plan.receiver.pk, plan.pk]))


class DatasetPlansHistoryView(DatasetStructureMixin, PlanMixin, HistoryView):
    model = Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-plans-history"
    plan_url_name = "dataset-plans"
    tabs_template_name = "vitrina/datasets/tabs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.object.pk]): self.object.title,
            reverse("dataset-plans", args=[self.object.pk]): _("Planas"),
        }
        return context

    def get_history_objects(self):
        dataset_plan_ids = PlanDataset.objects.filter(dataset=self.object).values_list("plan_id", flat=True)
        return (
            Version.objects.get_for_model(Plan)
            .filter(object_id__in=list(dataset_plan_ids))
            .order_by("-revision__date_created")
        )


class UpdateDatasetOrgFilters(FacetedSearchView):
    template_name = "vitrina/datasets/organization_filter_items.html"
    form_class = DatasetSearchForm
    facet_fields = DatasetListView.facet_fields

    def get_queryset(self):
        datasets = super().get_queryset()
        datasets = get_datasets_for_user(self.request, datasets)
        return datasets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get("q")
        if q and len(q) > 2:
            facet_fields = context.get("facets").get("fields")
            form = context.get("form")
            filter_args = (self.request, form, facet_fields)
            filter = (
                Filter(
                    *filter_args,
                    "organization",
                    _("Organizacija"),
                    Organization,
                    multiple=True,
                    is_int=False,
                    remove_search_query=True,
                ),
            )
            items = []
            for item in filter[0].items():
                if q.lower() in item.title.lower():
                    items.append(item)
            extra_context = {"filter_items": items}
            context.update(extra_context)
            return context


class UpdateDatasetCategoryFilters(FacetedSearchView):
    template_name = "vitrina/datasets/category_filter_items.html"
    form_class = DatasetSearchForm
    facet_fields = DatasetListView.facet_fields

    def get_queryset(self):
        datasets = super().get_queryset()
        datasets = get_datasets_for_user(self.request, datasets)
        return datasets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get("q")
        if q and len(q) > 2:
            facet_fields = context.get("facets").get("fields")
            form = context.get("form")
            filter_args = (self.request, form, facet_fields)
            filter = (
                Filter(
                    *filter_args,
                    "category",
                    _("Kategorija"),
                    Category,
                    multiple=True,
                    is_int=False,
                    use_str=True,
                    remove_search_query=True,
                ),
            )
            items = []
            for item in filter[0].items():
                if q.lower() in item.title.lower():
                    items.append(item)
            extra_context = {"filter_items": items}
            context.update(extra_context)
            return context


class UpdateDatasetTagFilters(FacetedSearchView):
    template_name = "vitrina/datasets/tag_filter_items.html"
    form_class = DatasetSearchForm
    facet_fields = DatasetListView.facet_fields

    def get_queryset(self):
        datasets = super().get_queryset()
        datasets = get_datasets_for_user(self.request, datasets)
        return datasets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get("q")
        if q and len(q) > 2:
            facet_fields = context.get("facets").get("fields")
            form = context.get("form")
            filter_args = (self.request, form, facet_fields)
            filter = (
                Filter(
                    *filter_args,
                    "tags",
                    _("Žymė"),
                    Dataset,
                    multiple=True,
                    is_int=False,
                    display_method="get_tag_title",
                    remove_search_query=True,
                ),
            )
            items = []
            for item in filter[0].items():
                if q.lower() in item.title.lower():
                    items.append(item)
            extra_context = {"filter_items": items}
            context.update(extra_context)
            return context


class UpdateDatasetJurisdictionFilters(FacetedSearchView):
    template_name = "vitrina/datasets/jurisdiction_filter_items.html"
    form_class = DatasetSearchForm
    facet_fields = DatasetListView.facet_fields

    def get_queryset(self):
        datasets = super().get_queryset()
        datasets = get_datasets_for_user(self.request, datasets)
        return datasets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get("q")
        if q and len(q) > 2:
            facet_fields = context.get("facets").get("fields")
            form = context.get("form")
            filter_args = (self.request, form, facet_fields)
            filter = (
                Filter(
                    *filter_args,
                    "jurisdiction",
                    _("Valdymo sritis"),
                    AreaOfManagement,
                    multiple=True,
                    is_int=False,
                    use_str=True,
                    remove_search_query=True,
                ),
            )
            items = []
            for item in filter[0].items():
                if q.lower() in item.title.lower():
                    items.append(item)
            extra_context = {"filter_items": items}
            context.update(extra_context)
            return context


class UpdateDatasetPublisherFilters(FacetedSearchView):
    template_name = "vitrina/datasets/publisher_filter_items.html"
    form_class = DatasetSearchForm
    facet_fields = DatasetListView.facet_fields

    def get_queryset(self):
        datasets = super().get_queryset()
        datasets = get_datasets_for_user(self.request, datasets)
        return datasets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get("q")
        if q and len(q) > 2:
            facet_fields = context.get("facets").get("fields")
            form = context.get("form")
            filter_args = (self.request, form, facet_fields)
            filter = (
                Filter(
                    *filter_args,
                    "publisher",
                    _("Duomenų atvėrimo paslaugų teikėjas"),
                    Organization,
                    multiple=True,
                    is_int=False,
                    remove_search_query=True,
                ),
            )
            items = []
            for item in filter[0].items():
                if q.lower() in item.title.lower():
                    items.append(item)
            extra_context = {"filter_items": items}
            context.update(extra_context)
            return context


class DatasetRepresentativeApiKeyView(PermissionRequiredMixin, TemplateView):
    template_name = "vitrina/orgs/api_key.html"

    dataset: Organization
    representative: Representative

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.representative = get_object_or_404(Representative, pk=kwargs.get("rep_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.dataset,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        serializer = URLSafeSerializer(settings.SECRET_KEY)
        api_key = kwargs.get("key")
        data = serializer.loads(api_key)
        context["api_key"] = data.get("api_key")
        context["url"] = reverse("dataset-members", args=[self.dataset.pk])
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
            reverse("dataset-members", args=[self.dataset.pk]): _("Tvarkytojai"),
        }
        return context


class DatasetChildResourceListView(
    DatasetBreadcrumbsMixin,
    LanguageChoiceMixin,
    HistoryMixin,
    DatasetStructureMixin,
    DatasetListView,
):
    model = Dataset
    detail_url_name = DatasetDetailView.detail_url_name
    history_url_name = DatasetDetailView.history_url_name
    plan_url_name = DatasetDetailView.plan_url_name
    tabs_template_name = "vitrina/datasets/tabs.html"
    breadcrumb_title = _("Ištekliai")

    @property
    def page_title(self) -> str:
        return f"{self.object.title} " + _("vaikiniai duomenų ištekliai")

    @property
    def parent_dataset_id(self) -> int:
        return self.kwargs["pk"]

    @cached_property
    def object(self) -> Dataset:
        return Dataset.objects.get(pk=self.parent_dataset_id)

    def get_queryset(self) -> QuerySet[Dataset]:
        descendants: list[int] = self.object.get_descendants().values_list("pk", flat=True)
        return super(DatasetChildResourceListView, self).get_queryset().filter(django_id__in=list(descendants))

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, get_object_or_404(Dataset, pk=self.parent_dataset_id))

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        dataset = self.object
        subclass = dataset.subclass
        action = Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.CREATE
        return super().get_context_data(**kwargs) | {
            "can_create_dataset": has_perm(
                self.request.user,
                action,
                Dataset,
                self.object,
            ),
            "can_view_members": has_perm(
                self.request.user,
                Action.VIEW,
                Representative,
                self.object,
            ),
            "parent_dataset_id": self.parent_dataset_id,
            "organization_id": self.object.organization_id,
        }


class DatasetChildResourceCreateView(DatasetCreateView):
    @property
    def parent_dataset_id(self) -> int:
        return self.kwargs["parent_id"]

    @cached_property
    def parent_dataset(self) -> Dataset:
        return get_object_or_404(Dataset, pk=self.parent_dataset_id)

    @cached_property
    def organization(self) -> Organization:
        return self.parent_dataset.organization

    @property
    def organization_id(self) -> int:
        return self.parent_dataset.organization_id

    def has_permission(self):
        subclass = self.parent_dataset.subclass
        action = Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.CREATE
        return has_perm(self.request.user, action, Dataset, self.parent_dataset)

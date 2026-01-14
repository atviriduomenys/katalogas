import datetime
import uuid
import json
from typing import List, Union
from urllib import parse
from urllib.parse import unquote
from flags.decorators import flag_required
from django.utils.decorators import method_decorator

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, ForeignKey
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.db.models import Func, F, Value, TextField, Max
from django.forms import BaseForm
from django.http import Http404, StreamingHttpResponse, JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer
from pygments.lexers.special import TextLexer
from pygments.styles import get_style_by_name
from reversion import set_comment, set_user, create_revision
from reversion.models import Version
from shapely.wkt import loads
from flags.state import flag_enabled

from vitrina.classifiers.models import Status
from vitrina.datasets.models import Dataset
from vitrina.datasets.mixins import Crumb, DatasetBreadcrumbsMixin
from vitrina.helpers import get_current_domain, email, none_to_string, object_to_none, build_page_title_context
from vitrina.orgs.models import Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project
from vitrina.resources.models import DatasetDistribution
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure import spyna
from vitrina.structure.forms import (
    EnumForm,
    ModelCreateForm,
    ModelUpdateForm,
    PropertyForm,
    ParamForm,
    PublishForm,
)
from vitrina.structure.models import (
    Model,
    Property,
    Metadata,
    EnumItem,
    Enum,
    PropertyList,
    Base,
    ParamItem,
    Param,
    MetadataVersion,
    StatusCode,
    VersionStatus,
    Prefix,
)
from vitrina.structure.models import Version as _Version
from vitrina.structure.services import (
    get_data_from_spinta,
    export_dataset_structure,
    _export_dataset_structure_to_stringio,
    get_model_name,
    get_srid,
    transform_coordinates,
    get_data_from_spinta_async,
    get_allowed_visibilities,
)
from vitrina.tasks.models import Task
from spinta.manifests.open_api.helpers import create_openapi_manifest
from spinta.manifests.components import ManifestPath
from vitrina.views import HistoryMixin, PlanMixin, HistoryView
from copy import deepcopy

RELATED_OBJECT_TYPE = Model | Property | Base | EnumItem | Enum | Param | ParamItem

EXCLUDED_COLS = ["_type", "_revision", "_base"]

FORMATS = {
    "csv": "CSV",
    "json": "JSON",
    "rdf": "RDF",
}


class StructureMixin:
    structure_url = None
    data_url = None
    api_url = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "structure_url": self.get_structure_url(),
                "data_url": self.get_data_url(),
                "api_url": self.get_api_url(),
            }
        )
        return context

    def get_structure_url(self):
        return self.structure_url

    def get_data_url(self):
        return self.data_url

    def get_api_url(self):
        return self.api_url


class DatasetStructureMixin(StructureMixin):
    dataset: Dataset
    models: List[Model]
    can_manage_structure: bool

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        subclass = self.dataset.subclass
        self.can_manage_structure = has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.STRUCTURE,
            Dataset,
            self.dataset,
        )
        version_id = kwargs.get("version_id")
        if version_id is not None:
            self.metadata_version = get_object_or_404(
                _Version,
                pk=version_id,
                dataset=self.dataset,
            )
        else:
            self.metadata_version = None

        allowed_visibilities = get_allowed_visibilities(self.request.user, self.dataset, Action.VIEW)
        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.dataset, metadata_version=self.metadata_version)
                .filter(Q(metadata__visibility__in=allowed_visibilities) | Q(metadata__visibility__isnull=True))
                .order_by("metadata__name")
            )
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.dataset, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(Q(metadata__visibility__in=allowed_visibilities) | Q(metadata__visibility__isnull=True))
                .order_by("metadata__name")
            )
        return super().dispatch(request, *args, **kwargs)

    def get_structure_url(self):
        if self.metadata_version:
            return reverse(
                "dataset-structure",
                kwargs={"pk": self.dataset.pk, "version_id": self.metadata_version.pk},
            )
        else:
            return reverse(
                "dataset-structure-no-version",
                kwargs={
                    "pk": self.dataset.pk,
                },
            )

    def get_data_url(self):
        if self.models and self.models[0].name:
            return reverse(
                "model-data",
                kwargs={
                    "pk": self.dataset.pk,
                    "model": self.models[0].name,
                    "version_id": self.models[0].metadata_version.pk,
                },
            )
        return None

    def get_api_url(self):
        return self.models[0].get_api_url() if self.models else None


class DatasetStructureView(
    DatasetBreadcrumbsMixin, PermissionRequiredMixin, HistoryMixin, StructureMixin, PlanMixin, TemplateView
):
    template_name = "vitrina/structure/dataset_structure.html"
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-structure-history"
    plan_url_name = "dataset-plans"
    breadcrumb_title = _("Struktūra")

    object: Dataset
    models: List[Model]
    can_manage_structure: bool

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        subclass = self.object.subclass
        self.can_manage_structure = has_perm(
            self.request.user,
            Action.INFORMATION_SYSTEM_UPDATE if subclass.is_information_system else Action.STRUCTURE,
            Dataset,
            self.object,
        )
        version_id = kwargs.get("version_id")
        if version_id is not None:
            self.metadata_version = get_object_or_404(
                _Version,
                pk=version_id,
                dataset=self.object,
            )
        else:
            self.metadata_version = _Version.objects.filter(dataset=self.object).last()
            if self.metadata_version:
                return redirect(
                    "dataset-structure",
                    pk=self.object.pk,
                    version_id=self.metadata_version.pk,
                )

        if self.metadata_version:
            self.breadcrumb_title = (
                self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
            )

        allowed_visibilities = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        self.models = Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .filter(Q(metadata__visibility__in=allowed_visibilities) | Q(metadata__visibility__isnull=True))
                .order_by("metadata__name")
            )
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(
                    dataset=self.object,
                    access__gte=Metadata.PUBLIC,
                    metadata_version=self.metadata_version,
                )
                .filter(Q(metadata__visibility__in=allowed_visibilities) | Q(metadata__visibility__isnull=True))
                .order_by("metadata__name")
            )

        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        structure = dataset.current_structure
        context["publish_button"] = flag_enabled("publish_button", request=self.request)
        context["selected_version"] = self.metadata_version
        context["is_disabled"] = not self.metadata_version.is_draft()
        context["versions"] = _Version.objects.filter(dataset=dataset).order_by("version")
        context["errors"] = []
        context["manifest"] = None
        context["structure"] = structure
        context["dataset"] = dataset
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context["can_manage_structure"] = self.can_manage_structure
        context["models"] = self.models
        context["version"] = dataset.dataset_version.filter(deployed__isnull=False).order_by("-deployed").first()
        context["version_id"] = self.metadata_version.pk if self.metadata_version else None
        return context

    def get_structure_url(self):
        if self.metadata_version:
            return reverse(
                "dataset-structure",
                kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk},
            )
        else:
            return reverse(
                "dataset-structure-no-version",
                kwargs={
                    "pk": self.object.pk,
                },
            )

    def get_data_url(self):
        if self.models and self.models[0].name:
            return reverse(
                "model-data",
                kwargs={
                    "pk": self.kwargs.get("pk"),
                    "model": self.models[0].name,
                    "version_id": self.models[0].metadata_version.pk,
                },
            )
        return None

    def get_api_url(self):
        return self.models[0].get_api_url() if self.models else None


class ModelStructureView(
    DatasetBreadcrumbsMixin, HistoryMixin, StructureMixin, PlanMixin, PermissionRequiredMixin, TemplateView
):
    template_name = "vitrina/structure/model_structure.html"
    detail_url_name = "dataset-detail"
    history_url_name = "model-history"
    plan_url_name = "dataset-plans"

    object: Dataset
    model: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object) and self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))

        version_id = kwargs.get("version_id")
        if version_id is not None:
            self.metadata_version = get_object_or_404(
                _Version,
                pk=version_id,
                dataset=self.object,
            )
        else:
            self.metadata_version = None

        model_name = kwargs.get("model")
        self.model = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model:
            raise Http404("No Model matches the given query.")
        allowed_structure_visibilities = get_allowed_visibilities(
            self.request.user, self.object, Action.STRUCTURE, model_class=Model
        )
        self.can_manage_structure = has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object) and (
            self.model.visibility in allowed_structure_visibilities
        )
        allowed_model_visibilities = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_prop_visibilities = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        model_visibility_filter = Q(metadata__visibility__in=allowed_model_visibilities) | Q(
            metadata__visibility__isnull=True
        )
        prop_visibility_filter = Q(metadata__visibility__in=allowed_prop_visibilities) | Q(
            metadata__visibility__isnull=True
        )
        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .filter(model_visibility_filter)
                .order_by("metadata__name")
            )
            self.props = self.model.get_given_props().filter(prop_visibility_filter).order_by("metadata__name")
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(model_visibility_filter)
                .order_by("metadata__name")
            )
            self.props = (
                self.model.get_given_props()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(prop_visibility_filter)
            )
        return super().dispatch(request, *args, **kwargs)

    def get_breadcrumbs(self) -> List[Crumb]:
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )
        crumbs = self.dataset_hierarchy(self.object, include_home=True, make_current=False)
        crumbs.append(
            Crumb(
                title=structure_title,
                url=reverse("dataset-structure", kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk}),
            )
        )
        crumbs.append(Crumb(title=self.model.title or self.model.name, url=None, is_current=True))
        return crumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.object
        context["version_id"] = self.metadata_version.pk
        context["model"] = self.model
        context["object"] = self.model
        context["models"] = self.models
        context["props"] = self.props
        context["prop_dict"] = {prop.name: prop for prop in self.props}
        allowed_visibilities_property = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        visibility_filter = Q(metadata__visibility__in=allowed_visibilities_property) | Q(
            metadata__visibility__isnull=True
        )
        if self.can_manage_structure:
            context["props_without_base"] = self.model.get_props_excluding_base().filter(visibility_filter)
        else:
            context["props_without_base"] = (
                self.model.get_props_excluding_base()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(visibility_filter)
            )
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context["can_manage_structure"] = self.can_manage_structure
        context["is_disabled"] = self.metadata_version is not None and not self.metadata_version.is_draft()
        context["base_props"] = self.model.get_base_props()
        context["params"] = self.model.params.all().order_by("name")
        context["page_title"] = build_page_title_context(
            dataset=self.object,
            model=self.model,
            language_code=self.request.LANGUAGE_CODE,
        )
        return context

    def get_structure_url(self):
        return reverse(
            "dataset-structure", kwargs={"pk": self.kwargs.get("pk"), "version_id": self.metadata_version.pk}
        )

    def get_data_url(self):
        if self.model.name:
            return reverse(
                "model-data",
                kwargs={
                    "pk": self.object.pk,
                    "model": self.model.name,
                    "version_id": self.metadata_version.pk,
                },
            )
        return None

    def get_api_url(self):
        return self.model.get_api_url()

    def get_history_url(self):
        if self.model.name:
            return reverse(
                self.history_url_name,
                kwargs={
                    "pk": self.object.pk,
                    "version_id": self.metadata_version.pk,
                    "model": self.model.name,
                },
            )
        return None


WGS84 = 4326


async def get_property_data(request, *args, **kwargs):
    model = kwargs.get("model", "").replace("-", "/")
    prop = kwargs.get("prop", "")
    data = await get_data_from_spinta_async(model, f":summary/{prop}")
    return JsonResponse(data)


class PropertyGraphView(PermissionRequiredMixin, View):
    template_name = "vitrina/structure/property_graph.html"

    object: Dataset
    model: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    object: Dataset
    model: Model
    property: Property
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return self.property in self.props

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        model_name = kwargs.get("model")
        self.model = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object)
            .first()
        )
        if not self.model:
            raise Http404("No Model matches the given query.")
        prop_name = kwargs.get("prop")
        self.property = get_object_or_404(Property, model=self.model, metadata__name=prop_name)
        allowed_visibilities_model = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_visibilities_property = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        allowed_visibilities_structure_model = get_allowed_visibilities(
            self.request.user, self.object, Action.STRUCTURE
        )
        self.can_manage_structure = (
            has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
            and self.model.visibility in allowed_visibilities_structure_model
        )
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibilities_model) | Q(
            metadata__visibility__isnull=True
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_visibilities_property) | Q(
            metadata__visibility__isnull=True
        )
        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object).filter(visibility_filter_model).order_by("metadata__name")
            )
            self.props = self.model.get_given_props().filter(visibility_filter_property)
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = (
                self.model.get_given_props()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(visibility_filter_property)
            )

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        context = {}
        data = json.loads(request.POST.get("data", ""))
        context["errors"] = data.get("errors", [])
        data = data.get("_data", [])
        metadata = self.property.metadata.first()
        if metadata:
            prop_type = metadata.type
            if data:
                if "count" in data[0]:
                    data = sorted(data, key=lambda x: x["count"], reverse=True)
                context["data"] = data

                if prop_type == "geometry":
                    transformed_data = []
                    context["graph_type"] = "map"
                    srid = get_srid(metadata.type_args)
                    if len(data) > 0:
                        for item in data:
                            centroid = loads(item.get("centroid"))
                            x = centroid.x
                            y = centroid.y
                            if srid != WGS84:
                                x, y = transform_coordinates(centroid.x, centroid.y, srid, WGS84)
                            item["centroid"] = [x, y]
                            transformed_data.append(item)
                    context["data"] = transformed_data
                    context["source_srid"] = srid
                    context["target_srid"] = WGS84
                elif prop_type in ["boolean", "ref"] or (
                    prop_type in ["string", "integer"] and self.property.enums.exists()
                ):
                    if len(data) > 0:
                        max_count = max([item["count"] for item in data])
                    else:
                        max_count = 0
                    context["max_count"] = max_count
                    context["graph_type"] = "horizontal"
                else:
                    x_values = [item["bin"] for item in data]
                    y_values = [item["count"] for item in data]
                    context["x_values"] = x_values
                    context["y_values"] = y_values
                    context["x_title"] = self.property.title or self.property.name
                    context["y_title"] = _("Kiekis")
                    context["graph_type"] = "vertical"

        rendered_template = render_to_string(self.template_name, context)

        return JsonResponse({"rendered_template": rendered_template})


class PropertyStructureView(
    DatasetBreadcrumbsMixin, HistoryMixin, StructureMixin, PlanMixin, PermissionRequiredMixin, TemplateView
):
    template_name = "vitrina/structure/property_structure.html"
    detail_url_name = "dataset-detail"
    history_url_name = "property-history"
    plan_url_name = "dataset-plans"

    object: Dataset
    model: Model
    property: Property
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object) and self.property in self.props

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.object)
        model_name = kwargs.get("model")
        self.model = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model:
            raise Http404("No Model matches the given query.")
        prop_name = kwargs.get("prop")
        self.property = get_object_or_404(
            Property, model=self.model, metadata__name=prop_name, metadata_version=self.metadata_version
        )
        allowed_structure_visibilities = get_allowed_visibilities(self.request.user, self.object, Action.STRUCTURE)
        self.can_manage_structure = (
            has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
            and self.model.visibility in allowed_structure_visibilities
        )
        allowed_visibilities_model = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_visibilities_property = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .filter(Q(metadata__visibility__in=allowed_visibilities_model) | Q(metadata__visibility__isnull=True))
                .order_by("metadata__name")
            )
            self.props = (
                self.model.get_given_props()
                .filter(
                    Q(metadata__visibility__in=allowed_visibilities_property) | Q(metadata__visibility__isnull=True)
                )
                .order_by("metadata__name")
            )
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(Q(metadata__visibility__in=allowed_visibilities_model) | Q(metadata__visibility__isnull=True))
                .order_by("metadata__name")
            )
            self.props = (
                self.model.get_given_props()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(
                    Q(metadata__visibility__in=allowed_visibilities_property) | Q(metadata__visibility__isnull=True)
                )
            )

        return super().dispatch(request, *args, **kwargs)

    def get_breadcrumbs(self) -> List[Crumb]:
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )

        crumbs = self.dataset_hierarchy(self.object, include_home=True, make_current=False)
        crumbs.append(
            Crumb(
                title=structure_title,
                url=reverse("dataset-structure", kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk}),
            )
        )
        crumbs.append(
            Crumb(
                title=self.model.title or self.model.name,
                url=reverse(
                    "model-structure",
                    kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
                ),
            )
        )
        crumbs.append(Crumb(title=self.property.title or self.property.name, url=None, is_current=True))
        return crumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.object
        context["version_id"] = self.metadata_version
        context["model"] = self.model
        context["models"] = self.models
        context["prop"] = self.property
        context["props"] = self.props
        context["show_props"] = True
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context["can_manage_structure"] = self.can_manage_structure
        context["is_disabled"] = self.metadata_version is not None and not self.metadata_version.is_draft()

        allowed_enum_visibilities = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Enum
        )

        filtered_enums = []
        for enum in self.property.enums.all():
            enum_items = enum.enumitem_set.filter(
                Q(metadata__visibility__in=allowed_enum_visibilities) | Q(metadata__visibility__isnull=True)
            )
            if enum_items.exists():
                enum.filtered_items = enum_items
                filtered_enums.append(enum)
        self.property.filtered_enums = filtered_enums

        metadata = self.property.metadata.first()
        if metadata and metadata.type:
            type = metadata.type
            if (
                (type == "string" and self.property.enums.exists())
                or (type == "geometry" and get_srid(metadata.type_args))
                or type
                in [
                    "boolean",
                    "integer",
                    "number",
                    "datetime",
                    "date",
                    "time",
                    "money",
                    "ref",
                ]
            ):
                context["has_graph"] = True
        context["page_title"] = build_page_title_context(
            dataset=self.object,
            model=self.model,
            prop=self.property,
            language_code=self.request.LANGUAGE_CODE,
        )
        return context

    def get_structure_url(self):
        return reverse(
            "dataset-structure", kwargs={"pk": self.kwargs.get("pk"), "version_id": self.metadata_version.pk}
        )

    def get_data_url(self):
        if self.model.name:
            return reverse(
                "model-data",
                kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
            )
        return None

    def get_api_url(self):
        return self.model.get_api_url()

    def get_history_url(self):
        if self.model.name and self.property.name:
            return reverse(
                self.history_url_name,
                kwargs={
                    "pk": self.object.pk,
                    "model": self.model.name,
                    "prop": self.property.name,
                    "version_id": self.metadata_version.pk,
                },
            )
        return None


async def get_model_data(request, *args, **kwargs):
    model = kwargs.get("model", "").replace("-", "/")
    query = ["limit(100)"]
    for key, val in request.GET.items():
        if key.startswith("select("):
            select = key
            query.append(select)
        else:
            if val == "":
                query.append(key)
            else:
                tag = f"{key}={val}"
                query.append(tag)

    query = "&".join(query)
    data = await get_data_from_spinta_async(model, query=query)
    return JsonResponse(data)


class ModelDataTableView(PermissionRequiredMixin, View):
    template_name = "vitrina/structure/model_data_table.html"

    object: Dataset
    model: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object) and self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.object)
        model_name = kwargs.get("model")
        self.model = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model:
            raise Http404("No Model matches the given query.")

        allowed_visibilities_model = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_visibilities_property = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        allowed_visibilities_structure_model = get_allowed_visibilities(
            self.request.user, self.object, Action.STRUCTURE
        )
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibilities_model) | Q(
            metadata__visibility__isnull=True
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_visibilities_property) | Q(
            metadata__visibility__isnull=True
        )
        self.can_manage_structure = (
            has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
            and self.model.visibility in allowed_visibilities_structure_model
        )
        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = self.model.get_given_props().filter(visibility_filter_property)
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = (
                self.model.get_given_props()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(visibility_filter_property)
            )

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        context = {"dataset": self.object, "model": self.model, "version_id": self.metadata_version.pk}
        tags = []
        select = "select(*)"
        selected_cols = []
        query = self.request.POST.get("query", "")
        if query:
            query = unquote(query)
            query = parse.urlsplit(query).query.split("&")
            for param in query:
                if "=" in param:
                    key, val = param.split("=", 1)
                else:
                    key, val = param, ""

                if key.startswith("select("):
                    select = key
                    cols = select.replace("select(", "").replace(")", "")
                    selected_cols = cols.split(",")
                    selected_cols = [col.strip() for col in selected_cols]
                else:
                    if val == "":
                        tags.append(key)
                    else:
                        tag = f"{key}={val}"
                        tags.append(tag)

        data = json.loads(request.POST.get("data", ""))
        data_count = 0
        if data.get("errors"):
            context["errors"] = data.get("errors")
        else:
            context["properties"] = {prop.name: prop for prop in self.props}
            all_props = self.model.get_given_props().values_list("metadata__name", flat=True)
            exclude = all_props - context["properties"].keys()
            exclude.update(EXCLUDED_COLS)

            context["data"] = data.get("_data") or []
            data_count = len(context["data"])
            if context["data"]:
                context["headers"] = [col for col in context["data"][0].keys() if col not in exclude]
            elif selected_cols:
                context["headers"] = selected_cols
            else:
                _data = get_data_from_spinta(self.model, query="limit(1)")
                _data = _data.get("_data")
                if _data:
                    context["headers"] = [col for col in _data[0].keys() if col not in exclude]
                else:
                    headers = ["_id"]
                    headers.extend(context["properties"].keys())
                    context["headers"] = headers
            context["excluded_cols"] = exclude
            context["formats"] = FORMATS
            context["tags"] = tags
            context["select"] = select
            context["selected_cols"] = selected_cols or context["headers"]
            context["can_manage"] = context["can_manage"] = self.can_manage_structure = has_perm(
                self.request.user, Action.STRUCTURE, Dataset, self.object
            ) and (self.model.visibility in get_allowed_visibilities(self.request.user, self.object, Action.STRUCTURE))

            context["dataset_id"] = self.object.id
            context["is_dev_features_enabled"] = settings.IS_DEV_FEATURES_ENABLED

        rendered_template = render_to_string(self.template_name, context)

        return JsonResponse({"rendered_template": rendered_template, "data_count": data_count})


async def get_model_data_count(request, *args, **kwargs):
    model = kwargs.get("model", "").replace("-", "/")
    count_query = ["count()"]
    for key, val in request.GET.items():
        if not key.startswith("select(") and not key.startswith("sort("):
            if val == "":
                count_query.append(key)
            else:
                tag = f"{key}={val}"
                count_query.append(tag)

    total_count = 0
    count_query = "&".join(count_query)
    path = f"{model}/?{count_query}"

    if not cache.get(path):
        count_data = await get_data_from_spinta_async(model, query=count_query)
        count_data = count_data.get("_data")
        if count_data and count_data[0].get("count()"):
            total_count = count_data[0].get("count()")

        total_count_saved = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        cache.set(path, total_count, timeout=86400)
        cache.set(path + "_saved", total_count_saved, timeout=86400)
    else:
        total_count = cache.get(path)
        total_count_saved = cache.get(path + "_saved")

    return JsonResponse({"total_count": total_count, "total_count_saved": total_count_saved})


class ModelDataView(
    DatasetBreadcrumbsMixin, HistoryMixin, StructureMixin, PlanMixin, PermissionRequiredMixin, TemplateView
):
    template_name = "vitrina/structure/model_data.html"
    detail_url_name = "dataset-detail"
    history_url_name = "model-history"
    plan_url_name = "dataset-plans"

    object: Dataset
    model: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object) and self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.object)
        model_name = kwargs.get("model")
        self.model = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model:
            raise Http404("No Model matches the given query.")

        allowed_visibilities_model = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_visibilities_property = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        allowed_visibilities_structure_model = get_allowed_visibilities(
            self.request.user, self.object, Action.STRUCTURE
        )
        self.can_manage_structure = (
            has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
            and self.model.visibility in allowed_visibilities_structure_model
        )
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibilities_model) | Q(
            metadata__visibility__isnull=True
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_visibilities_property) | Q(
            metadata__visibility__isnull=True
        )
        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .order_by("metadata__name")
                .filter(visibility_filter_model)
            )
            self.props = self.model.get_given_props().filter(visibility_filter_property)
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = (
                self.model.get_given_props()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(visibility_filter_property)
            )

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        for frm in FORMATS.keys():
            if f"format({frm})" in request.GET:
                query = []
                for key, val in self.request.GET.items():
                    if val == "":
                        query.append(key)
                    else:
                        query.append(f"{key}={val}")
                query = "&".join(query)
                return redirect(f"https://get.data.gov.lt/{self.model}?{query}")
        return super().get(request, *args, **kwargs)

    def get_breadcrumbs(self) -> List[Crumb]:
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )
        crumbs = self.dataset_hierarchy(self.object, include_home=True)
        crumbs.append(
            Crumb(
                title=structure_title,
                url=reverse("dataset-structure", kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk}),
            )
        )
        crumbs.append(
            Crumb(
                title=self.model.title or self.model.name,
                url=reverse(
                    "model-structure",
                    kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
                ),
            )
        )
        crumbs.append(Crumb(title=_("Duomenys"), url=None, is_current=True))
        return crumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_data"] = True
        context["dataset"] = self.object
        context["model"] = self.model
        context["models"] = self.models
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        return context

    def get_structure_url(self):
        if self.model.name:
            return reverse(
                "model-structure",
                kwargs={
                    "pk": self.object.pk,
                    "model": self.model.name,
                    "version_id": self.metadata_version.pk,
                },
            )
        return None

    def get_data_url(self):
        if self.model.name:
            return reverse(
                "model-data",
                kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
            )
        return None

    def get_api_url(self):
        url = self.model.get_api_url()
        if url:
            query = []
            for key, val in self.request.GET.items():
                if val == "":
                    query.append(key)
                else:
                    query.append(f"{key}={val}")
            if query:
                query = "&".join(query)
                url = f"{url}?{query}"
        return url

    def get_history_url(self):
        if self.model.name:
            return reverse(
                self.history_url_name,
                kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
            )
        return None


async def get_object_data(request, *args, **kwargs):
    model = kwargs.get("model", "").replace("-", "/")
    object_uuid = kwargs.get("uuid", "")
    data = await get_data_from_spinta_async(model, uuid=object_uuid)
    return JsonResponse(data)


class ObjectDataTableView(DatasetBreadcrumbsMixin, PermissionRequiredMixin, View):
    template_name = "vitrina/structure/object_data_table.html"

    object: Dataset
    model: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object) and self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.object)
        model_name = kwargs.get("model")
        self.model = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model:
            raise Http404("No Model matches the given query.")

        allowed_visibilities_model = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_visibilities_property = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        allowed_visibilities_structure = get_allowed_visibilities(self.request.user, self.object, Action.STRUCTURE)
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibilities_model) | Q(
            metadata__visibility__isnull=True
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_visibilities_property) | Q(
            metadata__visibility__isnull=True
        )
        self.can_manage_structure = (
            has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
            and self.model.visibility in allowed_visibilities_structure
        )

        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = self.model.get_given_props().filter(visibility_filter_property)
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = (
                self.model.get_given_props()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(visibility_filter_property)
            )

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        context = {
            "request": request,
            "dataset": self.object,
            "model": self.model,
            "version_id": self.metadata_version.pk,
        }
        data = json.loads(request.POST.get("data", ""))
        if data.get("errors"):
            context["errors"] = data.get("errors")
        else:
            context["properties"] = {prop.name: prop for prop in self.props}
            all_props = self.model.get_given_props().values_list("metadata__name", flat=True)
            exclude = all_props - context["properties"].keys()
            exclude.update(EXCLUDED_COLS)

            context["data"] = data
            context["headers"] = [col for col in data.keys()]
            context["excluded_cols"] = exclude

        rendered_template = render_to_string(self.template_name, context)

        return JsonResponse({"rendered_template": rendered_template})


class ObjectDataView(
    DatasetBreadcrumbsMixin, HistoryMixin, StructureMixin, PlanMixin, PermissionRequiredMixin, TemplateView
):
    template_name = "vitrina/structure/object_data.html"
    detail_url_name = "dataset-detail"
    history_url_name = "model-history"
    plan_url_name = "dataset-plans"

    object: Dataset
    model: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object) and self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.object)
        model_name = kwargs.get("model")
        self.model = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model:
            raise Http404("No Model matches the given query.")

        allowed_visibilities_model = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_visibilities_property = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        allowed_visibilities_structure = get_allowed_visibilities(self.request.user, self.object, Action.STRUCTURE)
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibilities_model) | Q(
            metadata__visibility__isnull=True
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_visibilities_property) | Q(
            metadata__visibility__isnull=True
        )
        self.can_manage_structure = (
            has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
            and self.model.visibility in allowed_visibilities_structure
        )
        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = self.model.get_given_props().filter(visibility_filter_property)
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = (
                self.model.get_given_props()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(visibility_filter_property)
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_data"] = True
        context["dataset"] = self.object
        context["model"] = self.model
        context["models"] = self.models
        context["object_id"] = self.kwargs.get("uuid")
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        return context

    def get_structure_url(self):
        if self.model.name:
            return reverse(
                "model-structure",
                kwargs={
                    "pk": self.object.pk,
                    "model": self.model.name,
                    "version_id": self.metadata_version.pk,
                },
            )
        return None

    def get_data_url(self):
        if self.model.name:
            return reverse(
                "model-data",
                kwargs={
                    "pk": self.object.pk,
                    "model": self.model.name,
                    "version_id": self.metadata_version.pk,
                },
            )
        return None

    def get_api_url(self):
        if self.model.name:
            return reverse(
                "getone-api",
                kwargs={
                    "pk": self.object.pk,
                    "model": self.model.name,
                    "uuid": self.kwargs.get("uuid"),
                    "version_id": self.metadata_version.pk,
                },
            )
        return None

    def get_history_url(self):
        if self.model.name:
            return reverse(
                self.history_url_name,
                kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
            )
        return None


class ApiView(DatasetBreadcrumbsMixin, HistoryMixin, StructureMixin, PlanMixin, PermissionRequiredMixin, TemplateView):
    template_name = "vitrina/structure/api.html"
    detail_url_name = "dataset-detail"
    history_url_name = "model-history"
    plan_url_name = "dataset-plans"

    object: Dataset
    model: Model
    models: List[Model]
    can_manage_structure: bool

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.object) and self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.object)
        model_name = kwargs.get("model")
        self.model = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model:
            raise Http404("No Model matches the given query.")

        allowed_visibilities_model = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_visibilities_structure = get_allowed_visibilities(self.request.user, self.object, Action.STRUCTURE)
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibilities_model) | Q(
            metadata__visibility__isnull=True
        )
        self.can_manage_structure = (
            has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
            and self.model.visibility in allowed_visibilities_structure
        )

        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_api"] = True
        context["dataset"] = self.object
        context["model"] = self.model
        context["models"] = self.models
        context["can_view_members"] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )

        query = self.get_query()
        query_params = []
        for key, val in self.request.GET.items():
            if val == "":
                query_params.append(key)
            else:
                query_params.append(f"{key}={val}")
        query_params = "&".join(query_params)
        context["query_params"] = query_params

        url = f"{query}?{query_params}" if query_params else query
        context["tabs"] = {
            "http": {
                "name": "HTTP",
                "query": highlight(url, TextLexer(), HtmlFormatter()),
            },
            "httpie": {
                "name": "HTTPie",
                "query": highlight(
                    'http GET "%s"' % url.replace("\\", r"\\").replace('"', r"\""),
                    TextLexer(),
                    HtmlFormatter(),
                ),
            },
            "curl": {
                "name": "curl",
                "query": highlight(
                    'curl "%s"' % url.replace("\\", r"\\").replace('"', r"\"").replace(" ", "%20"),
                    TextLexer(),
                    HtmlFormatter(),
                ),
            },
        }

        return context

    def get_structure_url(self):
        if self.model.name:
            return reverse(
                "model-structure",
                kwargs={
                    "pk": self.object.pk,
                    "model": self.model.name,
                    "version_id": self.metadata_version.pk,
                },
            )
        return None

    def get_data_url(self):
        query_params = []
        for key, val in self.request.GET.items():
            if val == "":
                query_params.append(key)
            else:
                query_params.append(f"{key}={val}")
        query_params = "&".join(query_params)

        if self.model.name:
            return "%s%s" % (
                reverse(
                    "model-data",
                    kwargs={
                        "pk": self.object.pk,
                        "model": self.model.name,
                        "version_id": self.metadata_version.pk,
                    },
                ),
                f"?{query_params}" if query_params else "",
            )
        return None

    def get_api_url(self):
        return self.model.get_api_url()

    def get_history_url(self):
        if self.model.name:
            return reverse(
                self.history_url_name,
                kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
            )
        return None

    def get_query(self):
        raise NotImplementedError


class GetAllApiView(ApiView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = context["query_params"]
        if query:
            query = f"{query}&limit(1)"
        else:
            query = "limit(1)"
        data = get_data_from_spinta(self.model, query=query)
        context["response"] = highlight(
            json.dumps(data, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name("borland"), noclasses=True),
        )

        if self.model.name:
            uuid = None
            if data.get("_data") and data.get("_data")[0].get("_id"):
                uuid = data.get("_data")[0].get("_id")
            else:
                # Try to get data again without filters
                data = get_data_from_spinta(self.model, query="limit(1)")
                if data.get("_data"):
                    uuid = data.get("_data")[0].get("_id")

            context["actions"] = {
                "getall": "%s%s"
                % (
                    reverse("getall-api", args=[self.object.pk, self.metadata_version.pk, self.model.name]),
                    f"?{context['query_params']}" if context["query_params"] else "",
                ),
                "getone": reverse("getone-api", args=[self.object.pk, self.metadata_version.pk, self.model.name, uuid]),
                "changes": reverse("changes-api", args=[self.object.pk, self.metadata_version.pk, self.model.name]),
            }

        return context

    def get_breadcrumbs(self) -> List[Crumb]:
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )
        crumbs = super().dataset_hierarchy(self.object, include_home=True, make_current=False)
        crumbs.append(
            Crumb(
                title=structure_title,
                url=reverse("dataset-structure", kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk}),
            )
        )
        crumbs.append(
            Crumb(
                title=self.model.title or self.model.name,
                url=reverse(
                    "model-structure",
                    kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
                ),
            )
        )
        crumbs.append(Crumb(title=_("API: visi įrašai"), url=None, is_current=True))
        return crumbs

    def get_query(self):
        return f"{SPINTA_SERVER_URL}/{self.model}"


class GetOneApiView(ApiView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = context["query_params"]
        if self.kwargs.get("uuid") != "None":
            data = get_data_from_spinta(self.model, self.kwargs.get("uuid"), query=query)
        else:
            data = {}
        context["response"] = highlight(
            json.dumps(data, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name("borland"), noclasses=True),
        )

        if self.model.name:
            context["actions"] = {
                "getall": reverse("getall-api", args=[self.object.pk, self.metadata_version.pk, self.model.name]),
                "getone": reverse(
                    "getone-api",
                    args=[self.object.pk, self.metadata_version.pk, self.model.name, self.kwargs.get("uuid")],
                ),
                "changes": reverse("changes-api", args=[self.object.pk, self.metadata_version.pk, self.model.name]),
            }

        return context

    def get_query(self):
        return f"{SPINTA_SERVER_URL}/{self.model}/{self.kwargs.get('uuid')}"

    def get_data_url(self):
        if self.model.name:
            return reverse(
                "object-data",
                kwargs={
                    "pk": self.object.pk,
                    "model": self.model.name,
                    "uuid": self.kwargs.get("uuid"),
                    "version_id": self.metadata_version.pk,
                },
            )
        return None

    def get_breadcrumbs(self) -> List[Crumb]:
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )
        crumbs = super().dataset_hierarchy(self.object, include_home=True, make_current=False)
        crumbs.append(
            Crumb(
                title=structure_title,
                url=reverse("dataset-structure", kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk}),
            )
        )
        crumbs.append(
            Crumb(
                title=self.model.title or self.model.name,
                url=reverse(
                    "model-structure",
                    kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
                ),
            )
        )
        crumbs.append(Crumb(title=_("API: visi įrašai"), url=None, is_current=True))
        return crumbs


class ChangesApiView(ApiView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = context["query_params"]
        if query:
            query = f"{query}&limit(1)"
        else:
            query = "limit(1)"
        data = get_data_from_spinta(self.model, ":changes", query=query)
        context["response"] = highlight(
            json.dumps(data, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name("borland"), noclasses=True),
        )

        if self.model.name:
            uuid = None
            if data.get("_data") and data.get("_data")[0].get("_id"):
                uuid = data.get("_data")[0].get("_id")
            else:
                # Try to get data again without filters
                data = get_data_from_spinta(self.model, query="limit(1)")
                if data.get("_data"):
                    uuid = data.get("_data")[0].get("_id")

            context["actions"] = {
                "getall": reverse("getall-api", args=[self.object.pk, self.metadata_version.pk, self.model.name]),
                "getone": reverse("getone-api", args=[self.object.pk, self.metadata_version.pk, self.model.name, uuid]),
                "changes": reverse("changes-api", args=[self.object.pk, self.metadata_version.pk, self.model.name]),
            }

        return context

    def get_query(self):
        return f"{SPINTA_SERVER_URL}/{self.model}/:changes"

    def get_breadcrumbs(self) -> List[Crumb]:
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )
        crumbs = super().dataset_hierarchy(self.object, include_home=True, make_current=False)
        crumbs.append(
            Crumb(
                title=structure_title,
                url=reverse("dataset-structure", kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk}),
            )
        )
        crumbs.append(
            Crumb(
                title=self.model.title or self.model.name,
                url=reverse(
                    "model-structure",
                    kwargs={"pk": self.object.pk, "version_id": self.metadata_version.pk, "model": self.model.name},
                ),
            )
        )
        crumbs.append(Crumb(title=_("API: visi įrašai"), url=None, is_current=True))
        return crumbs


class DatasetStructureExportView(DatasetStructureMixin, PermissionRequiredMixin, View):
    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def get(self, request, *args, **kwargs):
        version = self.metadata_version or self.dataset.latest_version()
        stream = export_dataset_structure(self.dataset, version=version)

        filename = (
            "dsa_manifest_draft.csv"
            if version.status == VersionStatus.DRAFT
            else f"dsa_manifest_{version.external_version}.csv"
            if version
            else "dsa_manifest.csv"
        )

        response = StreamingHttpResponse(stream, content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response


class DatasetStructureExportOpenAPIView(DatasetStructureMixin, PermissionRequiredMixin, View):
    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def get(self, request, *args, **kwargs):
        version = self.metadata_version or self.dataset.latest_version()
        manifest_stream = _export_dataset_structure_to_stringio(self.dataset, version=version)
        manifest_path = ManifestPath(file=manifest_stream)
        openapi_spec = create_openapi_manifest(manifest_path)

        response = JsonResponse(openapi_spec, json_dumps_params={"indent": 2, "ensure_ascii": False})
        response["Content-Disposition"] = "attachment; filename=manifest.json"
        return response


class EnumCreateView(PermissionRequiredMixin, CreateView):
    model = EnumItem
    form_class = EnumForm
    template_name = "base_form.html"

    dataset: Dataset
    model_obj: Model
    property: Property
    enum: Enum

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.dataset)
        model_name = kwargs.get("model")
        self.model_obj = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.dataset, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model_obj:
            raise Http404("No Model matches the given query.")
        prop_name = kwargs.get("prop")
        self.property = get_object_or_404(
            Property, model=self.model_obj, metadata__name=prop_name, metadata_version=self.metadata_version
        )
        if self.metadata_version and not self.metadata_version.is_draft():
            messages.error(request, _("Negalima kurti naujos reikšmės, kai versijos būsena nėra juodraštis."))
            return redirect(self.property.get_absolute_url())
        self.enum = self.property.enums.first()
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["prop"] = self.property
        return kwargs

    def get_context_data(self, **kwargs):
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )

        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Galimos reikšmės pridėjimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
            reverse("dataset-structure", args=[self.dataset.pk, self.metadata_version.pk]): structure_title,
        }
        if self.model_obj.name:
            url = reverse("model-structure", args=[self.dataset.pk, self.metadata_version.pk, self.model_obj.name])
            context["parent_links"][url] = self.model_obj.title or self.model_obj.name
        if self.model_obj.name and self.property.name:
            url = reverse(
                "property-structure",
                args=[self.dataset.pk, self.metadata_version.pk, self.model_obj.name, self.property.name],
            )
            context["parent_links"][url] = self.property.title or self.property.name
        return context

    def form_valid(self, form):
        self.object: EnumItem = form.save(commit=False)
        self.object.version_id = self.metadata_version.pk
        if self.enum:
            self.object.enum = self.enum
        else:
            self.object.enum = Enum.objects.create(
                content_type=ContentType.objects.get_for_model(Property),
                object_id=self.property.pk,
                name=self.property.name,
                metadata_version_id=self.metadata_version.pk,
            )
        self.object.save()
        value = form.cleaned_data.get("value")
        visibility = form.cleaned_data.get("visibility")
        status = form.cleaned_data.get("status") or Status.objects.filter(is_default=True).first()
        eli = form.cleaned_data.get("eli")
        if metadata := self.property.metadata.first():
            if metadata.type == "string":
                value = f'"{value}"'
        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=self.dataset,
            content_type=ContentType.objects.get_for_model(EnumItem),
            object_id=self.object.pk,
            name=self.object.enum.name,
            type="enum",
            prepare=value,
            visibility=visibility,
            status=status,
            eli=eli,
            prepare_ast=spyna.parse(form.cleaned_data.get("value")),
            source=form.cleaned_data.get("source"),
            access=form.cleaned_data.get("access") or None,
            title=form.cleaned_data.get("title"),
            description=form.cleaned_data.get("description"),
            version=1,
            metadata_version=self.metadata_version,
        )

        # Save history
        self.property.save()

        return redirect(self.property.get_absolute_url())


class EnumUpdateView(PermissionRequiredMixin, UpdateView):
    model = EnumItem
    form_class = EnumForm
    template_name = "base_form.html"
    pk_url_kwarg = "enum_id"

    dataset: Dataset
    model_obj: Model
    property: Property

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.dataset)
        model_name = kwargs.get("model")
        allowed_visibility_model = get_allowed_visibilities(self.request.user, self.dataset, Action.VIEW)
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibility_model) | Q(
            metadata__visibility__isnull=True
        )
        allowed_visibility_property = get_allowed_visibilities(
            self.request.user, self.dataset, Action.VIEW, model_class=Property
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_visibility_property) | Q(
            metadata__visibility__isnull=True
        )
        self.model_obj = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.dataset, metadata_version=self.metadata_version)
            .filter(visibility_filter_model)
            .first()
        )
        if not self.model_obj:
            raise Http404("No Model matches the given query.")
        prop_name = kwargs.get("prop")
        self.property = get_object_or_404(
            Property.objects.filter(visibility_filter_property),
            model=self.model_obj,
            metadata__name=prop_name,
            metadata_version=self.metadata_version,
        )
        if not self.property:
            raise Http404("No Property matches the given query.")
        if self.metadata_version and not self.metadata_version.is_draft():
            messages.error(request, _("Negalima redaguoti reikšmės, kai versijos būsena nėra juodraštis."))
            return redirect(self.property.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if metadata := self.get_object().metadata.first():
            return has_perm(
                self.request.user, Action.STRUCTURE, Dataset, self.dataset
            ) and metadata.visibility in get_allowed_visibilities(
                self.request.user, self.dataset, Action.VIEW, model_class=Enum
            )
        else:
            return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["prop"] = self.property
        return kwargs

    def get_context_data(self, **kwargs):
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Galimos reikšmės redagavimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
            reverse("dataset-structure", args=[self.dataset.pk, self.metadata_version.pk]): structure_title,
        }
        if self.model_obj.name:
            url = reverse("model-structure", args=[self.dataset.pk, self.metadata_version.pk, self.model_obj.name])
            context["parent_links"][url] = self.model_obj.title or self.model_obj.name
        if self.model_obj.name and self.property.name:
            url = reverse(
                "property-structure",
                args=[self.dataset.pk, self.metadata_version.pk, self.model_obj.name, self.property.name],
            )
            context["parent_links"][url] = self.property.title or self.property.name
        return context

    def form_valid(self, form):
        self.object: EnumItem = form.save()
        value = form.cleaned_data.get("value")
        if metadata := self.property.metadata.first():
            if metadata.type == "string":
                value = f'"{value}"'

        old_metadata = self.get_object().metadata.first()

        if metadata := self.object.metadata.first():
            metadata.prepare = value
            metadata.prepare_ast = spyna.parse(form.cleaned_data.get("value"))
            metadata.source = form.cleaned_data.get("source")
            metadata.access = form.cleaned_data.get("access") or None
            metadata.title = form.cleaned_data.get("title")
            metadata.description = form.cleaned_data.get("description")
            metadata.visibility = form.cleaned_data.get("visibility")
            metadata.eli = form.cleaned_data.get("eli")
            metadata.status = form.cleaned_data.get("status")
            metadata.version += 1
            metadata.status = form.cleaned_data.get("status") or form.initial.get("status")

            if latest_version := metadata.metadataversion_set.order_by("-version__created").first():
                latest_version_fields_changed = none_to_string(latest_version.prepare) != none_to_string(
                    metadata.prepare
                ) or none_to_string(latest_version.source) != none_to_string(metadata.source)

                latest_version_status_changed = latest_version.status != metadata.status

                if latest_version_fields_changed or latest_version_status_changed:
                    metadata.draft = True
                else:
                    metadata.draft = False

            if self.should_reset_to_default_status(old_metadata, metadata):
                metadata.status = Status.objects.filter(is_default=True).first()
            metadata.save()
        # Save history
        self.property.save()

        return redirect(self.property.get_absolute_url())

    @staticmethod
    def should_reset_to_default_status(old_object, new_object):
        """Reset status to default if metadata changed but status wasn't explicitly updated."""
        metadata_changed = (
            old_object
            and none_to_string(old_object.prepare) != none_to_string(new_object.prepare)
            or none_to_string(old_object.source) != none_to_string(new_object.source)
        )
        status_unchanged = old_object.status == new_object.status or new_object.status is None

        return metadata_changed and status_unchanged


class EnumDeleteView(PermissionRequiredMixin, DeleteView):
    model = EnumItem
    pk_url_kwarg = "enum_id"
    template_name = "confirm_delete.html"

    dataset: Dataset
    model_obj: Model
    property: Property

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.dataset)
        model_name = kwargs.get("model")
        self.model_obj = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.dataset, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model:
            raise Http404("No Model matches the given query.")
        prop_name = kwargs.get("prop")
        self.property = get_object_or_404(
            Property, model=self.model_obj, metadata__name=prop_name, metadata_version=self.metadata_version
        )
        if self.metadata_version and not self.metadata_version.is_draft():
            messages.error(request, _("Negalima trinti reikšmės, kai versijos būsena nėra juodraštis."))
            return redirect(self.property.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if metadata := self.get_object().metadata.first():
            return has_perm(
                self.request.user, Action.STRUCTURE, Dataset, self.dataset
            ) and metadata.visibility in get_allowed_visibilities(
                self.request.user, self.dataset, Action.VIEW, model_class=Enum
            )
        else:
            return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def get_success_url(self):
        return self.property.get_absolute_url()

    def get_context_data(self, **kwargs):
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )

        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Galimos reikšmės šalinimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
            reverse("dataset-structure", args=[self.dataset.pk, self.metadata_version.pk]): structure_title,
        }
        if self.model_obj.name:
            url = reverse("model-structure", args=[self.dataset.pk, self.metadata_version.pk, self.model_obj.name])
            context["parent_links"][url] = self.model_obj.title or self.model_obj.name
        if self.model_obj.name and self.property.name:
            url = reverse(
                "property-structure",
                args=[self.dataset.pk, self.metadata_version.pk, self.model_obj.name, self.property.name],
            )
            context["parent_links"][url] = self.property.title or self.property.name
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()

        # Save history
        self.property.save()

        return redirect(success_url)


class ModelCreateView(PermissionRequiredMixin, CreateView):
    model = Metadata
    template_name = "vitrina/structure/model_form.html"
    form_class = ModelCreateForm

    dataset: Dataset
    models: List[Model]

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        allowed_visibility_model = get_allowed_visibilities(self.request.user, self.dataset, Action.STRUCTURE)
        visibility_filter = Q(metadata__visibility__in=allowed_visibility_model) | Q(metadata__visibility__isnull=True)

        version_id = kwargs.get("version_id")
        if version_id is not None:
            self.metadata_version = get_object_or_404(
                _Version,
                pk=version_id,
                dataset=self.dataset,
            )
        else:
            self.metadata_version = None

        if self.metadata_version and not self.metadata_version.is_draft():
            messages.error(request, _("Negalima kurti naujo modelio, kai versijos būsena nėra juodraštis."))
            return redirect(self.dataset.get_absolute_url())

        # Filter by version?
        if has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset):
            self.models = (
                Model.objects.filter(dataset=self.dataset, metadata_version=self.metadata_version)
                .filter(visibility_filter)
                .order_by("metadata__name")
            )
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.dataset, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(visibility_filter)
                .order_by("metadata__name")
            )
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)
        if not self.metadata_version:
            latest_version = self.dataset.latest_version()
            version_number = latest_version.version + 1 if latest_version else 1
            new_draft_version = _Version.objects.create(
                dataset=self.dataset, status=VersionStatus.DRAFT, version=version_number
            )
            self.metadata_version = new_draft_version
        distribution = form.cleaned_data.get("distribution")

        model = Model.objects.create(
            dataset=self.dataset,
            is_parameterized=form.cleaned_data.get("is_parameterized", False),
            metadata_version=self.metadata_version,
            distribution=distribution,
        )
        self.object.metadata_version = self.metadata_version
        self.object.object = model
        self.object.dataset = self.dataset
        self.object.uuid = str(uuid.uuid4())
        self.object.version = 1
        self.object.name = get_model_name(self.dataset, self.object.name)
        self.object.level_given = form.cleaned_data.get("level")
        if not self.object.status:
            self.object.status = Status.objects.filter(is_default=True).first()
        if form.cleaned_data.get("uri"):
            self.object.level = 5
        else:
            self.object.level = self.object.level_given
        if self.object.prepare:
            self.object.prepare_ast = spyna.parse(self.object.prepare)
        else:
            self.object.prepare_ast = ""
        self.object.save()

        if base_model := form.cleaned_data.get("base"):
            base = Base.objects.create(model=base_model, metadata_version=self.metadata_version)
            model.base = base
            model.save()

            if base_model.metadata.first() and base_model.metadata.first().uri:
                base_level = 5
            else:
                base_level = form.cleaned_data.get("base_level")
            base_ref = form.cleaned_data.get("base_ref")

            Metadata.objects.create(
                uuid=str(uuid.uuid4()),
                dataset=self.dataset,
                content_type=ContentType.objects.get_for_model(Base),
                object_id=base.pk,
                name=str(base_model),
                version=1,
                level=base_level,
                level_given=form.cleaned_data.get("base_level"),
                prepare_ast="",
                ref=", ".join(base_ref.values_list("metadata__name", flat=True)) if base_ref else "",
                metadata_version=self.metadata_version,
            )

            if base_ref:
                for i, ref_prop in enumerate(base_ref, start=1):
                    PropertyList.objects.create(
                        content_type=ContentType.objects.get_for_model(Base),
                        object_id=base.pk,
                        property=ref_prop,
                        order=i,
                        metadata_version=self.metadata_version,
                    )

        model.update_level()
        self.dataset.update_level()

        return redirect(model.get_absolute_url())

    def get_context_data(self, **kwargs):
        structure_title = (
            self.metadata_version.external_version
            if self.metadata_version and self.metadata_version.external_version
            else _("Juodraštis")
        )
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Modelio pridėjimas")
        if self.metadata_version:
            structure_url = reverse("dataset-structure", args=[self.dataset.pk, self.metadata_version.pk])
        else:
            structure_url = reverse("dataset-structure-no-version", args=[self.dataset.pk])

        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
            structure_url: structure_title,
        }

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.dataset
        kwargs["metadata_version"] = self.metadata_version
        return kwargs


class ModelDeleteView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk, version_id, model):
        dataset = get_object_or_404(Dataset, pk=pk)
        metadata_version = get_object_or_404(_Version, pk=version_id)
        if not has_perm(request.user, Action.STRUCTURE, Dataset, dataset):
            return JsonResponse({"error": "Permission denied"}, status=403)
        if metadata_version and not metadata_version.is_draft():
            return JsonResponse({"error": "Permission denied"}, status=403)
        model_obj = get_object_or_404(
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            ).filter(model_name=model, dataset=dataset, metadata_version=metadata_version)
        )

        model_obj.delete()
        return JsonResponse({"success": True})


class ModelUpdateView(DatasetBreadcrumbsMixin, PermissionRequiredMixin, UpdateView):
    model = Metadata
    template_name = "vitrina/structure/model_form.html"
    form_class = ModelUpdateForm

    dataset: Dataset
    model_obj: Model

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.dataset)
        if self.metadata_version and not self.metadata_version.is_draft():
            messages.error(request, _("Negalima redaguoti modelio, kai versijos būsena nėra juodraštis."))
            return redirect(self.dataset.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        model_name = self.kwargs.get("model")

        allowed_vis = get_allowed_visibilities(self.request.user, self.dataset, Action.STRUCTURE)
        visibility_filter = Q(metadata__visibility__in=allowed_vis) | Q(metadata__visibility__isnull=True)

        self.model_obj = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.dataset, metadata_version=self.metadata_version)
            .filter(visibility_filter)
            .first()
        )
        if not self.model_obj:
            raise Http404("No Model matches the given query.")
        metadata = self.model_obj.metadata.first()
        if not metadata:
            raise Http404("No Model matches the given query.")
        return metadata

    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)
        old_object = self.get_object()
        model = self.object.object
        old_model_distribution = model.distribution
        model.is_parameterized = form.cleaned_data.get("is_parameterized", False)
        model.distribution = form.cleaned_data.get("distribution")
        model.save()

        if old_model_distribution and old_model_distribution != model.distribution:
            old_model_distribution.delete_resource_metadata_if_has_no_models()

        model_ref = form.cleaned_data.get("ref")
        self.object.status = form.cleaned_data.get("status") or form.initial.get("status")
        self.object.version += 1
        self.object.name = get_model_name(self.dataset, self.object.name)
        self.object.level_given = form.cleaned_data.get("level")
        if form.cleaned_data.get("uri"):
            self.object.level = 5
        else:
            self.object.level = self.object.level_given
        if self.object.prepare:
            self.object.prepare_ast = spyna.parse(self.object.prepare)
        else:
            self.object.prepare_ast = ""
        self.object.ref = ", ".join(model_ref.values_list("metadata__name", flat=True)) if model_ref else ""
        self.object.save()

        model.property_list.all().delete()
        if model_ref:
            for i, ref_prop in enumerate(model_ref, start=1):
                PropertyList.objects.create(
                    content_type=ContentType.objects.get_for_model(Model),
                    object_id=model.pk,
                    property=ref_prop,
                    order=i,
                    metadata_version=self.metadata_version,
                )

        if base_model := form.cleaned_data.get("base"):
            if base_model.metadata.first() and base_model.metadata.first().uri:
                base_level = 5
            else:
                base_level = form.cleaned_data.get("base_level")

            if model.base and model.base.model == base_model:
                base = model.base
            else:
                if model.base:
                    model.base.delete()

                base = Base.objects.create(model=base_model, metadata_version=self.metadata_version)
                model.base = base
                model.save()

                Metadata.objects.create(
                    uuid=str(uuid.uuid4()),
                    dataset=self.dataset,
                    content_type=ContentType.objects.get_for_model(Base),
                    object_id=base.pk,
                    name=str(base_model),
                    version=1,
                    level=base_level,
                    level_given=form.cleaned_data.get("base_level"),
                    prepare_ast="",
                    metadata_version=self.metadata_version,
                )

            base_ref = form.cleaned_data.get("base_ref")
            if base_meta := base.metadata.first():
                base_meta.level = base_level
                base_meta.level_given = form.cleaned_data.get("base_level")
                base_meta.version += 1
                base_meta.ref = ", ".join(base_ref.values_list("metadata__name", flat=True)) if base_ref else ""
                base_meta.save()

            base.property_list.all().delete()
            if base_ref:
                for i, ref_prop in enumerate(base_ref, start=1):
                    PropertyList.objects.create(
                        content_type=ContentType.objects.get_for_model(Base),
                        object_id=base.pk,
                        property=ref_prop,
                        order=i,
                        metadata_version=self.metadata_version,
                    )
        elif model.base:
            model.base.delete()

        # if name was changed, need to change related object metadata where updated model is base or ref model
        if "name" in form.changed_data:
            if ref_model_base := model.ref_model_base.all():
                for item in ref_model_base:
                    if metadata := item.metadata.first():
                        metadata.name = str(model)
                        metadata.save()

            if ref_model_properties := model.ref_model_properties.all():
                for item in ref_model_properties:
                    if metadata := item.metadata.first():
                        metadata.ref = str(model)
                        metadata.save()

        model.update_level()
        self.dataset.update_level()

        if latest_version := self.object.metadataversion_set.order_by("-version__created").first():
            latest_version_fields_changed = (
                latest_version.name != self.object.name
                or latest_version.base != object_to_none(model.base)
                or none_to_string(latest_version.ref) != none_to_string(self.object.ref)
                or latest_version.level_given != self.object.level_given
            )

            latest_version_status_changed = latest_version.status != self.object.status

            if latest_version_fields_changed or latest_version_status_changed:
                self.object.draft = True
            else:
                self.object.draft = False

        if self.should_reset_to_default_status(old_object, self.object, form):
            self.object.status = Status.objects.filter(is_default=True).first()
        self.object.save()

        return redirect(model.get_absolute_url())

    def get_breadcrumbs(self) -> List[Crumb]:
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )
        crumbs = self.dataset_hierarchy(self.dataset, include_home=True)
        crumbs.append(
            Crumb(
                title=structure_title,
                url=reverse("dataset-structure", args=[self.dataset.pk, self.metadata_version.pk]),
            )
        )
        crumbs.append(
            Crumb(
                title=self.model_obj.title or self.model_obj.name,
                url=reverse("model-structure", args=[self.dataset.pk, self.metadata_version.pk, self.model_obj.name]),
            )
        )
        crumbs.append(Crumb(title=_("Modelio redagavimas"), url=None, is_current=True))
        return crumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Modelio redagavimas")
        context["page_title"] = build_page_title_context(
            dataset=self.dataset,
            model=self.object.object,
            language_code=self.request.LANGUAGE_CODE,
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.dataset
        kwargs["metadata_version"] = self.metadata_version
        return kwargs

    @staticmethod
    def should_reset_to_default_status(old_object, new_object, form):
        """Reset status to default if metadata changed but status wasn't explicitly updated."""
        metadata_changed = (
            old_object.name != new_object.name
            or old_object.object.base != form.cleaned_data.get("base")
            or none_to_string(old_object.ref) != none_to_string(new_object.ref)
            or old_object.level_given != new_object.level_given
        )

        status_unchanged = old_object.status == new_object.status or new_object.status is None

        return metadata_changed and status_unchanged


class PropertyCreateView(DatasetBreadcrumbsMixin, PermissionRequiredMixin, CreateView):
    model = Metadata
    template_name = "vitrina/structure/property_form.html"
    form_class = PropertyForm

    dataset: Dataset
    model_obj: Model

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.dataset)
        model_name = self.kwargs.get("model")
        allowed_visibility_model = get_allowed_visibilities(self.request.user, self.dataset, Action.STRUCTURE)
        visibility_filter = Q(metadata__visibility__in=allowed_visibility_model) | Q(metadata__visibility__isnull=True)
        self.model_obj = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.dataset, metadata_version=self.metadata_version)
            .filter(visibility_filter)
            .first()
        )
        if not self.model_obj:
            raise Http404("No Model matches the given query.")
        if self.metadata_version and not self.metadata_version.is_draft():
            messages.error(request, _("Negalima kurti naujo duomenų lauko, kai versijos būsena nėra juodraštis."))
            return redirect(self.model_obj.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)
        self.object.metadata_version = self.metadata_version
        prop = Property.objects.create(model=self.model_obj, metadata_version=self.metadata_version)
        self.object.metadata_version = self.metadata_version
        self.object.uuid = str(uuid.uuid4())
        self.object.object = prop
        self.object.dataset = self.dataset
        self.object.version = 1
        self.object.level_given = self.object.level
        if self.object.prepare:
            self.object.prepare_ast = spyna.parse(self.object.prepare)
        else:
            self.object.prepare_ast = ""
        if self.object.type == "ref":
            ref = form.cleaned_data.get("ref")
            if ref and ref.metadata.first():
                self.object.ref = ref.metadata.first().name
                prop.ref_model = ref
                prop.save()
        else:
            self.object.ref = form.cleaned_data.get("ref_others")
        if not self.object.status:
            self.object.status = Status.objects.filter(is_default=True).first()
        self.object.save()

        self.model_obj.update_level()
        self.dataset.update_level()

        return redirect(prop.get_absolute_url())

    def get_breadcrumbs(self) -> List[Crumb]:
        crumbs = self.dataset_hierarchy(dataset=self.dataset)
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )
        crumbs.append(
            Crumb(
                title=structure_title,
                url=reverse("dataset-structure", args=[self.dataset.pk, self.metadata_version.pk]),
            )
        )
        crumbs.append(
            Crumb(
                title=self.model_obj.title or self.model_obj.name,
                url=reverse("model-structure", args=[self.dataset.pk, self.metadata_version.pk, self.model_obj.name]),
            )
        )
        crumbs.append(Crumb(title=_("Duomenų lauko pridėjimas"), url=None, is_current=True))
        return crumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Duomenų lauko pridėjimas")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["model"] = self.model_obj
        return kwargs


class PropertyUpdateView(DatasetBreadcrumbsMixin, PermissionRequiredMixin, UpdateView):
    model = Metadata
    template_name = "vitrina/structure/property_form.html"
    form_class = PropertyForm

    dataset: Dataset
    model_obj: Model
    property: Property

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.dataset)
        model_name = kwargs.get("model")
        allowed_visibility_model = get_allowed_visibilities(self.request.user, self.dataset, Action.VIEW)
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibility_model) | Q(
            metadata__visibility__isnull=True
        )
        allowed_visibility_property = get_allowed_visibilities(
            self.request.user, self.dataset, Action.VIEW, model_class=Property
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_visibility_property) | Q(
            metadata__visibility__isnull=True
        )

        self.model_obj = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.dataset, metadata_version=self.metadata_version)
            .filter(visibility_filter_model)
            .first()
        )
        if not self.model_obj:
            raise Http404("No Model matches the given query.")
        if self.metadata_version and not self.metadata_version.is_draft():
            messages.error(request, _("Negalima redaguoti naujo duomenų lauko, kai versijos būsena nėra juodraštis."))
            return redirect(self.model_obj.get_absolute_url())
        prop_name = kwargs.get("prop")
        self.property = get_object_or_404(
            Property.objects.filter(visibility_filter_property),
            model=self.model_obj,
            metadata__name=prop_name,
            metadata_version=self.metadata_version,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        metadata = self.property.metadata.first()
        if not metadata:
            raise Http404("No Property matches the given query.")
        return metadata

    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)
        old_object = self.get_object()
        prop = self.object.object
        self.object.version += 1
        self.object.level_given = self.object.level
        self.object.status = form.cleaned_data.get("status") or form.initial.get("status")
        if self.object.prepare:
            self.object.prepare_ast = spyna.parse(self.object.prepare)
        else:
            self.object.prepare_ast = ""
        if self.object.type == "ref":
            ref = form.cleaned_data.get("ref")
            if ref and ref.metadata.first():
                self.object.ref = ref.metadata.first().name
                prop.ref_model = ref
        else:
            self.object.ref = form.cleaned_data.get("ref_others")
            if prop.ref_model:
                prop.ref_model = None

        if latest_version := self.object.metadataversion_set.order_by("-version__created").first():
            latest_version_fields_changed = (
                latest_version.name != self.object.name
                or latest_version.type_repr != self.object.type_repr
                or none_to_string(latest_version.ref) != none_to_string(self.object.ref)
                or latest_version.level_given != self.object.level_given
                or latest_version.access != self.object.access
            )
            latest_version_status_unchanged = latest_version.status != self.object.status
            if latest_version_status_unchanged or latest_version_fields_changed:
                self.object.draft = True
            else:
                self.object.draft = False

        if self.should_reset_to_default_status(old_object, self.object, form):
            self.object.status = Status.objects.filter(is_default=True).first()
        self.object.save()

        self.model_obj.update_level()
        self.dataset.update_level()
        prop.save()

        return redirect(prop.get_absolute_url())

    def get_breadcrumbs(self) -> List[Crumb]:
        structure_title = (
            self.metadata_version.external_version if self.metadata_version.external_version else _("Juodraštis")
        )
        crumbs = self.dataset_hierarchy(self.dataset, include_home=True)
        crumbs.append(
            Crumb(
                title=structure_title,
                url=reverse(
                    "dataset-structure", kwargs={"pk": self.dataset.pk, "version_id": self.metadata_version.pk}
                ),
            )
        )
        crumbs.append(
            Crumb(
                title=self.model_obj.title or self.model_obj.name,
                url=reverse(
                    "model-structure",
                    kwargs={
                        "pk": self.dataset.pk,
                        "version_id": self.metadata_version.pk,
                        "model": self.model_obj.name,
                    },
                ),
            )
        )
        prop_url = getattr(self.property, "get_absolute_url", None)
        prop_url = prop_url() if callable(prop_url) else None
        crumbs.append(
            Crumb(
                title=self.property.title or self.property.name,
                url=prop_url,
            )
        )
        crumbs.append(Crumb(title=_("Redaguoti"), url=None, is_current=True))
        return crumbs

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Duomenų lauko redagavimas")
        context["page_title"] = build_page_title_context(
            dataset=self.dataset,
            model=self.object.object,
            prop=self.property,
            language_code=self.request.LANGUAGE_CODE,
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["model"] = self.model_obj
        return kwargs

    @staticmethod
    def should_reset_to_default_status(old_object, new_object, form):
        """Reset status to default if metadata changed but status wasn't explicitly updated."""
        metadata_changed = (
            old_object.name != new_object.name
            or old_object.type_repr != new_object.type_repr
            or none_to_string(old_object.ref) != none_to_string(new_object.ref)
            or old_object.level_given != new_object.level_given
            or old_object.access != new_object.access
        )
        status_unchanged = old_object.status == new_object.status or new_object.status is None

        return metadata_changed and status_unchanged


class CreateBasePropertyView(PermissionRequiredMixin, View):
    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.dataset)
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def get(self, request, *args, **kwargs):
        model = get_object_or_404(Model, pk=kwargs.get("model_id"), metadata_version=self.metadata_version)
        base_prop = get_object_or_404(Property, pk=kwargs.get("prop_id"))

        prop = Property.objects.create(model=model, metadata_version=self.metadata_version)
        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=self.dataset,
            content_type=ContentType.objects.get_for_model(prop),
            object_id=prop.pk,
            version=1,
            type="inherit",
            name=base_prop.name,
            prepare_ast="",
            metadata_version=self.metadata_version,
        )

        model.update_level()

        # Save history
        with create_revision():
            prop.save()
            set_comment(_(f'Pridėtas "{model.name}" modelio bazinis duomenų laukas "{prop.name}".'))
            set_user(request.user)

        return redirect(model.get_absolute_url())


class DeleteBasePropertyView(PermissionRequiredMixin, View):
    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"), dataset=self.dataset)
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, Dataset, self.dataset)

    def get(self, request, *args, **kwargs):
        prop = get_object_or_404(Property, pk=kwargs.get("prop_id"), metadata_version=self.metadata_version)
        model = get_object_or_404(Model, pk=kwargs.get("model_id"), metadata_version=self.metadata_version)
        prop_name = prop.name
        prop.delete()
        model.update_level()

        # Save history
        with create_revision():
            set_comment(_(f'Pašalintas "{model.name}" modelio bazinis duomenų laukas "{prop_name}".'))
            set_user(request.user)

        return redirect(model.get_absolute_url())


class ParamCreateView(PermissionRequiredMixin, CreateView):
    model = Metadata
    form_class = ParamForm
    template_name = "base_form.html"

    dataset: Dataset
    rel_object: Union[Model, DatasetDistribution]

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        content_type = get_object_or_404(ContentType, pk=kwargs.get("content_type_id"))
        self.rel_object = get_object_or_404(content_type.model_class(), pk=kwargs.get("object_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Parametro pridėjimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)

        param, created = Param.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(self.rel_object),
            object_id=self.rel_object.pk,
            name=form.cleaned_data.get("name"),
        )
        param_item = ParamItem.objects.create(param=param)
        self.object.object = param_item
        self.object.dataset = self.dataset
        self.object.uuid = str(uuid.uuid4())
        self.object.version = 1
        self.object.ref = self.object.name
        self.object.prepare_ast = spyna.parse(self.object.prepare)
        self.object.save()

        # Save history
        if isinstance(self.rel_object, Model):
            self.rel_object.save()

        return redirect(self.rel_object.get_absolute_url())


class ParamUpdateView(PermissionRequiredMixin, UpdateView):
    model = Metadata
    form_class = ParamForm
    template_name = "base_form.html"

    dataset: Dataset
    param_item: ParamItem

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.param_item = get_object_or_404(ParamItem, pk=kwargs.get("param_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_object(self, queryset=None):
        metadata = self.param_item.metadata.first()
        if not metadata:
            raise Http404("No Property matches the given query.")
        return metadata

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Parametro redagavimas")
        context["parent_links"] = {
            reverse("home"): _("Pradžia"),
            reverse("dataset-list"): _("Duomenų ištekliai"),
            reverse("dataset-detail", args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)

        param_item = self.object.object
        rel_object = param_item.param.object

        if "name" in form.changed_data:
            if param_item.param.paramitem_set.count() == 1:
                param_item.param.name = self.object.name
                param_item.param.save()
            else:
                param, created = Param.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(rel_object),
                    object_id=rel_object.pk,
                    name=form.cleaned_data.get("name"),
                )
                param_item.param = param
                param_item.save()

        self.object.version += 1
        self.object.ref = self.object.name
        self.object.prepare_ast = spyna.parse(self.object.prepare)
        self.object.save()

        # Save history
        if isinstance(rel_object, Model):
            rel_object.save()

        return redirect(rel_object.get_absolute_url())


class ParamDeleteView(PermissionRequiredMixin, DeleteView):
    model = ParamItem
    pk_url_kwarg = "param_id"

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_success_url(self):
        return self.object.param.object.get_absolute_url()

    def form_valid(self, form: BaseForm) -> HttpResponse:
        self.object = self.get_object()
        rel_object = self.object.param.object
        response = super().form_valid(form)

        # Save history
        if isinstance(rel_object, Model):
            rel_object.save()

        return response


class DatasetStructureHistoryView(StructureMixin, PlanMixin, HistoryView):
    model = Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"
    tabs_template_name = "vitrina/datasets/tabs.html"

    object: Dataset
    models: List[Model]
    can_manage_structure: bool

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        version_id = kwargs.get("version_id")
        if version_id is not None:
            self.metadata_version = get_object_or_404(
                _Version,
                pk=version_id,
                dataset=self.object,
            )
        else:
            self.metadata_version = _Version.objects.filter(dataset=self.object).last()
            if self.metadata_version:
                redirect(
                    "dataset-structure-history",
                    pk=self.object.pk,
                    version_id=self.metadata_version.pk,
                )

        self.can_manage_structure = has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
        allowed_visibilities = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        visibility_filter = Q(metadata__visibility__in=allowed_visibilities) | Q(metadata__visibility__isnull=True)
        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object)
                .filter(visibility_filter, metadata_version=self.metadata_version)
                .order_by("metadata__name")
            )
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(visibility_filter)
                .order_by("metadata__name")
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_version"] = self.metadata_version
        context["versions"] = _Version.objects.filter(dataset=self.object).order_by("version")
        context["dataset"] = self.object
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
        if self.metadata_version and self.metadata_version.external_version:
            last_url = reverse("dataset-structure", args=[self.object.pk, self.metadata_version.pk])
            last_label = self.metadata_version.external_version
        elif self.metadata_version:
            last_url = reverse("dataset-structure", args=[self.object.pk, self.metadata_version.pk])
            last_label = _("Juodraštis")
        else:
            last_url = reverse("dataset-structure-no-version", args=[self.object.pk])
            last_label = _("Struktūra")

        context["parent_links"][last_url] = last_label

        return context

    def get_structure_url(self):
        if self.metadata_version:
            return reverse(
                "dataset-structure", kwargs={"pk": self.kwargs.get("pk"), "version_id": self.metadata_version.pk}
            )
        else:
            return reverse("dataset-structure-no-version", kwargs={"pk": self.kwargs.get("pk")})

    def get_data_url(self):
        if self.models and self.models[0].name and self.metadata_version:
            return reverse(
                "model-data",
                kwargs={
                    "pk": self.kwargs.get("pk"),
                    "model": self.models[0].name,
                    "version_id": self.metadata_version.pk,
                },
            )
        elif self.models and self.models[0].name and not self.metadata_version:
            return reverse(
                "model-data-no-version",
                kwargs={
                    "pk": self.kwargs.get("pk"),
                    "model": self.models[0].name,
                },
            )
        return None

    def get_api_url(self):
        return self.models[0].get_api_url() if self.models else None

    def get_history_objects(self):
        model_ids = self.models.values_list("pk", flat=True)
        allowed_visibilities = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        visibility_filter = Q(metadata__visibility__in=allowed_visibilities) | Q(metadata__visibility__isnull=True)
        if self.can_manage_structure:
            property_ids = (
                Property.objects.filter(model__pk__in=model_ids, given=True)
                .filter(visibility_filter)
                .values_list("pk", flat=True)
            )
        else:
            property_ids = (
                Property.objects.filter(
                    model__pk__in=model_ids,
                    given=True,
                    metadata__access__gte=Metadata.PUBLIC,
                )
                .filter(visibility_filter)
                .values_list("pk", flat=True)
            )

        property_history_objects = Version.objects.get_for_model(Property).filter(object_id__in=list(property_ids))
        model_history_objects = Version.objects.get_for_model(Model).filter(object_id__in=list(model_ids))
        history_objects = property_history_objects | model_history_objects
        return history_objects.order_by("-revision__date_created")


class ModelHistoryView(StructureMixin, PlanMixin, HistoryView):
    model = Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"
    tabs_template_name = "vitrina/datasets/tabs.html"

    object: Dataset
    model_obj: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        permission = super().has_permission()
        return permission and self.model_obj in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"))
        model_name = kwargs.get("model")
        self.model_obj = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model_obj:
            raise Http404("No Model matches the given query.")

        allowed_visibilities_model = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_visibilities_property = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        allowed_visibilities_structure = get_allowed_visibilities(self.request.user, self.object, Action.STRUCTURE)
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibilities_model) | Q(
            metadata__visibility__isnull=True
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_visibilities_property) | Q(
            metadata__visibility__isnull=True
        )
        self.can_manage_structure = (
            has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
            and self.model_obj.visibility in allowed_visibilities_structure
        )

        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = self.model_obj.get_given_props().filter(visibility_filter_property)
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = (
                self.model_obj.get_given_props()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(visibility_filter_property)
            )

        return super().dispatch(request, *args, **kwargs)

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
        if self.metadata_version and self.metadata_version.external_version:
            last_url = reverse("dataset-structure", args=[self.object.pk, self.metadata_version.pk])
            last_label = self.metadata_version.external_version
        elif self.metadata_version:
            last_url = reverse("dataset-structure", args=[self.object.pk, self.metadata_version.pk])
            last_label = _("Juodraštis")
        else:
            last_url = reverse("dataset-structure-no-version", args=[self.object.pk])
            last_label = _("Struktūra")

        context["parent_links"][last_url] = last_label

        if self.model_obj.name:
            context["parent_links"].update(
                {
                    reverse(
                        "model-structure",
                        args=[self.kwargs.get("pk"), self.metadata_version.pk, self.model_obj.name],
                    ): self.model_obj.title or self.model_obj.name
                }
            )
        return context

    def get_structure_url(self):
        if self.model_obj.name:
            return reverse(
                "model-structure",
                kwargs={
                    "pk": self.kwargs.get("pk"),
                    "version_id": self.metadata_version.pk,
                    "model": self.model_obj.name,
                },
            )
        return None

    def get_data_url(self):
        if self.model_obj.name:
            return reverse(
                "model-data",
                kwargs={
                    "pk": self.object.pk,
                    "model": self.model_obj.name,
                    "version_id": self.metadata_version.pk,
                },
            )
        return None

    def get_api_url(self):
        return self.model_obj.get_api_url()

    def get_history_objects(self):
        property_ids = self.props.values_list("pk", flat=True)
        property_history_objects = Version.objects.get_for_model(Property).filter(object_id__in=list(property_ids))
        model_history_objects = Version.objects.get_for_object(self.model_obj)
        history_objects = property_history_objects | model_history_objects
        return history_objects.order_by("-revision__date_created")


class PropertyHistoryView(StructureMixin, PlanMixin, HistoryView):
    model = Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = "dataset-plans"
    tabs_template_name = "vitrina/datasets/tabs.html"

    object: Dataset
    model_obj: Model
    property: Property
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        permission = super().has_permission()
        return permission and self.property in self.props

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"))
        model_name = kwargs.get("model")
        self.model_obj = (
            Model.objects.annotate(
                model_name=Func(
                    F("metadata__name"),
                    Value("/"),
                    Value(-1),
                    function="split_part",
                    output_field=TextField(),
                )
            )
            .filter(model_name=model_name, dataset=self.object, metadata_version=self.metadata_version)
            .first()
        )
        if not self.model_obj:
            raise Http404("No Model matches the given query.")
        prop_name = kwargs.get("prop")
        self.property = get_object_or_404(
            Property, model=self.model_obj, metadata__name=prop_name, metadata_version=self.metadata_version
        )

        allowed_visibilities_model = get_allowed_visibilities(self.request.user, self.object, Action.VIEW)
        allowed_visibilities_property = get_allowed_visibilities(
            self.request.user, self.object, Action.VIEW, model_class=Property
        )
        allowed_visibilities_structure = get_allowed_visibilities(self.request.user, self.object, Action.STRUCTURE)
        visibility_filter_model = Q(metadata__visibility__in=allowed_visibilities_model) | Q(
            metadata__visibility__isnull=True
        )
        visibility_filter_property = Q(metadata__visibility__in=allowed_visibilities_property) | Q(
            metadata__visibility__isnull=True
        )
        self.can_manage_structure = (
            has_perm(self.request.user, Action.STRUCTURE, Dataset, self.object)
            and self.model_obj.visibility in allowed_visibilities_structure
        )

        if self.can_manage_structure:
            self.models = (
                Model.objects.filter(dataset=self.object, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = self.model_obj.get_given_props().filter(visibility_filter_property)
        else:
            self.models = (
                Model.objects.annotate(access=Max("model_properties__metadata__access"))
                .filter(dataset=self.object, access__gte=Metadata.PUBLIC, metadata_version=self.metadata_version)
                .filter(visibility_filter_model)
                .order_by("metadata__name")
            )
            self.props = (
                self.model_obj.get_given_props()
                .filter(metadata__access__gte=Metadata.PUBLIC)
                .filter(visibility_filter_property)
            )

        return super().dispatch(request, *args, **kwargs)

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
        if self.metadata_version and self.metadata_version.external_version:
            last_url = reverse("dataset-structure", args=[self.object.pk, self.metadata_version.pk])
            last_label = self.metadata_version.external_version
        elif self.metadata_version:
            last_url = reverse("dataset-structure", args=[self.object.pk, self.metadata_version.pk])
            last_label = _("Juodraštis")
        else:
            last_url = reverse("dataset-structure-no-version", args=[self.object.pk])
            last_label = _("Struktūra")

        context["parent_links"][last_url] = last_label

        if self.model_obj.name and self.property.name:
            context["parent_links"].update(
                {
                    reverse(
                        "model-structure",
                        args=[self.kwargs.get("pk"), self.metadata_version.pk, self.model_obj.name],
                    ): self.model_obj.title or self.model_obj.name,
                    reverse(
                        "property-structure",
                        kwargs={
                            "pk": self.kwargs.get("pk"),
                            "version_id": self.metadata_version.pk,
                            "model": self.model_obj.name,
                            "prop": self.property.name,
                        },
                    ): self.property.title or self.property.name,
                }
            )
        return context

    def get_structure_url(self):
        if self.model_obj.name and self.property.name:
            return reverse(
                "property-structure",
                kwargs={
                    "pk": self.kwargs.get("pk"),
                    "version_id": self.metadata_version.pk,
                    "model": self.model_obj.name,
                    "prop": self.property.name,
                },
            )
        return None

    def get_data_url(self):
        if self.model_obj.name:
            return reverse(
                "model-data",
                kwargs={"pk": self.object.pk, "model": self.model_obj.name, "version_id": self.metadata_version.pk},
            )
        return None

    def get_api_url(self):
        return self.model_obj.get_api_url()

    def get_history_objects(self):
        return Version.objects.get_for_object(self.property).order_by("-revision__date_created")


async def get_updated_summary(request, *args, **kwargs):
    model = request.GET.get("model")
    prop = request.GET.get("property")
    source_srid = request.GET.get("source_srid")
    target_srid = request.GET.get("target_srid")
    min_lng = request.GET.get("min_lng")
    min_lat = request.GET.get("min_lat")
    max_lng = request.GET.get("max_lng")
    max_lat = request.GET.get("max_lat")

    if source_srid != target_srid:
        min_lat, min_lng = transform_coordinates(min_lat, min_lng, target_srid, source_srid)
        max_lat, max_lng = transform_coordinates(max_lat, max_lng, target_srid, source_srid)

    query = f"bbox({min_lat}, {min_lng}, {max_lat}, {max_lng})"
    data = await get_data_from_spinta_async(model, f":summary/{prop}", query)
    data = data.get("_data", [])

    transformed_data = []
    for item in data:
        centroid = loads(item.get("centroid"))
        x = centroid.x
        y = centroid.y
        if source_srid != target_srid:
            x, y = transform_coordinates(centroid.x, centroid.y, source_srid, target_srid)
        item["centroid"] = [x, y]
        transformed_data.append(item)
    return JsonResponse({"data": transformed_data})


@method_decorator(flag_required("publish_button"), name="dispatch")
class PublishVersionView(PermissionRequiredMixin, CreateView):
    model = _Version
    form_class = PublishForm
    template_name = "vitrina/structure/publish_form.html"

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get("pk"))
        self.metadata_version = get_object_or_404(_Version, pk=kwargs.get("version_id"))
        if self.metadata_version and not self.metadata_version.is_draft():
            messages.error(request, _("Negalima publikuoti versijos, kai versijos būsena nėra juodraštis."))
            return redirect(self.dataset.get_absolute_url())

        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.STRUCTURE, self.dataset)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.dataset
        kwargs["metadata_version"] = self.metadata_version
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        context["metadata_version"] = self.metadata_version
        return context

    def form_valid(self, form: ModelCreateForm) -> HttpResponseRedirect:
        if not self.metadata_version.is_draft():
            form.add_error(None, _("Publikuota versija negali būti publikuota dar kartą."))
            return self.form_invalid(form)
        self.new_version = form.save(commit=False)
        self.new_version.dataset = self.dataset
        self.new_version.status = VersionStatus.PRE_RELEASE

        based_on_version = form.cleaned_data.get("related_version")
        if self.new_version.version_type == "MAJOR":
            max_major = _Version.objects.filter(dataset=self.dataset).aggregate(Max("major"))["major__max"]
            self.new_version.major = max_major + 1 if max_major else 1
            self.new_version.minor = 0
            self.new_version.patch = 0
        elif self.new_version.version_type == "MINOR":
            self.new_version.major = based_on_version.major
            self.new_version.minor = based_on_version.minor + 1
            self.new_version.patch = 0
        elif self.new_version.version_type == "PATCH":
            self.new_version.major = based_on_version.major
            self.new_version.minor = based_on_version.minor
            self.new_version.patch = based_on_version.patch + 1

        self.new_version.external_version = (
            f"{self.new_version.major}.{self.new_version.minor}.{self.new_version.patch}"
        )

        latest_version = self.dataset.dataset_version.order_by("-version").first()
        if latest_version and latest_version.version:
            self.new_version.version = latest_version.version + 1
        else:
            self.new_version.version = 1

        rel_projects = Project.objects.filter(datasets=self.new_version.dataset)
        emails = []
        version_content_type_list = []
        for proj in rel_projects:
            emails.append(proj.user.email)
            version_content_type = ContentType.objects.get_for_model(self.new_version)
            version_content_type_list.append(version_content_type)
            Task.objects.create(
                # FIXME: Maybe task title and describtion should be generated
                #        on display.
                title=(
                    f"Sukurta nauja duomenų rinkinio struktūros versija: {version_content_type}, id: {self.new_version.pk}"
                ),
                description=("Sukurta nauja duomenų rinkinio struktūros versija."),
                content_type=version_content_type,
                object_id=self.new_version.pk,
                user=proj.user,
                status=Task.CREATED,
            )

        url = f"{get_current_domain(self.request)}/datasets/{self.new_version.dataset.pk}/version/{self.new_version.pk}"
        email(
            emails,
            "new-dataset-structure-version",
            "vitrina/structure/emails/new_version.md",
            {
                "dataset": self.new_version.dataset.title,
                "url": url,
            },
        )

        selected_metadata = form.cleaned_data.get("metadata", [])

        metadata_dataset = Metadata.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset), metadata_version=self.metadata_version
        ).first()

        if not metadata_dataset or str(metadata_dataset.pk) not in selected_metadata:
            form.add_error(None, _("Privalote publikuoti duomenų rinkinį."))
            return self.form_invalid(form)

        old_to_new_metadata_object_map = {}
        with transaction.atomic():
            self.new_version.save()

            for meta in selected_metadata:
                if meta := Metadata.objects.filter(pk=meta).first():
                    old_metadata_instance, new_metadata_instance = self.create_metadata_duplicate(meta)

                    if not (
                        related_object_duplication_result := self.create_related_model_duplicate(old_metadata_instance)
                    ):
                        continue
                    old_related_instance, new_related_instance = related_object_duplication_result

                    if hasattr(old_related_instance, "base") and old_related_instance.base:
                        base_pk = old_related_instance.base.pk
                        base_metadata = Metadata.objects.filter(
                            dataset=self.dataset,
                            object_id=base_pk,
                            content_type=ContentType.objects.get_for_model(Base),
                        ).first()
                        if base_metadata:
                            old_base_metadata_instance, new_base_metadata_instance = self.create_metadata_duplicate(
                                base_metadata
                            )
                            old_base_related_instance, new_base_related_instance = self.create_related_model_duplicate(
                                old_base_metadata_instance
                            )
                            new_base_metadata_instance.object = new_base_related_instance
                            new_base_metadata_instance.save()
                            old_to_new_metadata_object_map[old_base_related_instance] = new_base_related_instance

                    new_metadata_instance.object = new_related_instance
                    new_metadata_instance.save()

                    old_to_new_metadata_object_map[old_related_instance] = new_related_instance

                    # TODO: remove and calculate diff by using metadata table
                    MetadataVersion.objects.create(
                        metadata=new_metadata_instance,
                        version=self.new_version,
                        name=new_metadata_instance.name if new_metadata_instance.name else None,
                        type=new_metadata_instance.type if new_metadata_instance.type else None,
                        required=new_metadata_instance.required,
                        unique=new_metadata_instance.unique,
                        type_args=new_metadata_instance.type_args if new_metadata_instance.type_args else None,
                        ref=new_metadata_instance.ref if new_metadata_instance.ref else None,
                        source=new_metadata_instance.source if new_metadata_instance.source else None,
                        prepare=new_metadata_instance.prepare if new_metadata_instance.prepare else None,
                        level_given=new_metadata_instance.level_given,
                        access=new_metadata_instance.access,
                        base=new_metadata_instance.object.base
                        if isinstance(new_metadata_instance.object, Model)
                        else None,
                        status=new_metadata_instance.status if new_metadata_instance.status else None,
                    )

            already_created_fields = old_to_new_metadata_object_map
            for old_related_instance, new_related_instance in list(old_to_new_metadata_object_map.items()):
                try:
                    already_created_fields = self.duplicate_foreign_key_relationships(
                        new_related_instance, already_created_fields
                    )
                except ValidationError as e:
                    transaction.set_rollback(True)
                    form.add_error(None, e.message)
                    return self.form_invalid(form)

        version_pk = self.new_version.pk if self.new_version else self.metadata_version.pk
        return redirect(reverse("dataset-structure", args=[self.dataset.pk, version_pk]))

    def create_related_model_duplicate(self, old_metadata_instance: Metadata) -> tuple | None:
        if isinstance(old_metadata_instance.object, Dataset):
            return None
        old_related_instance = old_metadata_instance.object
        new_related_instance = deepcopy(old_related_instance)
        new_related_instance.pk = None
        new_related_instance.metadata_version = self.new_version
        new_related_instance.save()

        if isinstance(old_related_instance, DatasetDistribution):
            for translation in old_related_instance.translations.all():
                lang = translation.language_code
                title = getattr(translation, "title", "") or ""
                description = getattr(translation, "description", "") or ""
                conditions = getattr(translation, "conditions", "") or ""

                if hasattr(new_related_instance, "has_translation") and new_related_instance.has_translation(lang):
                    new_related_instance.set_current_language(lang)
                    if hasattr(new_related_instance, "title"):
                        new_related_instance.title = title
                    if hasattr(new_related_instance, "description"):
                        new_related_instance.description = description
                    if hasattr(new_related_instance, "conditions"):
                        new_related_instance.conditions = conditions
                    new_related_instance.save()
                else:
                    new_related_instance.create_translation(
                        language_code=lang,
                        title=title,
                        description=description,
                        conditions=conditions,
                    )

        return old_related_instance, new_related_instance

    def create_metadata_duplicate(self, old_metadata_instance: Metadata) -> tuple:
        new_metadata_instance = deepcopy(old_metadata_instance)
        new_metadata_instance.pk = None
        # TODO: column draft can be deprecated after full versioning is completed.
        new_metadata_instance.draft = False
        if old_metadata_instance.status and old_metadata_instance.status.codename == StatusCode.DEVELOP:
            new_metadata_instance.status = self.get_status_completed

        new_metadata_instance.metadata_version = self.new_version
        new_metadata_instance.save()

        return old_metadata_instance, new_metadata_instance

    def duplicate_foreign_key_relationships(
        self, new_related_object: RELATED_OBJECT_TYPE, already_created_fields: dict
    ) -> dict:
        needed_foreign_key_relationships = [
            Base,
            Model,
            Property,
            EnumItem,
            ParamItem,
            DatasetDistribution,
            Enum,
            Param,
            Prefix,
        ]
        for field in new_related_object._meta.get_fields():
            if not self._should_process_foreign_key(field, needed_foreign_key_relationships):
                continue

            deeper_old_related_object = getattr(new_related_object, field.name)
            if deeper_old_related_object:
                self.validate_field_relationships(deeper_old_related_object, new_related_object, already_created_fields)

            # EnumItem and ParamItem have an additional connection to a specific table which has to be checked.
            if isinstance(deeper_old_related_object, (Enum, Param)):
                deeper_new_related_object = deepcopy(deeper_old_related_object)
                deeper_new_related_object.pk = None
                deeper_new_related_object.metadata_version = self.new_version

                if hasattr(deeper_new_related_object, "content_type_id"):
                    if self._should_raise_unpublished_field_error_for_enum_param(
                        deeper_new_related_object, already_created_fields
                    ):
                        error_field_name = (
                            new_related_object.metadata.first().prepare or new_related_object.metadata.first()
                        )
                        error_msg = _(
                            "Laukas {0} turi nuorodą į nepublikuojamą lauką tame pačiame duomenų ištekliuje.".format(
                                error_field_name
                            )
                        )
                        raise ValidationError(error_msg)

                    if isinstance(deeper_old_related_object, (Enum, Param)):
                        deeper_new_related_object.object = already_created_fields[deeper_new_related_object.object]

                deeper_new_related_object.save()

                already_created_fields[deeper_old_related_object] = deeper_new_related_object
                setattr(new_related_object, field.name, deeper_new_related_object)
                new_related_object.save()

            elif deeper_old_related_object and deeper_old_related_object in already_created_fields:
                value_to_set = already_created_fields[deeper_old_related_object]
                setattr(new_related_object, field.name, value_to_set)
                new_related_object.save()

        return already_created_fields

    def _should_process_foreign_key(self, field: object, needed_relationships: list) -> bool:
        return isinstance(field, ForeignKey) and field.related_model in needed_relationships

    def _should_raise_unpublished_field_error_for_enum_param(
        self, enum_param_obj: Union[Enum, Param], already_created_fields: dict
    ) -> bool:
        related_model = type(enum_param_obj.object)
        return (
            related_model in [Property, Model, DatasetDistribution]
            and enum_param_obj.object not in already_created_fields
        )

    def check_if_field_has_same_dataset(self, field: RELATED_OBJECT_TYPE) -> bool:
        return field.metadata_version.dataset == self.dataset

    def check_if_field_has_same_version(self, field: RELATED_OBJECT_TYPE) -> bool:
        return field.metadata_version == self.metadata_version

    def check_if_field_has_published_version(self, field: RELATED_OBJECT_TYPE) -> bool:
        return field.metadata_version.status and field.metadata_version.status != VersionStatus.DRAFT

    def validate_field_relationships(
        self,
        deeper_old_related_object: RELATED_OBJECT_TYPE,
        new_related_object: RELATED_OBJECT_TYPE,
        already_created_fields: dict,
    ) -> None:
        always_valid_fields = [Param, Enum]
        if isinstance(deeper_old_related_object, tuple(always_valid_fields)):
            return None
        same_dataset = self.check_if_field_has_same_dataset(deeper_old_related_object)
        same_version = self.check_if_field_has_same_version(deeper_old_related_object)
        in_created = deeper_old_related_object in already_created_fields
        published = self.check_if_field_has_published_version(deeper_old_related_object)
        error_msg = None
        deeper_name = (
            getattr(deeper_old_related_object, "name", None)
            or getattr(deeper_old_related_object, "title", None)
            or deeper_old_related_object
        )

        new_name = (
            getattr(new_related_object, "name", None)
            or getattr(new_related_object, "title", None)
            or new_related_object
        )

        if same_dataset and not same_version and not published:
            error_msg = _(
                "Laukas {0} turi nuorodą į nepublikuotą lauką {1} tame pačiame duomenų ištekliuje.".format(
                    new_name, deeper_name
                )
            )

        elif same_dataset and same_version and not in_created:
            error_msg = _(
                "Laukas {0} privalo būti publikuojamas, nes laukas {1} turi nuorodą į jį.".format(deeper_name, new_name)
            )

        elif not same_dataset and not published:
            error_msg = _("Laukas {0} turi nuorodą į nepublikuotą lauką kitame duomenų ištekliuje.".format(new_name))

        if error_msg:
            raise ValidationError(error_msg)
        return None

    @cached_property
    def get_status_completed(self) -> Status:
        return get_object_or_404(Status, codename=StatusCode.COMPLETED)


class VersionListView(
    PermissionRequiredMixin,
    HistoryMixin,
    DatasetStructureMixin,
    PlanMixin,
    TemplateView,
):
    template_name = "vitrina/structure/version_list.html"
    context_object_name = "dataset"
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-plans-history"
    plan_url_name = "dataset-plans"

    def has_permission(self):
        dataset = get_object_or_404(Dataset, id=self.kwargs["pk"])
        return has_perm(self.request.user, Action.VIEW, dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get("status", "not_deployed")
        context["dataset"] = self.dataset
        if status == "deployed":
            context["versions"] = (
                self.dataset.dataset_version.filter(deployed__isnull=False)
                .exclude(status=VersionStatus.DRAFT)
                .order_by("version")
            )
        else:
            context["versions"] = (
                self.dataset.dataset_version.filter(deployed__isnull=True)
                .exclude(status=VersionStatus.DRAFT)
                .order_by("version")
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


class VersionDetailView(
    PermissionRequiredMixin,
    HistoryMixin,
    DatasetStructureMixin,
    PlanMixin,
    TemplateView,
):
    template_name = "vitrina/structure/version_detail.html"
    context_object_name = "dataset"
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-plans-history"
    plan_url_name = "dataset-plans"

    version: _Version

    def dispatch(self, request, *args, **kwargs):
        self.version = get_object_or_404(_Version, pk=kwargs.get("version_id"))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.VIEW, self.version.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        context["version"] = self.version
        context["can_view_members"] = has_perm(self.request.user, Action.VIEW, Representative, self.dataset)

        changes = []
        models = []
        props = []
        version_items = {item.metadata.object: item for item in self.version.metadataversion_set.all()}

        if dataset_meta := version_items.get(self.dataset):
            prev_version = (
                dataset_meta.metadata.metadataversion_set.filter(version__created__lt=self.version.created)
                .order_by("-version__created")
                .first()
            )
            if prev_version:
                changes.append(
                    {
                        "title": self.dataset.title,
                        "url": self.dataset.get_absolute_url(),
                        "new": False,
                        "changed_attrs": [
                            {
                                "attr": "name",
                                "value_before": prev_version.name,
                                "value_after": dataset_meta.name,
                            }
                        ],
                        "class": "dataset_meta",
                    }
                )
            else:
                changes.append(
                    {
                        "title": self.dataset.title,
                        "url": self.dataset.get_absolute_url(),
                        "new": True,
                        "changed_attrs": [{"attr": "name", "value_after": dataset_meta.name}],
                        "class": "dataset_metadata",
                    }
                )

        for model in self.dataset.model_set.all():
            if model_meta := version_items.get(model):
                models.append(model)
                prev_version = (
                    model_meta.metadata.metadataversion_set.filter(version__created__lt=self.version.created)
                    .order_by("-version__created")
                    .first()
                )

                changed_attrs = []
                if prev_version:
                    new = False
                    if prev_version.name != model_meta.name:
                        changed_attrs.append(
                            {
                                "attr": "name",
                                "value_before": prev_version.name,
                                "value_after": model_meta.name,
                            }
                        )
                    if prev_version.ref != model_meta.ref:
                        changed_attrs.append(
                            {
                                "attr": "ref",
                                "value_before": prev_version.ref,
                                "value_after": model_meta.ref,
                            }
                        )
                    if prev_version.level_given != model_meta.level_given:
                        changed_attrs.append(
                            {
                                "attr": "level",
                                "value_before": prev_version.level_given,
                                "value_after": model_meta.level_given,
                            }
                        )
                    if prev_version.base != model_meta.base:
                        changed_attrs.append(
                            {
                                "attr": "base",
                                "value_before": prev_version.base.model.name if prev_version.base else None,
                                "value_after": model_meta.base.model.name if model_meta.base else None,
                            }
                        )
                else:
                    new = True
                    changed_attrs.append(
                        {
                            "attr": "name",
                            "value_after": model_meta.name,
                        }
                    )
                    if model_meta.ref:
                        changed_attrs.append(
                            {
                                "attr": "ref",
                                "value_after": model_meta.ref,
                            }
                        )
                    if model_meta.level_given:
                        changed_attrs.append(
                            {
                                "attr": "level",
                                "value_after": model_meta.level_given,
                            }
                        )
                    if model_meta.base:
                        changed_attrs.append(
                            {
                                "attr": "base",
                                "value_after": model_meta.base.model.name,
                            }
                        )
                changes.append(
                    {
                        "title": model.name,
                        "url": model.get_absolute_url(),
                        "new": new,
                        "changed_attrs": changed_attrs,
                        "class": "model_metadata",
                    }
                )

            for prop in model.model_properties.filter(given=True):
                changed_attrs = []

                if prop_meta := version_items.get(prop):
                    props.append(prop)
                    prev_version = (
                        prop_meta.metadata.metadataversion_set.filter(version__created__lt=self.version.created)
                        .order_by("-version__created")
                        .first()
                    )

                    if prop.model not in models:
                        changes.append(
                            {
                                "title": prop.model.name,
                                "url": prop.model.get_absolute_url(),
                                "changed_attrs": [],
                                "class": "model_metadata",
                            }
                        )
                        models.append(prop.model)

                    if prev_version:
                        new = False
                        if prev_version.name != prop_meta.name:
                            changed_attrs.append(
                                {
                                    "attr": "name",
                                    "value_before": prev_version.name,
                                    "value_after": prop_meta.name,
                                }
                            )
                        if prev_version.type_repr != prop_meta.type_repr:
                            changed_attrs.append(
                                {
                                    "attr": "type",
                                    "value_before": prev_version.type_repr,
                                    "value_after": prop_meta.type_repr,
                                }
                            )
                        if prev_version.ref != prop_meta.ref:
                            changed_attrs.append(
                                {
                                    "attr": "ref",
                                    "value_before": prev_version.ref,
                                    "value_after": prop_meta.ref,
                                }
                            )
                        if prev_version.level_given != prop_meta.level_given:
                            changed_attrs.append(
                                {
                                    "attr": "level",
                                    "value_before": prev_version.level_given,
                                    "value_after": prop_meta.level_given,
                                }
                            )
                        if prev_version.access != prop_meta.access:
                            changed_attrs.append(
                                {
                                    "attr": "access",
                                    "value_before": prev_version.get_access_display(),
                                    "value_after": prop_meta.get_access_display(),
                                }
                            )
                    else:
                        new = True
                        changed_attrs.append(
                            {
                                "attr": "name",
                                "value_after": prop_meta.name,
                            }
                        )
                        if prop_meta.type:
                            changed_attrs.append(
                                {
                                    "attr": "type",
                                    "value_after": prop_meta.type_repr,
                                }
                            )
                        if prop_meta.ref:
                            changed_attrs.append(
                                {
                                    "attr": "ref",
                                    "value_after": prop_meta.ref,
                                }
                            )
                        if prop_meta.level_given:
                            changed_attrs.append(
                                {
                                    "attr": "level",
                                    "value_after": prop_meta.level_given,
                                }
                            )
                        if prop_meta.access:
                            changed_attrs.append(
                                {
                                    "attr": "access",
                                    "value_after": prop_meta.get_access_display(),
                                }
                            )
                    changes.append(
                        {
                            "title": prop.name,
                            "url": prop.get_absolute_url(),
                            "new": new,
                            "changed_attrs": changed_attrs,
                            "class": "prop_metadata",
                        }
                    )

                if enum := prop.enums.first():
                    for enum_item in enum.enumitem_set.all():
                        changed_attrs = []

                        if enum_meta := version_items.get(enum_item):
                            prev_version = (
                                enum_meta.metadata.metadataversion_set.filter(version__created__lt=self.version.created)
                                .order_by("-version__created")
                                .first()
                            )

                            if enum.object.model not in models:
                                changes.append(
                                    {
                                        "title": enum.object.model.name,
                                        "url": enum.object.model.get_absolute_url(),
                                        "changed_attrs": [],
                                        "class": "model_metadata",
                                    }
                                )
                                models.append(enum.object.model)
                            if enum.object not in props:
                                changes.append(
                                    {
                                        "title": enum.object.name,
                                        "url": enum.object.get_absolute_url(),
                                        "changed_attrs": [],
                                        "class": "prop_metadata",
                                    }
                                )
                                props.append(enum.object)

                            if prev_version:
                                new = False
                                if prev_version.prepare != enum_meta.prepare:
                                    changed_attrs.append(
                                        {
                                            "attr": "prepare",
                                            "value_before": prev_version.prepare,
                                            "value_after": enum_meta.prepare,
                                        }
                                    )
                                if prev_version.source != enum_meta.source:
                                    changed_attrs.append(
                                        {
                                            "attr": "source",
                                            "value_before": prev_version.source,
                                            "value_after": enum_meta.source,
                                        }
                                    )
                            else:
                                new = True
                                if enum_meta.prepare:
                                    changed_attrs.append(
                                        {
                                            "attr": "prepare",
                                            "value_after": enum_meta.prepare,
                                        }
                                    )
                                if enum_meta.source:
                                    changed_attrs.append(
                                        {
                                            "attr": "source",
                                            "value_after": enum_meta.source,
                                        }
                                    )
                            changes.append(
                                {
                                    "title": enum_item,
                                    "url": prop.get_absolute_url(),
                                    "new": new,
                                    "changed_attrs": changed_attrs,
                                    "class": "enum_metadata",
                                }
                            )

        context["changes"] = changes

        return context

    def get_history_object(self):
        return self.dataset

    def get_detail_object(self):
        return self.dataset

    def get_plan_object(self):
        return self.dataset

    def get_structure_url(self):
        return reverse(
            "version-list",
            kwargs={
                "pk": self.dataset.pk,
            },
        )

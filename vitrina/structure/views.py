import uuid
import json
from gettext import ngettext
from typing import List, Union

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Func, F, Value, TextField, Max
from django.http import Http404, StreamingHttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
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
from reversion.views import RevisionMixin
from shapely.wkt import loads

from vitrina.datasets.models import Dataset
from vitrina.helpers import get_current_domain, prepare_email_by_identifier, send_email_with_logging
from vitrina.orgs.models import Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project
from vitrina.resources.models import DatasetDistribution
from vitrina.structure import spyna
from vitrina.structure.forms import EnumForm, ModelCreateForm, ModelUpdateForm, PropertyForm, ParamForm, VersionForm
from vitrina.structure.models import Model, Property, Metadata, EnumItem, Enum, PropertyList, Base, ParamItem, Param, \
    MetadataVersion
from vitrina.structure.models import Version as _Version
from vitrina.structure.services import get_data_from_spinta, export_dataset_structure, get_model_name, get_srid, \
    transform_coordinates
from vitrina.tasks.models import Task
from vitrina.views import HistoryMixin, PlanMixin, HistoryView

EXCLUDED_COLS = ['_type', '_revision', '_base']

FORMATS = {
    'csv': 'CSV',
    'json': 'JSON',
    'rdf': 'RDF',
}


class StructureMixin:
    structure_url = None
    data_url = None
    api_url = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'structure_url': self.get_structure_url(),
            'data_url': self.get_data_url(),
            'api_url': self.get_api_url(),
        })
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
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.dataset).order_by('metadata__name')
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.dataset, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
        return super().dispatch(request, *args, **kwargs)

    def get_structure_url(self):
        return reverse('dataset-structure', kwargs={
            'pk': self.dataset.pk,
        })

    def get_data_url(self):
        if self.models and self.models[0].name:
            return reverse('model-data', kwargs={
                'pk': self.dataset.pk,
                'model': self.models[0].name,
            })
        return None

    def get_api_url(self):
        return self.models[0].get_api_url() if self.models else None


class DatasetStructureView(
    HistoryMixin,
    StructureMixin,
    PlanMixin,
    TemplateView
):
    template_name = 'vitrina/structure/dataset_structure.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-structure-history'
    plan_url_name = 'dataset-plans'

    object: Dataset
    models: List[Model]
    can_manage_structure: bool

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.object).order_by('metadata__name')
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.object, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        structure = dataset.current_structure
        context['errors'] = []
        context['manifest'] = None
        context['structure'] = structure
        context['dataset'] = dataset
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['can_manage_structure'] = self.can_manage_structure
        context['models'] = self.models
        context['version'] = dataset.dataset_version.filter(deployed__isnull=False).order_by('-deployed').first()
        return context

    def get_structure_url(self):
        return reverse('dataset-structure', kwargs={'pk': self.kwargs.get('pk')})

    def get_data_url(self):
        if self.models and self.models[0].name:
            return reverse('model-data', kwargs={
                'pk': self.kwargs.get('pk'),
                'model': self.models[0].name,
            })
        return None

    def get_api_url(self):
        return self.models[0].get_api_url() if self.models else None


class ModelStructureView(
    HistoryMixin,
    StructureMixin,
    PlanMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/structure/model_structure.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'model-history'
    plan_url_name = 'dataset-plans'

    object: Dataset
    model: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.object).first()
        if not self.model:
            raise Http404('No Model matches the given query.')

        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.object).order_by('metadata__name')
            self.props = self.model.get_given_props()
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.object, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
            self.props = self.model.get_given_props().filter(metadata__access__gte=Metadata.PUBLIC)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.object
        context['model'] = self.model
        context['object'] = self.model
        context['models'] = self.models
        context['props'] = self.props
        context['prop_dict'] = {
            prop.name: prop
            for prop in self.props
        }
        if self.can_manage_structure:
            context['props_without_base'] = self.model.get_props_excluding_base()
        else:
            context['props_without_base'] = self.model.get_props_excluding_base().filter(
                metadata__access__gte=Metadata.PUBLIC
            )
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['can_manage_structure'] = self.can_manage_structure
        context['base_props'] = self.model.get_base_props()
        context['params'] = self.model.params.all().order_by('name')
        return context

    def get_structure_url(self):
        return reverse('dataset-structure', kwargs={'pk': self.kwargs.get('pk')})

    def get_data_url(self):
        if self.model.name:
            return reverse('model-data', kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
            })
        return None

    def get_api_url(self):
        return self.model.get_api_url()

    def get_history_url(self):
        if self.model.name:
            return reverse(self.history_url_name, kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
            })
        return None


WGS84 = 4326


class PropertyStructureView(
    HistoryMixin,
    StructureMixin,
    PlanMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/structure/property_structure.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'property-history'
    plan_url_name = 'dataset-plans'

    object: Dataset
    model: Model
    property: Property
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return self.property in self.props

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.object).first()
        if not self.model:
            raise Http404('No Model matches the given query.')
        prop_name = kwargs.get('prop')
        self.property = get_object_or_404(Property, model=self.model, metadata__name=prop_name)

        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.object).order_by('metadata__name')
            self.props = self.model.get_given_props()
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.object, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
            self.props = self.model.get_given_props().filter(metadata__access__gte=Metadata.PUBLIC)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.object
        context['model'] = self.model
        context['models'] = self.models
        context['prop'] = self.property
        context['props'] = self.props
        context['show_props'] = True
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['can_manage_structure'] = self.can_manage_structure

        metadata = self.property.metadata.first()
        if metadata and metadata.type:
            type = metadata.type
            if (
                (type == 'string' and self.property.enums.exists()) or
                (type == 'geometry' and get_srid(metadata.type_args)) or
                type in [
                    'boolean',
                    'integer',
                    'number',
                    'datetime',
                    'date',
                    'time',
                    'money',
                    'ref',
                ]
            ):
                data = get_data_from_spinta(self.model, f":summary/{self.property}")
                data = data.get('_data', [])
                if 'count' in data[0]:
                    data = sorted(data, key=lambda x: x['count'], reverse=True)
                context['data'] = data

                if type == 'geometry':
                    transformed_data = []
                    context['graph_type'] = 'map'
                    srid = get_srid(metadata.type_args)
                    if len(data) > 0:
                        for item in data:
                            centroid = loads(item.get('centroid'))
                            x = centroid.x
                            y = centroid.y
                            if srid != WGS84:
                                x, y = transform_coordinates(centroid.x, centroid.y, srid, WGS84)
                            item['centroid'] = [x, y]
                            transformed_data.append(item)
                    context['data'] = transformed_data
                    context['source_srid'] = srid
                    context['target_srid'] = WGS84
                elif (
                        type in ['boolean', 'ref'] or
                        (type in ['string', 'integer'] and self.property.enums.exists())
                ):
                    if len(data) > 0:
                        max_count = max([item['count'] for item in data])
                    else:
                        max_count = 0
                    context['max_count'] = max_count
                    context['graph_type'] = 'horizontal'
                else:
                    x_values = [item['bin'] for item in data]
                    y_values = [item['count'] for item in data]
                    context['x_values'] = x_values
                    context['y_values'] = y_values
                    context['x_title'] = self.property.title or self.property.name
                    context['y_title'] = _("Kiekis")
                    context['graph_type'] = 'vertical'
        return context

    def get_structure_url(self):
        return reverse('dataset-structure', kwargs={'pk': self.kwargs.get('pk')})

    def get_data_url(self):
        if self.model.name:
            return reverse('model-data', kwargs={
                'pk': self.object.pk,
                'model': self.model.name
            })
        return None

    def get_api_url(self):
        return self.model.get_api_url()

    def get_history_url(self):
        if self.model.name and self.property.name:
            return reverse(self.history_url_name, kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
                'prop': self.property.name,
            })
        return None


class ModelDataView(
    HistoryMixin,
    StructureMixin,
    PlanMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/structure/model_data.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'model-history'
    plan_url_name = 'dataset-plans'

    object: Dataset
    model: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.object).first()
        if not self.model:
            raise Http404('No Model matches the given query.')

        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.object).order_by('metadata__name')
            self.props = self.model.get_given_props()
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.object, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
            self.props = self.model.get_given_props().filter(metadata__access__gte=Metadata.PUBLIC)

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        for frm in FORMATS.keys():
            if f"format({frm})" in request.GET:
                query = []
                for key, val in self.request.GET.items():
                    if val == '':
                        query.append(key)
                    else:
                        query.append(f"{key}={val}")
                query = '&'.join(query)
                return redirect(f"https://get.data.gov.lt/{self.model}?{query}")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_data'] = True
        context['dataset'] = self.object
        context['model'] = self.model

        context['models'] = self.models

        tags = []
        select = 'select(*)'
        selected_cols = []
        query = ['limit(100)']
        count_query = ['count()']
        for key, val in self.request.GET.items():
            if key.startswith('select('):
                select = key
                cols = select.replace('select(', '').replace(')', '')
                selected_cols = cols.split(',')
                selected_cols = [col.strip() for col in selected_cols]
                query.append(select)
            else:
                if val == '':
                    tags.append(key)
                    query.append(key)
                    if not key.startswith('sort('):
                        count_query.append(key)
                else:
                    tag = f"{key}={val}"
                    tags.append(tag)
                    query.append(tag)
                    count_query.append(tag)

        query = '&'.join(query)
        data = get_data_from_spinta(self.model, query=query)
        if data.get('errors'):
            context['errors'] = data.get('errors')
        else:
            context['properties'] = {
                prop.name: prop
                for prop in self.props
            }
            all_props = self.model.get_given_props().values_list('metadata__name', flat=True)
            exclude = all_props - context['properties'].keys()
            exclude.update(EXCLUDED_COLS)

            context['data'] = data.get('_data') or []
            if context['data']:
                context['headers'] = [col for col in context['data'][0].keys() if col not in exclude]
            elif selected_cols:
                context['headers'] = selected_cols
            else:
                _data = get_data_from_spinta(self.model, query="limit(1)")
                _data = _data.get('_data')
                if _data:
                    context['headers'] = [col for col in _data[0].keys() if col not in exclude]
                else:
                    headers = ['_id']
                    headers.extend(context['properties'].keys())
                    context['headers'] = headers
            context['excluded_cols'] = exclude
            context['formats'] = FORMATS
            context['tags'] = tags
            context['select'] = select
            context['selected_cols'] = selected_cols or context['headers']

            total_count = 0
            count_query = '&'.join(count_query)
            count_data = get_data_from_spinta(self.model, query=count_query)
            count_data = count_data.get('_data')
            if count_data and count_data[0].get('count()'):
                total_count = count_data[0].get('count()')
            total_count = ngettext(
                f"Rodoma {len(context['data'])} objektas iš {total_count:,}",
                f"Rodoma {len(context['data'])} objektai iš {total_count:,}",
                len(context['data']),
            )
            context['total_count'] = total_count

        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        return context

    def get_structure_url(self):
        if self.model.name:
            return reverse('model-structure', kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
            })
        return None

    def get_data_url(self):
        if self.model.name:
            return reverse('model-data', kwargs={
                'pk': self.object.pk,
                'model': self.model.name
            })
        return None

    def get_api_url(self):
        url = self.model.get_api_url()
        if url:
            query = []
            for key, val in self.request.GET.items():
                if val == '':
                    query.append(key)
                else:
                    query.append(f"{key}={val}")
            if query:
                query = '&'.join(query)
                url = f"{url}?{query}"
        return url

    def get_history_url(self):
        if self.model.name:
            return reverse(self.history_url_name, kwargs={
                'pk': self.object.pk,
                'model': self.model.name
            })
        return None


class ObjectDataView(
    HistoryMixin,
    StructureMixin,
    PlanMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/structure/object_data.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'model-history'
    plan_url_name = 'dataset-plans'

    object: Dataset
    model: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        return self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.object).first()
        if not self.model:
            raise Http404('No Model matches the given query.')

        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.object).order_by('metadata__name')
            self.props = self.model.get_given_props()
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.object, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
            self.props = self.model.get_given_props().filter(metadata__access__gte=Metadata.PUBLIC)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_data'] = True
        context['dataset'] = self.object
        context['model'] = self.model

        context['models'] = self.models

        data = get_data_from_spinta(self.model, uuid=self.kwargs.get('uuid'))
        if data.get('errors'):
            context['errors'] = data.get('errors')
        else:
            context['properties'] = {
                prop.name: prop
                for prop in self.props
            }
            all_props = self.model.get_given_props().values_list('metadata__name', flat=True)
            exclude = all_props - context['properties'].keys()
            exclude.update(EXCLUDED_COLS)

            context['data'] = data
            context['headers'] = [col for col in data.keys()]
            context['excluded_cols'] = exclude
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        return context

    def get_structure_url(self):
        if self.model.name:
            return reverse('model-structure', kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
            })
        return None

    def get_data_url(self):
        if self.model.name:
            return reverse('model-data', kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
            })
        return None

    def get_api_url(self):
        if self.model.name:
            return reverse('getone-api', kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
                'uuid': self.kwargs.get('uuid'),
            })
        return None

    def get_history_url(self):
        if self.model.name:
            return reverse(self.history_url_name, kwargs={
                'pk': self.object.pk,
                'model': self.model.name
            })
        return None


class ApiView(
    HistoryMixin,
    StructureMixin,
    PlanMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/structure/api.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'model-history'
    plan_url_name = 'dataset-plans'

    object: Dataset
    model: Model
    models: List[Model]
    can_manage_structure: bool

    def has_permission(self):
        return self.model in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.object).first()
        if not self.model:
            raise Http404('No Model matches the given query.')

        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.object).order_by('metadata__name')
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.object, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_api'] = True
        context['dataset'] = self.object
        context['model'] = self.model
        context['models'] = self.models
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )

        query = self.get_query()
        query_params = []
        for key, val in self.request.GET.items():
            if val == '':
                query_params.append(key)
            else:
                query_params.append(f"{key}={val}")
        query_params = '&'.join(query_params)
        context['query_params'] = query_params

        url = f"{query}?{query_params}" if query_params else query
        context['tabs'] = {
            'http': {
                'name': 'HTTP',
                'query': highlight(
                    url,
                    TextLexer(), HtmlFormatter()
                )
            },
            'httpie': {
                'name': 'HTTPie',
                'query': highlight(
                    'http GET "%s"' % url.replace("\\", r"\\").replace('"', r'\"'),
                    TextLexer(), HtmlFormatter()
                )
            },
            'curl': {
                'name': 'curl',
                'query': highlight(
                    f'curl "%s"' % url.replace("\\", r"\\").replace('"', r'\"').replace(' ', '%20'),
                    TextLexer(), HtmlFormatter()
                )
            }
        }

        return context

    def get_structure_url(self):
        if self.model.name:
            return reverse('model-structure', kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
            })
        return None

    def get_data_url(self):
        query_params = []
        for key, val in self.request.GET.items():
            if val == '':
                query_params.append(key)
            else:
                query_params.append(f"{key}={val}")
        query_params = '&'.join(query_params)

        if self.model.name:
            return "%s%s" % (reverse('model-data', kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
            }), f"?{query_params}" if query_params else "")
        return None

    def get_api_url(self):
        return self.model.get_api_url()

    def get_history_url(self):
        if self.model.name:
            return reverse(self.history_url_name, kwargs={
                'pk': self.object.pk,
                'model': self.model.name
            })
        return None

    def get_query(self):
        raise NotImplementedError


class GetAllApiView(ApiView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = context['query_params']
        if query:
            query = f"{query}&limit(1)"
        else:
            query = 'limit(1)'
        data = get_data_from_spinta(self.model, query=query)
        context['response'] = highlight(
            json.dumps(data, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name('borland'), noclasses=True)
        )

        if self.model.name:
            uuid = None
            if data.get('_data') and data.get('_data')[0].get('_id'):
                uuid = data.get('_data')[0].get('_id')
            else:
                # Try to get data again without filters
                data = get_data_from_spinta(self.model, query="limit(1)")
                if data.get('_data'):
                    uuid = data.get('_data')[0].get('_id')

            context['actions'] = {
                'getall': "%s%s" % (
                    reverse('getall-api', args=[self.object.pk, self.model.name]),
                    f"?{context['query_params']}" if context['query_params'] else ""
                ),
                'getone': reverse('getone-api', args=[self.object.pk, self.model.name, uuid]),
                'changes': reverse('changes-api', args=[self.object.pk, self.model.name]),
            }

        return context

    def get_query(self):
        return f"https://get.data.gov.lt/{self.model}"


class GetOneApiView(ApiView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = context['query_params']
        if self.kwargs.get('uuid') != 'None':
            data = get_data_from_spinta(self.model, self.kwargs.get('uuid'), query=query)
        else:
            data = {}
        context['response'] = highlight(
            json.dumps(data, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name('borland'), noclasses=True)
        )

        if self.model.name:
            context['actions'] = {
                'getall': reverse('getall-api', args=[self.object.pk, self.model.name]),
                'getone': reverse('getone-api', args=[self.object.pk, self.model.name, self.kwargs.get('uuid')]),
                'changes': reverse('changes-api', args=[self.object.pk, self.model.name]),
            }

        return context

    def get_query(self):
        return f"https://get.data.gov.lt/{self.model}/{self.kwargs.get('uuid')}"

    def get_data_url(self):
        if self.model.name:
            return reverse('object-data', kwargs={
                'pk': self.object.pk,
                'model': self.model.name,
                'uuid': self.kwargs.get('uuid'),
            })
        return None


class ChangesApiView(ApiView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = context['query_params']
        if query:
            query = f"{query}&limit(1)"
        else:
            query = 'limit(1)'
        data = get_data_from_spinta(self.model, ":changes", query=query)
        context['response'] = highlight(
            json.dumps(data, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name('borland'), noclasses=True)
        )

        if self.model.name:
            uuid = None
            if data.get('_data') and data.get('_data')[0].get('_id'):
                uuid = data.get('_data')[0].get('_id')
            else:
                # Try to get data again without filters
                data = get_data_from_spinta(self.model, query="limit(1)")
                if data.get('_data'):
                    uuid = data.get('_data')[0].get('_id')

            context['actions'] = {
                'getall': reverse('getall-api', args=[self.object.pk, self.model.name]),
                'getone': reverse('getone-api', args=[self.object.pk, self.model.name, uuid]),
                'changes': reverse('changes-api', args=[self.object.pk, self.model.name]),
            }

        return context

    def get_query(self):
        return f"https://get.data.gov.lt/{self.model}/:changes"


class DatasetStructureExportView(PermissionRequiredMixin, View):
    def has_permission(self):
        dataset = get_object_or_404(Dataset, pk=self.kwargs.get('pk'))
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            dataset
        )

    def get(self, request, *args, **kwargs):
        dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        stream = export_dataset_structure(dataset)

        response = StreamingHttpResponse(stream, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=manifest.csv'
        return response


class EnumCreateView(RevisionMixin, PermissionRequiredMixin, CreateView):
    model = EnumItem
    form_class = EnumForm
    template_name = 'base_form.html'

    dataset: Dataset
    model_obj: Model
    property: Property
    enum: Enum

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model_obj = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.dataset).first()
        if not self.model_obj:
            raise Http404('No Model matches the given query.')
        prop_name = kwargs.get('prop')
        self.property = get_object_or_404(Property, model=self.model_obj, metadata__name=prop_name)
        self.enum = self.property.enums.first()
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['prop'] = self.property
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Galimos reikšmės pridėjimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
            reverse('dataset-structure', args=[self.dataset.pk]): _('Struktūra'),
        }
        if self.model_obj.name:
            url = reverse('model-structure', args=[self.dataset.pk, self.model_obj.name])
            context['parent_links'][url] = self.model_obj.title or self.model_obj.name
        if self.model_obj.name and self.property.name:
            url = reverse('property-structure', args=[self.dataset.pk, self.model_obj.name, self.property.name])
            context['parent_links'][url] = self.property.title or self.property.name
        return context

    def form_valid(self, form):
        self.object: EnumItem = form.save(commit=False)
        if self.enum:
            self.object.enum = self.enum
        else:
            self.object.enum = Enum.objects.create(
                content_type=ContentType.objects.get_for_model(Property),
                object_id=self.property.pk,
                name=self.property.name
            )
        self.object.save()
        value = form.cleaned_data.get('value')
        if metadata := self.property.metadata.first():
            if metadata.type == 'string':
                value = f'"{value}"'
        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=self.dataset,
            content_type=ContentType.objects.get_for_model(EnumItem),
            object_id=self.object.pk,
            name=self.object.enum.name,
            type='enum',
            prepare=value,
            prepare_ast=spyna.parse(form.cleaned_data.get('value')),
            source=form.cleaned_data.get('source'),
            access=form.cleaned_data.get('access') or None,
            title=form.cleaned_data.get('title'),
            description=form.cleaned_data.get('description'),
            version=1,
        )

        # Save history
        self.property.save()
        set_comment(_(f'Pridėta duomenų lauko "{self.property.name}" reikšmė "{form.cleaned_data.get("value")}".'))

        return redirect(self.property.get_absolute_url())


class EnumUpdateView(RevisionMixin, PermissionRequiredMixin, UpdateView):
    model = EnumItem
    form_class = EnumForm
    template_name = 'base_form.html'
    pk_url_kwarg = 'enum_id'

    dataset: Dataset
    model_obj: Model
    property: Property

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model_obj = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.dataset).first()
        if not self.model_obj:
            raise Http404('No Model matches the given query.')
        prop_name = kwargs.get('prop')
        self.property = get_object_or_404(Property, model=self.model_obj, metadata__name=prop_name)
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['prop'] = self.property
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Galimos reikšmės redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
            reverse('dataset-structure', args=[self.dataset.pk]): _('Struktūra'),
        }
        if self.model_obj.name:
            url = reverse('model-structure', args=[self.dataset.pk, self.model_obj.name])
            context['parent_links'][url] = self.model_obj.title or self.model_obj.name
        if self.model_obj.name and self.property.name:
            url = reverse('property-structure', args=[self.dataset.pk, self.model_obj.name, self.property.name])
            context['parent_links'][url] = self.property.title or self.property.name
        return context

    def form_valid(self, form):
        self.object: EnumItem = form.save()
        value = form.cleaned_data.get('value')
        if metadata := self.property.metadata.first():
            if metadata.type == 'string':
                value = f'"{value}"'
        if metadata := self.object.metadata.first():
            metadata.prepare = value
            metadata.prepare_ast = spyna.parse(form.cleaned_data.get('value'))
            metadata.source = form.cleaned_data.get('source')
            metadata.access = form.cleaned_data.get('access') or None
            metadata.title = form.cleaned_data.get('title')
            metadata.description = form.cleaned_data.get('description')
            metadata.version += 1

            if (
                'value' in form.changed_data or
                'source' in form.changed_data
            ):
                metadata.draft = True

            metadata.save()

        # Save history
        self.property.save()
        set_comment(_(f'Redaguota duomenų lauko "{self.property.name}" reikšmė "{form.cleaned_data.get("value")}".'))

        return redirect(self.property.get_absolute_url())


class EnumDeleteView(PermissionRequiredMixin, DeleteView):
    model = EnumItem
    pk_url_kwarg = 'enum_id'
    template_name = 'confirm_delete.html'

    dataset: Dataset
    model_obj: Model
    property: Property

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model_obj = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.dataset).first()
        if not self.model:
            raise Http404('No Model matches the given query.')
        prop_name = kwargs.get('prop')
        self.property = get_object_or_404(Property, model=self.model_obj, metadata__name=prop_name)
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )

    def get_success_url(self):
        return self.property.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Galimos reikšmės šalinimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
            reverse('dataset-structure', args=[self.dataset.pk]): _('Struktūra'),
        }
        if self.model_obj.name:
            url = reverse('model-structure', args=[self.dataset.pk, self.model_obj.name])
            context['parent_links'][url] = self.model_obj.title or self.model_obj.name
        if self.model_obj.name and self.property.name:
            url = reverse('property-structure', args=[self.dataset.pk, self.model_obj.name, self.property.name])
            context['parent_links'][url] = self.property.title or self.property.name
        return context

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        value = str(self.object).replace('"', "")
        self.object.delete()

        # Save history
        with create_revision():
            self.property.save()
            set_user(request.user)
            set_comment(_(f'Pašalinta duomenų lauko "{self.property.name}" reikšmė "{value}".'))

        return redirect(success_url)


class ModelCreateView(
    PermissionRequiredMixin,
    RevisionMixin,
    CreateView
):
    model = Metadata
    template_name = 'vitrina/structure/model_form.html'
    form_class = ModelCreateForm

    dataset: Dataset
    models: List[Model]

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        if has_perm(
                self.request.user,
                Action.STRUCTURE,
                Dataset,
                self.dataset
        ):
            self.models = Model.objects.filter(dataset=self.dataset).order_by('metadata__name')
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.dataset, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)

        model = Model.objects.create(
            dataset=self.dataset,
            is_parameterized=form.cleaned_data.get('is_parameterized', False)
        )

        self.object.object = model
        self.object.dataset = self.dataset
        self.object.uuid = str(uuid.uuid4())
        self.object.version = 1
        self.object.name = get_model_name(self.dataset, self.object.name)
        self.object.level_given = form.cleaned_data.get('level')
        if form.cleaned_data.get('uri'):
            self.object.level = 5
        else:
            self.object.level = self.object.level_given
        if self.object.prepare:
            self.object.prepare_ast = spyna.parse(self.object.prepare)
        else:
            self.object.prepare_ast = ""
        self.object.save()

        if base_model := form.cleaned_data.get('base'):
            base = Base.objects.create(model=base_model)
            model.base = base
            model.save()

            if base_model.metadata.first() and base_model.metadata.first().uri:
                base_level = 5
            else:
                base_level = form.cleaned_data.get('base_level')
            base_ref = form.cleaned_data.get('base_ref')

            Metadata.objects.create(
                uuid=str(uuid.uuid4()),
                dataset=self.dataset,
                content_type=ContentType.objects.get_for_model(Base),
                object_id=base.pk,
                name=str(base_model),
                version=1,
                level=base_level,
                level_given=form.cleaned_data.get('base_level'),
                prepare_ast='',
                ref=', '.join(base_ref.values_list('metadata__name', flat=True)) if base_ref else ''
            )

            if base_ref:
                for i, ref_prop in enumerate(base_ref, start=1):
                    PropertyList.objects.create(
                        content_type=ContentType.objects.get_for_model(Base),
                        object_id=base.pk,
                        property=ref_prop,
                        order=i
                    )

        model.update_level()
        self.dataset.update_level()

        if form.cleaned_data.get('comment'):
            comment = _(f'Sukurtas "{model.name}" modelis. {form.cleaned_data.get("comment")}')
        else:
            comment = _(f'Sukurtas "{model.name}" modelis.')
        set_comment(comment)
        set_user(self.request.user)

        return redirect(model.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Modelio pridėjimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
            reverse('dataset-structure', args=[self.dataset.pk]): _('Struktūra'),
        }
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dataset'] = self.dataset
        return kwargs


class ModelUpdateView(
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Metadata
    template_name = 'vitrina/structure/model_form.html'
    form_class = ModelUpdateForm

    dataset: Dataset
    model_obj: Model

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        model_name = self.kwargs.get('model')
        self.model_obj = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.dataset).first()
        if not self.model_obj:
            raise Http404('No Model matches the given query.')
        metadata = self.model_obj.metadata.first()
        if not metadata:
            raise Http404('No Model matches the given query.')
        return metadata

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)
        model = self.object.object
        model.is_parameterized = form.cleaned_data.get('is_parameterized', False)
        model.save()
        model_ref = form.cleaned_data.get('ref')

        self.object.version += 1
        self.object.name = get_model_name(self.dataset, self.object.name)
        self.object.level_given = form.cleaned_data.get('level')
        if form.cleaned_data.get('uri'):
            self.object.level = 5
        else:
            self.object.level = self.object.level_given
        if self.object.prepare:
            self.object.prepare_ast = spyna.parse(self.object.prepare)
        else:
            self.object.prepare_ast = ""
        self.object.ref = ', '.join(model_ref.values_list('metadata__name', flat=True)) if model_ref else ''

        if (
            'name' in form.changed_data or
            'base' in form.changed_data or
            'ref' in form.changed_data or
            'level' in form.changed_data
        ):
            self.object.draft = True

        self.object.save()

        model.property_list.all().delete()
        if model_ref:
            for i, ref_prop in enumerate(model_ref, start=1):
                PropertyList.objects.create(
                    content_type=ContentType.objects.get_for_model(Model),
                    object_id=model.pk,
                    property=ref_prop,
                    order=i
                )

        if base_model := form.cleaned_data.get('base'):
            if base_model.metadata.first() and base_model.metadata.first().uri:
                base_level = 5
            else:
                base_level = form.cleaned_data.get('base_level')

            if model.base and model.base.model == base_model:
                base = model.base
            else:
                if model.base:
                    model.base.delete()

                base = Base.objects.create(model=base_model)
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
                    level_given=form.cleaned_data.get('base_level'),
                    prepare_ast=''
                )

            base_ref = form.cleaned_data.get('base_ref')
            if base_meta := base.metadata.first():
                base_meta.level = base_level
                base_meta.level_given = form.cleaned_data.get('base_level')
                base_meta.version += 1
                base_meta.ref = ', '.join(base_ref.values_list('metadata__name', flat=True)) if base_ref else ''
                base_meta.save()

            base.property_list.all().delete()
            if base_ref:
                for i, ref_prop in enumerate(base_ref, start=1):
                    PropertyList.objects.create(
                        content_type=ContentType.objects.get_for_model(Base),
                        object_id=base.pk,
                        property=ref_prop,
                        order=i
                    )
        elif model.base:
            model.base.delete()

        model.update_level()
        self.dataset.update_level()

        if form.cleaned_data.get('comment'):
            comment = _(f'Redaguotas "{model.name}" modelis. {form.cleaned_data.get("comment")}')
        else:
            comment = _(f'Redaguotas "{model.name}" modelis.')
        set_comment(comment)
        set_user(self.request.user)

        return redirect(model.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Modelio redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
            reverse('dataset-structure', args=[self.dataset.pk]): _('Struktūra'),
            reverse('model-structure', args=[self.dataset.pk, self.model_obj.name]):
                self.model_obj.title or self.model_obj.name,
        }
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dataset'] = self.dataset
        return kwargs


class PropertyCreateView(
    PermissionRequiredMixin,
    RevisionMixin,
    CreateView
):
    model = Metadata
    template_name = 'vitrina/structure/property_form.html'
    form_class = PropertyForm

    dataset: Dataset
    model_obj: Model

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = self.kwargs.get('model')
        self.model_obj = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.dataset).first()
        if not self.model_obj:
            raise Http404('No Model matches the given query.')
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)
        prop = Property.objects.create(model=self.model_obj)

        self.object.uuid = str(uuid.uuid4())
        self.object.object = prop
        self.object.dataset = self.dataset
        self.object.version = 1
        self.object.level_given = self.object.level
        if self.object.prepare:
            self.object.prepare_ast = spyna.parse(self.object.prepare)
        else:
            self.object.prepare_ast = ""
        if self.object.type == 'ref':
            ref = form.cleaned_data.get('ref')
            if ref and ref.metadata.first():
                self.object.ref = ref.metadata.first().name
                prop.ref_model = ref
                prop.save()
        else:
            self.object.ref = form.cleaned_data.get('ref_others')
        self.object.save()

        self.model_obj.update_level()
        self.dataset.update_level()

        # Save history
        set_comment(_(f'Pridėtas "{self.model_obj.name}" modelio duomenų laukas "{self.object.name}".'))

        return redirect(prop.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Duomenų lauko pridėjimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
            reverse('dataset-structure', args=[self.dataset.pk]): _('Struktūra'),
        }
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['model'] = self.model_obj
        return kwargs


class PropertyUpdateView(
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Metadata
    template_name = 'vitrina/structure/property_form.html'
    form_class = PropertyForm

    dataset: Dataset
    model_obj: Model
    property: Property

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model_obj = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.dataset).first()
        if not self.model_obj:
            raise Http404('No Model matches the given query.')
        prop_name = kwargs.get('prop')
        self.property = get_object_or_404(Property, model=self.model_obj, metadata__name=prop_name)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        metadata = self.property.metadata.first()
        if not metadata:
            raise Http404('No Property matches the given query.')
        return metadata

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)
        prop = self.object.object

        self.object.version += 1
        self.object.level_given = self.object.level
        if self.object.prepare:
            self.object.prepare_ast = spyna.parse(self.object.prepare)
        else:
            self.object.prepare_ast = ""
        if self.object.type == 'ref':
            ref = form.cleaned_data.get('ref')
            if ref and ref.metadata.first():
                self.object.ref = ref.metadata.first().name
                prop.ref_model = ref
        else:
            self.object.ref = form.cleaned_data.get('ref_others')
            if prop.ref_model:
                prop.ref_model = None

        if (
            'name' in form.changed_data or
            'type' in form.changed_data or
            'ref' in form.changed_data or
            'ref_others' in form.changed_data or
            'level' in form.changed_data or
            'access' in form.changed_data
        ):
            self.object.draft = True
        self.object.save()

        self.model_obj.update_level()
        self.dataset.update_level()

        # Save history
        prop.save()
        set_comment(_(f'Redaguotas "{self.model_obj.name}" modelio duomenų laukas "{self.object.name}".'))

        return redirect(prop.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Duomenų lauko redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
            reverse('dataset-structure', args=[self.dataset.pk]): _('Struktūra'),
            reverse('model-structure', args=[self.dataset.pk, self.model_obj.name]):
                self.model_obj.title or self.model_obj.name,
        }
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['model'] = self.model_obj
        return kwargs


class CreateBasePropertyView(PermissionRequiredMixin, View):
    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )

    def get(self, request, *args, **kwargs):
        model = get_object_or_404(Model, pk=kwargs.get('model_id'))
        base_prop = get_object_or_404(Property, pk=kwargs.get('prop_id'))

        prop = Property.objects.create(model=model)
        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=self.dataset,
            content_type=ContentType.objects.get_for_model(prop),
            object_id=prop.pk,
            version=1,
            type='inherit',
            name=base_prop.name,
            prepare_ast=""
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
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.dataset
        )

    def get(self, request, *args, **kwargs):
        prop = get_object_or_404(Property, pk=kwargs.get('prop_id'))
        model = get_object_or_404(Model, pk=kwargs.get('model_id'))
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
    template_name = 'base_form.html'

    dataset: Dataset
    rel_object: Union[Model, DatasetDistribution]

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        content_type = get_object_or_404(ContentType, pk=kwargs.get('content_type_id'))
        self.rel_object = get_object_or_404(content_type.model_class(), pk=kwargs.get('object_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.UPDATE,
            self.dataset
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Parametro pridėjimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)

        param, created = Param.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(self.rel_object),
            object_id=self.rel_object.pk,
            name=form.cleaned_data.get('name')
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
            with create_revision():
                self.rel_object.save()
                set_comment(_(f'Pridėtas "{self.rel_object.name}" modelio parametras "{self.object.name}".'))
                set_user(self.request.user)

        return redirect(self.rel_object.get_absolute_url())


class ParamUpdateView(PermissionRequiredMixin, UpdateView):
    model = Metadata
    form_class = ParamForm
    template_name = 'base_form.html'

    dataset: Dataset
    param_item: ParamItem

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        self.param_item = get_object_or_404(ParamItem, pk=kwargs.get('param_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.UPDATE,
            self.dataset
        )

    def get_object(self, queryset=None):
        metadata = self.param_item.metadata.first()
        if not metadata:
            raise Http404('No Property matches the given query.')
        return metadata

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Parametro redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def form_valid(self, form):
        self.object: Metadata = form.save(commit=False)

        param_item = self.object.object
        rel_object = param_item.param.object

        if 'name' in form.changed_data:
            if param_item.param.paramitem_set.count() == 1:
                param_item.param.name = self.object.name
                param_item.param.save()
            else:
                param, created = Param.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(rel_object),
                    object_id=rel_object.pk,
                    name=form.cleaned_data.get('name')
                )
                param_item.param = param
                param_item.save()

        self.object.version += 1
        self.object.ref = self.object.name
        self.object.prepare_ast = spyna.parse(self.object.prepare)
        self.object.save()

        # Save history
        if isinstance(rel_object, Model):
            with create_revision():
                rel_object.save()
                set_comment(_(f'Redaguotas "{rel_object.name}" modelio parametras "{self.object.name}".'))
                set_user(self.request.user)

        return redirect(rel_object.get_absolute_url())


class ParamDeleteView(PermissionRequiredMixin, DeleteView):
    model = ParamItem
    pk_url_kwarg = 'param_id'

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.UPDATE,
            self.dataset
        )

    def get_success_url(self):
        return self.object.param.object.get_absolute_url()

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        value = str(self.object)
        rel_object = self.object.param.object
        self.object.delete()

        # Save history
        if isinstance(rel_object, Model):
            with create_revision():
                rel_object.save()
                set_comment(_(f'Pašalintas "{rel_object.name}" modelio parametras "{value}".'))
                set_user(self.request.user)

        return redirect(success_url)


class DatasetStructureHistoryView(
    StructureMixin,
    PlanMixin,
    HistoryView
):
    model = Dataset
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'
    plan_url_name = 'dataset-plans'
    tabs_template_name = 'vitrina/datasets/tabs.html'

    object: Dataset
    models: List[Model]
    can_manage_structure: bool

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.object).order_by('metadata__name')
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.object, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.object.pk]): self.object.title,
            reverse('dataset-structure', args=[self.object.pk]): _("Struktūra"),
        }
        return context

    def get_structure_url(self):
        return reverse('dataset-structure', kwargs={'pk': self.kwargs.get('pk')})

    def get_data_url(self):
        if self.models and self.models[0].name:
            return reverse('model-data', kwargs={
                'pk': self.kwargs.get('pk'),
                'model': self.models[0].name,
            })
        return None

    def get_api_url(self):
        return self.models[0].get_api_url() if self.models else None

    def get_history_objects(self):
        model_ids = self.models.values_list('pk', flat=True)
        if self.can_manage_structure:
            property_ids = Property.objects.filter(
                model__pk__in=model_ids,
                given=True
            ).values_list('pk', flat=True)
        else:
            property_ids = Property.objects.filter(
                model__pk__in=model_ids,
                given=True,
                metadata__access__gte=Metadata.PUBLIC,
            ).values_list('pk', flat=True)

        property_history_objects = Version.objects.get_for_model(Property).filter(object_id__in=list(property_ids))
        model_history_objects = Version.objects.get_for_model(Model).filter(object_id__in=list(model_ids))
        history_objects = property_history_objects | model_history_objects
        return history_objects.order_by('-revision__date_created')


class ModelHistoryView(
    StructureMixin,
    PlanMixin,
    HistoryView
):
    model = Dataset
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'
    plan_url_name = 'dataset-plans'
    tabs_template_name = 'vitrina/datasets/tabs.html'

    object: Dataset
    model_obj: Model
    models: List[Model]
    props: List[Property]
    can_manage_structure: bool

    def has_permission(self):
        permission = super().has_permission()
        return permission and self.model_obj in self.models

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model_obj = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.object).first()
        if not self.model_obj:
            raise Http404('No Model matches the given query.')

        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.object).order_by('metadata__name')
            self.props = self.model_obj.get_given_props()
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.object, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
            self.props = self.model_obj.get_given_props().filter(metadata__access__gte=Metadata.PUBLIC)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.object.pk]): self.object.title,
            reverse('dataset-structure', args=[self.object.pk]): _("Struktūra"),
        }
        if self.model_obj.name:
            context['parent_links'].update({
                reverse('model-structure', args=[
                    self.kwargs.get('pk'),
                    self.model_obj.name
                ]): self.model_obj.title or self.model_obj.name
            })
        return context

    def get_structure_url(self):
        if self.model_obj.name:
            return reverse('model-structure', kwargs={
                'pk': self.kwargs.get('pk'),
                'model': self.model_obj.name
            })
        return None

    def get_data_url(self):
        if self.model_obj.name:
            return reverse('model-data', kwargs={
                'pk': self.object.pk,
                'model': self.model_obj.name,
            })
        return None

    def get_api_url(self):
        return self.model_obj.get_api_url()

    def get_history_objects(self):
        property_ids = self.props.values_list('pk', flat=True)
        property_history_objects = Version.objects.get_for_model(Property).filter(object_id__in=list(property_ids))
        model_history_objects = Version.objects.get_for_object(self.model_obj)
        history_objects = property_history_objects | model_history_objects
        return history_objects.order_by('-revision__date_created')


class PropertyHistoryView(
    StructureMixin,
    PlanMixin,
    HistoryView
):
    model = Dataset
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'
    plan_url_name = 'dataset-plans'
    tabs_template_name = 'vitrina/datasets/tabs.html'

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
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        self.model_obj = Model.objects.annotate(model_name=Func(
            F('metadata__name'),
            Value("/"),
            Value(-1),
            function='split_part',
            output_field=TextField())
        ).filter(model_name=model_name, dataset=self.object).first()
        if not self.model_obj:
            raise Http404('No Model matches the given query.')
        prop_name = kwargs.get('prop')
        self.property = get_object_or_404(Property, model=self.model_obj, metadata__name=prop_name)

        self.can_manage_structure = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        if self.can_manage_structure:
            self.models = Model.objects.filter(dataset=self.object).order_by('metadata__name')
            self.props = self.model_obj.get_given_props()
        else:
            self.models = Model.objects. \
                annotate(access=Max('model_properties__metadata__access')). \
                filter(dataset=self.object, access__gte=Metadata.PUBLIC). \
                order_by('metadata__name')
            self.props = self.model_obj.get_given_props().filter(metadata__access__gte=Metadata.PUBLIC)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.object.pk]): self.object.title,
            reverse('dataset-structure', args=[self.object.pk]): _("Struktūra"),
        }
        if self.model_obj.name and self.property.name:
            context['parent_links'].update({
                reverse('model-structure', args=[
                    self.kwargs.get('pk'),
                    self.model_obj.name
                ]): self.model_obj.title or self.model_obj.name,
                reverse('property-structure', kwargs={
                    'pk': self.kwargs.get('pk'),
                    'model': self.model_obj.name,
                    'prop': self.property.name,
                }): self.property.title or self.property.name,
            })
        return context

    def get_structure_url(self):
        if self.model_obj.name and self.property.name:
            return reverse('property-structure', kwargs={
                'pk': self.kwargs.get('pk'),
                'model': self.model_obj.name,
                'prop': self.property.name,
            })
        return None

    def get_data_url(self):
        if self.model_obj.name:
            return reverse('model-data', kwargs={
                'pk': self.object.pk,
                'model': self.model_obj.name
            })
        return None

    def get_api_url(self):
        return self.model_obj.get_api_url()

    def get_history_objects(self):
        return Version.objects.get_for_object(self.property).order_by('-revision__date_created')


class GetUpdatedSummaryView(View):
    def get(self, request, *args, **kwargs):
        model = request.GET.get('model')
        prop = request.GET.get('property')
        source_srid = request.GET.get('source_srid')
        target_srid = request.GET.get('target_srid')
        min_lng = request.GET.get('min_lng')
        min_lat = request.GET.get('min_lat')
        max_lng = request.GET.get('max_lng')
        max_lat = request.GET.get('max_lat')

        if source_srid != target_srid:
            min_lat, min_lng = transform_coordinates(min_lat, min_lng, target_srid, source_srid)
            max_lat, max_lng = transform_coordinates(max_lat, max_lng, target_srid, source_srid)

        query = f"bbox({min_lat}, {min_lng}, {max_lat}, {max_lng})"
        data = get_data_from_spinta(model, f":summary/{prop}", query)
        data = data.get('_data', [])

        transformed_data = []
        for item in data:
            centroid = loads(item.get('centroid'))
            x = centroid.x
            y = centroid.y
            if source_srid != target_srid:
                x, y = transform_coordinates(centroid.x, centroid.y, source_srid, target_srid)
            item['centroid'] = [x, y]
            transformed_data.append(item)
        return JsonResponse({'data': transformed_data})


class VersionCreateView(CreateView, PermissionRequiredMixin):
    model = _Version
    form_class = VersionForm
    template_name = 'vitrina/structure/version_form.html'

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.STRUCTURE,
            self.dataset
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dataset'] = self.dataset
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        return context

    def form_valid(self, form):
        version = form.save(commit=False)
        version.dataset = self.dataset

        base_email_content = """
                    Gautas pranešimas, kad sukurta nauja duomenų rinkinio struktūros versija:
                    {0}
                """

        latest_version = self.dataset.dataset_version.order_by('-version').first()
        if latest_version and latest_version.version:
            version.version = latest_version.version + 1
        else:
            version.version = 1
        version.save()

        rel_projects = Project.objects.filter(datasets=version.dataset)
        emails = []
        title = f"Sukurta nauja duomenų rinkinio struktūros versija: {ContentType.objects.get_for_model(version)}," \
                f" id: {version.pk}"
        for proj in rel_projects:
            emails.append(proj.user.email)
            Task.objects.create(
                title=title,
                description=f"Sukurta nauja duomenų rinkinio struktūros versija.",
                content_type=ContentType.objects.get_for_model(version),
                object_id=version.pk,
                user=proj.user,
                status=Task.CREATED
            )

        url = f"{get_current_domain(self.request)}/datasets/" \
              f"{version.dataset.pk}/version/{version.pk}"
        email_data = prepare_email_by_identifier('new-dataset-structure-version', base_email_content, title,
                                                 [url])
        send_email_with_logging(email_data, [emails])

        metadata = form.cleaned_data.get('metadata', [])

        for meta in metadata:
            if meta := Metadata.objects.filter(pk=meta).first():
                meta.draft = False
                meta.metadata_version = version
                meta.save()

                MetadataVersion.objects.create(
                    metadata=meta,
                    version=version,
                    name=meta.name if meta.name else None,
                    type=meta.type if meta.type else None,
                    required=meta.required,
                    unique=meta.unique,
                    type_args=meta.type_args if meta.type_args else None,
                    ref=meta.ref if meta.ref else None,
                    source=meta.source if meta.source else None,
                    prepare=meta.prepare if meta.prepare else None,
                    level_given=meta.level_given,
                    access=meta.access,
                    base=meta.object.base if isinstance(meta.object, Model) else None
                )

        return redirect(reverse("dataset-structure", args=[self.dataset.pk]))


class VersionListView(
    HistoryMixin,
    DatasetStructureMixin,
    PlanMixin,
    TemplateView
):
    template_name = 'vitrina/structure/version_list.html'
    context_object_name = 'dataset'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-plans-history'
    plan_url_name = 'dataset-plans'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get('status', 'not_deployed')
        context['dataset'] = self.dataset
        if status == 'deployed':
            context['versions'] = self.dataset.dataset_version.filter(deployed__isnull=False).order_by('-released')
        else:
            context['versions'] = self.dataset.dataset_version.filter(deployed__isnull=True).order_by('-released')
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.dataset
        )
        context['selected_tab'] = status
        return context

    def get_history_object(self):
        return self.dataset

    def get_detail_object(self):
        return self.dataset

    def get_plan_object(self):
        return self.dataset


class VersionDetailView(
    HistoryMixin,
    DatasetStructureMixin,
    PlanMixin,
    TemplateView
):
    template_name = 'vitrina/structure/version_detail.html'
    context_object_name = 'dataset'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-plans-history'
    plan_url_name = 'dataset-plans'

    version: _Version

    def dispatch(self, request, *args, **kwargs):
        self.version = get_object_or_404(_Version, pk=kwargs.get('version_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        context['version'] = self.version
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.dataset
        )

        changes = []
        models = []
        props = []
        version_items = {
            item.metadata.object: item
            for item in self.version.metadataversion_set.all()
        }

        if dataset_meta := version_items.get(self.dataset):
            prev_version = dataset_meta.metadata.metadataversion_set.filter(
                version__created__lt=self.version.created
            ).order_by('-version__created').first()
            if prev_version:
                changes.append({
                    'title': self.dataset.title,
                    'url': self.dataset.get_absolute_url(),
                    'new': False,
                    'changed_attrs': [{
                        'attr': 'name',
                        'value_before': prev_version.name,
                        'value_after': dataset_meta.name
                    }],
                    'class': 'dataset_meta'
                })
            else:
                changes.append({
                    'title': self.dataset.title,
                    'url': self.dataset.get_absolute_url(),
                    'new': True,
                    'changed_attrs': [{
                        'attr': 'name',
                        'value_after': dataset_meta.name
                    }],
                    'class': 'dataset_metadata'
                })

        for model in self.dataset.model_set.all():
            if model_meta := version_items.get(model):
                models.append(model)
                prev_version = model_meta.metadata.metadataversion_set.filter(
                    version__created__lt=self.version.created
                ).order_by('-version__created').first()

                changed_attrs = []
                if prev_version:
                    new = False
                    if prev_version.name != model_meta.name:
                        changed_attrs.append({
                            'attr': 'name',
                            'value_before': prev_version.name,
                            'value_after': model_meta.name,
                        })
                    if prev_version.ref != model_meta.ref:
                        changed_attrs.append({
                            'attr': 'ref',
                            'value_before': prev_version.ref,
                            'value_after': model_meta.ref,
                        })
                    if prev_version.level_given != model_meta.level_given:
                        changed_attrs.append({
                            'attr': 'level',
                            'value_before': prev_version.level_given,
                            'value_after': model_meta.level_given,
                        })
                    if prev_version.base != model_meta.base:
                        changed_attrs.append({
                            'attr': 'base',
                            'value_before': prev_version.base.model.name if prev_version.base else None,
                            'value_after': model_meta.base.model.name if model_meta.base else None,
                        })
                else:
                    new = True
                    changed_attrs.append({
                        'attr': 'name',
                        'value_after': model_meta.name,
                    })
                    if model_meta.ref:
                        changed_attrs.append({
                            'attr': 'ref',
                            'value_after': model_meta.ref,
                        })
                    if model_meta.level_given:
                        changed_attrs.append({
                            'attr': 'level',
                            'value_after': model_meta.level_given,
                        })
                    if model_meta.base:
                        changed_attrs.append({
                            'attr': 'base',
                            'value_after': model_meta.base.model.name,
                        })
                changes.append({
                    'title': model.name,
                    'url': model.get_absolute_url(),
                    'new': new,
                    'changed_attrs': changed_attrs,
                    'class': 'model_metadata'
                })

            for prop in model.model_properties.filter(given=True):
                changed_attrs = []

                if prop_meta := version_items.get(prop):
                    props.append(prop)
                    prev_version = prop_meta.metadata.metadataversion_set.filter(
                        version__created__lt=self.version.created
                    ).order_by('-version__created').first()

                    if prop.model not in models:
                        changes.append({
                            'title': prop.model.name,
                            'url': prop.model.get_absolute_url(),
                            'changed_attrs': [],
                            'class': 'model_metadata'
                        })
                        models.append(prop.model)

                    if prev_version:
                        new = False
                        if prev_version.name != prop_meta.name:
                            changed_attrs.append({
                                'attr': 'name',
                                'value_before': prev_version.name,
                                'value_after': prop_meta.name,
                            })
                        if prev_version.type_repr != prop_meta.type_repr:
                            changed_attrs.append({
                                'attr': 'type',
                                'value_before': prev_version.type_repr,
                                'value_after': prop_meta.type_repr,
                            })
                        if prev_version.ref != prop_meta.ref:
                            changed_attrs.append({
                                'attr': 'ref',
                                'value_before': prev_version.ref,
                                'value_after': prop_meta.ref,
                            })
                        if prev_version.level_given != prop_meta.level_given:
                            changed_attrs.append({
                                'attr': 'level',
                                'value_before': prev_version.level_given,
                                'value_after': prop_meta.level_given,
                            })
                        if prev_version.access != prop_meta.access:
                            changed_attrs.append({
                                'attr': 'access',
                                'value_before': prev_version.access,
                                'value_after': prop_meta.access,
                            })
                    else:
                        new = True
                        changed_attrs.append({
                            'attr': 'name',
                            'value_after': prop_meta.name,
                        })
                        if prop_meta.type:
                            changed_attrs.append({
                                'attr': 'type',
                                'value_after': prop_meta.type_repr,
                            })
                        if prop_meta.ref:
                            changed_attrs.append({
                                'attr': 'ref',
                                'value_after': prop_meta.ref,
                            })
                        if prop_meta.level_given:
                            changed_attrs.append({
                                'attr': 'level',
                                'value_after': prop_meta.level_given,
                            })
                        if prop_meta.access:
                            changed_attrs.append({
                                'attr': 'access',
                                'value_after': prop_meta.access,
                            })
                    changes.append({
                        'title': prop.name,
                        'url': prop.get_absolute_url(),
                        'new': new,
                        'changed_attrs': changed_attrs,
                        'class': 'prop_metadata'
                    })

                if enum := prop.enums.first():
                    for enum_item in enum.enumitem_set.all():
                        changed_attrs = []

                        if enum_meta := version_items.get(enum_item):
                            prev_version = enum_meta.metadata.metadataversion_set.filter(
                                version__created__lt=self.version.created
                            ).order_by('-version__created').first()

                            if enum.object.model not in models:
                                changes.append({
                                    'title': enum.object.model.name,
                                    'url': enum.object.model.get_absolute_url(),
                                    'changed_attrs': [],
                                    'class': 'model_metadata'
                                })
                                models.append(enum.object.model)
                            if enum.object not in props:
                                changes.append({
                                    'title': enum.object.name,
                                    'url': enum.object.get_absolute_url(),
                                    'changed_attrs': [],
                                    'class': 'prop_metadata'
                                })
                                props.append(enum.object)

                            if prev_version:
                                new = False
                                if prev_version.prepare != enum_meta.prepare:
                                    changed_attrs.append({
                                        'attr': 'prepare',
                                        'value_before': prev_version.prepare,
                                        'value_after': enum_meta.prepare,
                                    })
                                if prev_version.source != enum_meta.source:
                                    changed_attrs.append({
                                        'attr': 'source',
                                        'value_before': prev_version.source,
                                        'value_after': enum_meta.source,
                                    })
                            else:
                                new = True
                                if enum_meta.prepare:
                                    changed_attrs.append({
                                        'attr': 'prepare',
                                        'value_after': enum_meta.prepare,
                                    })
                                if enum_meta.source:
                                    changed_attrs.append({
                                        'attr': 'source',
                                        'value_after': enum_meta.source,
                                    })
                            changes.append({
                                'title': enum_item,
                                'url': prop.get_absolute_url(),
                                'new': new,
                                'changed_attrs': changed_attrs,
                                'class': 'enum_metadata'
                            })

        context['changes'] = changes

        return context

    def get_history_object(self):
        return self.dataset

    def get_detail_object(self):
        return self.dataset

    def get_plan_object(self):
        return self.dataset

    def get_structure_url(self):
        return reverse('version-list', kwargs={
            'pk': self.dataset.pk,
        })

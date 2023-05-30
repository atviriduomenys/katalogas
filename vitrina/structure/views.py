from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.structure.models import Model, Property
from vitrina.structure.services import get_data_from_spinta
from vitrina.views import HistoryMixin

EXCLUDED_COLS = ['_type', '_revision', '_base']

FORMATS = {
    'csv': 'CSV',
    'json': 'JSON',
    'rdf': 'RDF',
}


class StructureMixin:
    structure_url = None
    data_url = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'structure_url': self.get_structure_url(),
            'data_url': self.get_data_url(),
        })
        return context

    def get_structure_url(self):
        return self.structure_url

    def get_data_url(self):
        return self.data_url


class DatasetStructureView(HistoryMixin, StructureMixin, TemplateView):
    template_name = 'vitrina/structure/dataset_structure.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    object: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        structure = dataset.current_structure
        context['errors'] = []
        context['manifest'] = None
        context['structure'] = structure
        context['dataset'] = dataset
        context['models'] = Model.objects.filter(dataset=dataset).order_by('metadata__order')
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['can_manage_structure'] = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        return context

    def get_structure_url(self):
        return reverse('dataset-structure', kwargs={'pk': self.kwargs.get('pk')})

    def get_data_url(self):
        if model := Model.objects.filter(dataset__pk=self.kwargs.get('pk')).first():
            return reverse('model-data', kwargs={
                'pk': self.kwargs.get('pk'),
                'model': model.name,
            })
        return None


class ModelStructureView(HistoryMixin, StructureMixin, TemplateView):
    template_name = 'vitrina/structure/model_structure.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    object: Dataset
    model: Model

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        model_name = '/'.join([self.object.name, model_name])
        self.model = get_object_or_404(Model, dataset=self.object, metadata__name=model_name)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.object
        context['model'] = self.model
        context['models'] = Model.objects.filter(dataset=self.object).order_by('metadata__order')
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['can_manage_structure'] = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        return context

    def get_structure_url(self):
        return reverse('dataset-structure', kwargs={'pk': self.kwargs.get('pk')})

    def get_data_url(self):
        return reverse('model-data', kwargs={
            'pk': self.object.pk,
            'model': self.model.name,
        })


class PropertyStructureView(HistoryMixin, StructureMixin, TemplateView):
    template_name = 'vitrina/structure/property_structure.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    object: Dataset
    model: Model
    property: Property

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        model_name = '/'.join([self.object.name, model_name])
        self.model = get_object_or_404(Model, dataset=self.object, metadata__name=model_name)
        prop_name = kwargs.get('prop')
        self.property = get_object_or_404(Property, model=self.model, metadata__name=prop_name)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.object
        context['model'] = self.model
        context['models'] = Model.objects.filter(dataset=self.object).order_by('metadata__order')
        context['prop'] = self.property
        context['show_props'] = True
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['can_manage_structure'] = has_perm(
            self.request.user,
            Action.STRUCTURE,
            Dataset,
            self.object
        )
        return context

    def get_structure_url(self):
        return reverse('dataset-structure', kwargs={'pk': self.kwargs.get('pk')})

    def get_data_url(self):
        return reverse('model-data', kwargs={
            'pk': self.object.pk,
            'model': self.model.name
        })


class ModelDataView(HistoryMixin, StructureMixin, TemplateView):
    template_name = 'vitrina/structure/model_data.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    object: Dataset
    model: Model

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        model_name = '/'.join([self.object.name, model_name])
        self.model = get_object_or_404(Model, dataset=self.object, metadata__name=model_name)
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

        context['models'] = Model.objects.filter(dataset=self.object).order_by('metadata__order')

        tags = []
        select = 'select(*)'
        selected_cols = []
        query = ['limit(100)']
        for key, val in self.request.GET.items():
            if key.startswith('select('):
                select = key
                cols = select.replace('select(', '').replace(')', '')
                selected_cols = cols.split(',')
                query.append(select)
            else:
                if val == '':
                    tags.append(key)
                    query.append(key)
                else:
                    tag = f"{key}={val}"
                    tags.append(tag)
                    query.append(tag)

        query = '&'.join(query)
        _data = get_data_from_spinta(self.model, query=query)
        if _data.get('errors'):
            context['errors'] = _data.get('errors')
        elif _data.get('_data'):
            context['data'] = _data.get('_data')
            context['headers'] = [col for col in context['data'][0].keys() if col not in EXCLUDED_COLS]
            context['excluded_cols'] = EXCLUDED_COLS
            context['properties'] = {
                prop.name: prop
                for prop in self.model.get_given_props()
            }
            context['formats'] = FORMATS
            context['tags'] = tags
            context['select'] = select
            context['selected_cols'] = selected_cols or context['headers']

        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        return context

    def get_structure_url(self):
        return reverse('model-structure', kwargs={
            'pk': self.object.pk,
            'model': self.model.name,
        })

    def get_data_url(self):
        return reverse('model-data', kwargs={
            'pk': self.object.pk,
            'model': self.model.name
        })


class ObjectDataView(HistoryMixin, StructureMixin, TemplateView):
    template_name = 'vitrina/structure/object_data.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    object: Dataset
    model: Model

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        model_name = kwargs.get('model')
        model_name = '/'.join([self.object.name, model_name])
        self.model = get_object_or_404(Model, dataset=self.object, metadata__name=model_name)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_data'] = True
        context['dataset'] = self.object
        context['model'] = self.model

        context['models'] = Model.objects.filter(dataset=self.object).order_by('metadata__order')

        data = get_data_from_spinta(self.model, uuid=self.kwargs.get('uuid'))
        if data.get('errors'):
            context['errors'] = data.get('errors')
        else:
            context['data'] = data
            context['headers'] = [col for col in data.keys()]
            context['excluded_cols'] = EXCLUDED_COLS
            context['properties'] = {
                prop.name: prop
                for prop in self.model.get_given_props()
            }
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        return context

    def get_structure_url(self):
        return reverse('model-structure', kwargs={
            'pk': self.object.pk,
            'model': self.model.name,
        })

    def get_data_url(self):
        return reverse('object-data', kwargs={
            'pk': self.object.pk,
            'model': self.model.name,
            'uuid': self.kwargs.get('uuid')
        })

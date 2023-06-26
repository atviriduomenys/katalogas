import uuid
from gettext import ngettext
from typing import List

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Func, F, Value, TextField, Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.structure import spyna
from vitrina.structure.forms import EnumForm
from vitrina.structure.models import Model, Property, Metadata, EnumItem, Enum
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


class ModelStructureView(
    HistoryMixin,
    StructureMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/structure/model_structure.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

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
        context['models'] = self.models
        context['props'] = self.props
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['can_manage_structure'] = self.can_manage_structure
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


class PropertyStructureView(
    HistoryMixin,
    StructureMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/structure/property_structure.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

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


class ModelDataView(
    HistoryMixin,
    StructureMixin,
    PermissionRequiredMixin,
    TemplateView
):
    template_name = 'vitrina/structure/model_data.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

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
            self.models = Model.objects.\
                annotate(access=Max('model_properties__metadata__access')).\
                filter(dataset=self.object, access__gte=Metadata.PUBLIC).\
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


class ObjectDataView(HistoryMixin, StructureMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'vitrina/structure/object_data.html'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

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


class EnumCreateView(PermissionRequiredMixin, CreateView):
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
        return redirect(self.property.get_absolute_url())


class EnumUpdateView(PermissionRequiredMixin, UpdateView):
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
            metadata.save()

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

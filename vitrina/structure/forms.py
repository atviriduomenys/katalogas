import markdown
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, HTML
from django.core.exceptions import ValidationError
from django.db.models import Case, When, Q, Count
from django.forms.models import ModelChoiceIterator
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2MultipleWidget, ModelSelect2Widget
from lark import ParseError

from vitrina.structure import spyna
from vitrina.structure.helpers import is_time_unit, is_si_unit
from vitrina.structure.models import EnumItem, Metadata, Property, Model, Prefix


class EnumForm(forms.ModelForm):
    value = forms.CharField(label=_("Reikšmė"))
    source = forms.CharField(label=_("Reikšmė šaltinyje"), required=False)
    access = forms.ChoiceField(label=_("Prieigos lygmuo"), choices=Metadata.ACCESS_TYPES, required=False)
    title = forms.CharField(label=_("Pavadinimas"), required=False)
    description = forms.CharField(label=_("Aprašymas"), widget=forms.Textarea(attrs={'rows': 8}), required=False)

    class Meta:
        model = EnumItem
        fields = ('value', 'source', 'access', 'title', 'description')

    def __init__(self, prop=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.prop = prop
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "enum-form"
        self.helper.layout = Layout(
            Field('value'),
            Field('source'),
            Field('access'),
            Field('title'),
            Field('description'),
            Submit('submit', _("Redaguoti") if instance else _("Sukurti"), css_class='button is-primary'),
        )

        if instance and instance.metadata.first():
            metadata = instance.metadata.first()
            if self.prop.metadata.first() and self.prop.metadata.first().type == 'string':
                value = metadata.prepare.replace('"', '')
            else:
                value = metadata.prepare
            self.initial['value'] = value
            self.initial['source'] = metadata.source
            self.initial['access'] = metadata.access
            self.initial['title'] = metadata.title
            self.initial['description'] = metadata.description

    def clean_value(self):
        value = self.cleaned_data.get('value')
        if value:
            if metadata := self.prop.metadata.first():
                if metadata.type == 'integer':
                    try:
                        int(value)
                    except ValueError:
                        raise ValidationError(_("Reikšmė turi būti integer tipo."))
            try:
                spyna.parse(value)
            except ParseError as e:
                raise ValidationError(e)
        return value

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            md = markdown.Markdown()
            try:
                md.convert(description)
            except:
                raise ValidationError(_("Aprašymas neatitinka Markdown formato."))
        return description


def _get_level_title(title, description=None):
    if description:
        return mark_safe(f'{title}<br/><p class="help">{description}</p>')
    else:
        return title


MODEL_LEVEL_CHOICES = (
    (None, _get_level_title(_("Nenurodyta"))),
    (0, _get_level_title(
        _("Nėra identifikatoriaus"),
        _("Duomenyse nėra tokio duomenų lauko, kuris unikaliai identifikuoja objektą.")
    )),
    (1, _get_level_title(
        _("Neunikalus identifikatorius"),
        _("Duomenų laukas parinktas kaip identifikatorius nėra unikalus arba parinktas "
          "laukas nėra privalomas ir ne visi objektai gali turėti reikšmę.")
    )),
    (2, _get_level_title(
        _("Nepatikimas identifikatorius"),
        _("Duomenų lauko, kuris yra parinktas kaip identifikatorius, reikšmės gali keistis.")
    )),
    (3, _get_level_title(
        _("Patikimas identifikatorius"),
        _("Naudojamas patikimas lokalus identifikatorius, tačiau objektams nėra priskirtas "
          "globalus nekintantis identifikatorius.")
    )),
    (4, _get_level_title(
        _("Globalus identifikatorius"),
        _("Objektams priskirtas globalus nekintantis identifikatorius.")
    )),
)

BASE_LEVEL_CHOICES = (
    (None, _get_level_title(_("Nenurodyta"))),
    (0, _get_level_title(
        _("Nėra per ką sieti"),
        _("Nėra tokių duomenų laukų, per kuriuos būtų galima daryti susiejimą.")
    )),
    (1, _get_level_title(
        _("Susiejimas neįmanomas"),
        _("Modelio ir jo bazės susiejimas nėra įmanomas, kadangi laukai, per kuriuos "
          "siejama turi skirtingos formos reikšmes, nors semantiškai laukai, per kuriuos "
          "galimas susiejimas turi tą pačią prasmę.")
    )),
    (2, _get_level_title(
        _("Susiejimas nepatikimas"),
        _("Modelio ir jo bazės susiejimas galimas per duomenų laukus, kurie nėra objekto "
          "identifikatoriai ir gali keistis, pavyzdžiui siejimas pagal pavadinimą ar aprašymą. "
          "Daugelis objektų, gali būti susieti, nes tarkim pavadinimai sutampa, bet gali būti "
          "tokių atvejų, kur pavadinimai nesutampa.")
    )),
    (3, _get_level_title(
        _("Susiejimas netikrinant"),
        _("Modelio ir jo bazės susiejimas daromas per patikimą identifikatorių, tačiau nėra "
          "daromas patikrinimas ar duomenys tikrai susisieja.")
    )),
    (4, _get_level_title(
        _("Susiejimas tikrinant"),
        _("Modelio ir jo bazės siejimas atliekamas ne tik naudojant patikimą identifikatorių, "
          "tačiau teikiant duomenis užtikrinamas identifikatorių vientisumas.")
    )),
)


class OrderedModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def clean(self, value):
        qs = super(OrderedModelMultipleChoiceField, self).clean(value)
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(value)])
        return qs.filter(pk__in=value).order_by(preserved)


class OrderMixin:

    def optgroups(self, name, value, attrs=None):
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {str(v) for v in value}
        if not self.is_required and not self.allow_multiple_selected:
            default[1].append(self.create_option(name, "", "", False, 0))
        if not isinstance(self.choices, ModelChoiceIterator):
            return super().optgroups(name, value, attrs=attrs)
        selected_choices = {
            c for c in selected_choices if c not in self.choices.field.empty_values
        }
        field_name = self.choices.field.to_field_name or "pk"

        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(value)])
        query = Q(**{"%s__in" % field_name: selected_choices})
        for obj in self.choices.queryset.filter(query).order_by(preserved):
            option_value = self.choices.choice(obj)[0]
            option_label = self.label_from_instance(obj)

            selected = str(option_value) in value and (
                has_selected is False or self.allow_multiple_selected
            )
            if selected is True and has_selected is False:
                has_selected = True
            index = len(default[1])
            subgroup = default[1]
            subgroup.append(
                self.create_option(
                    name, option_value, option_label, selected_choices, index
                )
            )
        return groups


class RefWidget(OrderMixin, ModelSelect2MultipleWidget):
    model = Property
    search_fields = ['metadata__name__icontains']
    dependent_fields = {'model_id': 'model__pk'}


class BaseWidget(ModelSelect2Widget):
    model = Model
    search_fields = ['metadata__name__icontains', 'metadata__title__icontains']

    def label_from_instance(self, obj):
        if obj.title:
            return f"{obj.name} - {obj.title}"
        else:
            return obj.name


class BaseRefWidget(OrderMixin, ModelSelect2MultipleWidget):
    model = Property
    search_fields = ['metadata__name__icontains']
    dependent_fields = {'base': 'model'}


def _check_prepare_ast(ast, model_props, bind=False):
    if isinstance(ast, dict):
        if ast.get('name') == 'bind':
            bind = True
        for arg in ast.get('args', []):
            _check_prepare_ast(arg, model_props, bind)
    elif bind:
        if ast not in model_props:
            raise ValidationError(_(f'Duomenų filtre nurodytas modelyje neegzistuojantis laukas: "{ast}".'))


class ModelCreateForm(forms.ModelForm):
    name = forms.CharField(label=_("Kodinis pavadinimas"))
    source = forms.CharField(label=_("Duomenų šaltinis"), required=False)
    prepare = forms.CharField(label=_("Duomenų filtras"), required=False)
    uri = forms.CharField(label=_("Klasė"), required=False)
    level = forms.ChoiceField(
        label=_("Brandos lygis"),
        required=False,
        widget=forms.RadioSelect,
        choices=MODEL_LEVEL_CHOICES,
    )
    title = forms.CharField(label=_("Pavadinimas"), required=False)
    description = forms.CharField(
        label=_("Aprašymas"),
        required=False,
        widget=forms.Textarea(attrs={'rows': 8})
    )

    base = forms.ModelChoiceField(
        label=_("Modelio bazė"),
        required=False,
        queryset=Model.objects.all(),
        widget=BaseWidget(attrs={'data-width': '100%', 'data-minimum-input-length': 0})
    )
    base_ref = OrderedModelMultipleChoiceField(
        label=_("Pirminis raktas"),
        required=False,
        widget=BaseRefWidget(attrs={'data-width': '100%', 'data-minimum-input-length': 0}),
        queryset=Property.objects.all()
    )
    base_level = forms.ChoiceField(
        label=_("Brandos lygis"),
        required=False,
        widget=forms.RadioSelect,
        choices=BASE_LEVEL_CHOICES,
    )

    comment = forms.CharField(
        label=_("Keitimo komentaras"),
        required=False,
        widget=forms.Textarea(attrs={'rows': 6})
    )
    is_parameterized = forms.BooleanField(label=_("Parametrizuotas"), required=False)

    class Meta:
        model = Metadata
        fields = ('name', 'source', 'prepare', 'uri', 'level', 'title',
                  'description', 'base', 'base_ref', 'base_level', 'comment', 'is_parameterized',)

    def __init__(self, dataset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset = dataset
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "model-form"
        self.helper.layout = Layout(
            Field('name'),
            Field('source'),
            Field('prepare'),
            Field('uri'),
            Field('level'),
            Field('title'),
            Field('description'),
            Field('is_parameterized'),
            HTML(f'<hr><h4 class="custom-title mt-5">{_("Modelio bazė")}</h4>'),
            Field('base'),
            Field('base_ref'),
            Field('base_level'),
            HTML(f'<hr><h4 class="custom-title mt-5">{_("Istorija")}</h4>'),
            Field('comment'),
            Submit('submit', _("Sukurti"), css_class='button is-primary')
        )

        self.initial['level'] = 'None'
        self.initial['base_level'] = 'None'

    def clean_level(self):
        level = self.cleaned_data.get('level')
        if level and level != 'None':
            return int(level)
        return None

    def clean_base_level(self):
        level = self.cleaned_data.get('base_level')
        if level and level != 'None':
            return int(level)
        return None

    def clean_prepare(self):
        prepare = self.cleaned_data.get('prepare')
        instance = self.instance if self.instance and self.instance.pk else None
        if instance:
            props = instance.object.model_properties.values_list('metadata__name', flat=True)
        else:
            props = []
        if prepare:
            try:
                prepare_ast = spyna.parse(prepare)
            except ParseError as e:
                raise ValidationError(e)
            _check_prepare_ast(prepare_ast, props)
        return prepare

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            if not name[0].isupper():
                raise ValidationError(_("Pirmas kodinio pavadinimo simbolis turi būti didžioji raidė."))
            elif any(not c.isalnum() for c in name):
                raise ValidationError(_("Pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, "
                                        "jokie kiti simboliai negalimi."))
        return name

    def clean_uri(self):
        uri = self.cleaned_data.get('uri')
        if uri:
            if '://' not in uri and ':' not in uri:
                raise ValidationError(_(f'Nevalidus uri "{uri}" formatas.'))
            if '://' not in uri and ':' in uri:
                parts = uri.split(':')
                if len(parts) != 2:
                    raise ValidationError(_(f'Nevalidus uri "{uri}" formatas.'))
                else:
                    prefix = parts[0]
                    if not Prefix.objects.filter(
                        Q(content_type=None, object_id=None, name=prefix) |
                        Q(metadata__dataset=self.dataset, name=prefix)
                    ).exists():
                        raise ValidationError(_(f'Neatpažintas "{prefix}" prefiksas.'))
        return uri

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            md = markdown.Markdown()
            try:
                md.convert(description)
            except:
                raise ValidationError(_("Aprašymas neatitinka Markdown formato."))
        return description


class ModelUpdateForm(ModelCreateForm):
    model_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    ref = OrderedModelMultipleChoiceField(
        label=_("Pirminis raktas"),
        required=False,
        widget=RefWidget(attrs={'data-width': '100%', 'data-minimum-input-length': 0}),
        queryset=Property.objects.all(),
    )

    class Meta:
        model = Metadata
        fields = ('model_id', 'name', 'ref', 'source', 'prepare', 'uri', 'is_parameterized',
                  'level', 'title', 'description', 'base', 'base_ref', 'base_level', 'comment')

    def __init__(self, dataset, *args, **kwargs):
        super().__init__(dataset, *args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None

        self.helper.layout = Layout(
            Field('model_id'),
            Field('name'),
            Field('ref'),
            Field('source'),
            Field('prepare'),
            Field('uri'),
            Field('level'),
            Field('title'),
            Field('description'),
            Field('is_parameterized'),
            HTML(f'<hr><h4 class="custom-title mt-5">{_("Modelio bazė")}</h4>'),
            Field('base'),
            Field('base_ref'),
            Field('base_level'),
            HTML(f'<hr><h4 class="custom-title mt-5">{_("Istorija")}</h4>'),
            Field('comment'),
            Submit('submit', _("Redaguoti"), css_class='button is-primary')
        )

        if instance:
            model = instance.object
            self.initial['model_id'] = model.pk
            self.initial['name'] = instance.name.split('/')[-1]
            self.initial['level'] = instance.level_given if instance.level_given is not None else 'None'
            self.initial['ref'] = model.property_list.order_by('order').values_list('property', flat=True)
            self.initial['is_parameterized'] = model.is_parameterized
            self.initial['base_level'] = 'None'
            if model.base:
                self.initial['base'] = model.base.model
                self.initial['base_ref'] = model.base.property_list.order_by('order').values_list('property', flat=True)
                if model.base.metadata.first():
                    self.initial['base_level'] = model.base.metadata.first().level_given or 'None'


PROPERTY_LEVEL_CHOICES = (
    (None, _get_level_title(_("Nenurodyta"))),
    (0, _get_level_title(
        _("Duomenų nėra"),
        _("Tokių duomenų nėra, tačiau jie yra reikalingi.")
    )),
    (1, _get_level_title(
        _("Laisvos formos duomenys"),
        _("Duomenys pateikti nesilaikant vientisumo ar aiškios struktūros, dažnai tai "
          "yra laisvos formos tekstas arba duomenys įvedami ranka.")
    )),
    (2, _get_level_title(
        _("Nestandartiniai duomenys"),
        _("Duomenyse išlaikytas vientisumas ir aiški struktūra, tačiau duomenys "
          "pateikti nestandartine forma.")
    )),
    (3, _get_level_title(
        _("Standartinė forma"),
        _("Duomenys pateikti standartine forma, tačiau nėra nurodyti vienetai ar duomenų tikslumas.")
    )),
    (4, _get_level_title(
        _("Identifikatoriai"),
        _("Duomenys susieti su kitais duomenimis, vienetais, klasifikatoriais, nurodytas duomenų tikslumas.")
    )),
    (5, _get_level_title(
        _("Standartai"),
        _("Duomenys susieti su standartiniais žodynais/ontologijomis.")
    )),
)


class PropertyRefWidget(ModelSelect2Widget):
    model = Model
    search_fields = ['metadata__name__icontains', 'metadata__title__icontains']
    dependent_fields = {'dataset_id': 'dataset__pk'}

    def label_from_instance(self, obj):
        if obj.title:
            return f"{obj.name} - {obj.title}"
        else:
            return obj.name

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        dataset_id = None
        if 'dataset__pk' in dependent_fields:
            dataset_id = dependent_fields.pop('dataset__pk')
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)

        top_models = queryset.annotate(
            count=Count('ref_model_properties')
        ).order_by('-count')[:5].values_list('pk', flat=True)
        dataset_models = []
        if dataset_id:
            dataset_models = queryset.filter(dataset__pk=dataset_id).exclude(
                pk__in=top_models
            ).values_list('pk', flat=True)
        if top_models or dataset_models:
            ids = []
            ids.extend(top_models)
            ids.extend(dataset_models)
            preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ids)])

            if term:
                queryset = queryset.order_by(preserved)
            else:
                queryset = queryset.filter(pk__in=ids).order_by(preserved)
        return queryset


TYPES = (
    ('any', _("any")),
    ('pk', _("pk")),
    ('date', _("date")),
    ('time', _("time")),
    ('datetime', _("datetime")),
    ('temporal', _("temporal")),
    ('string', _("string")),
    ('binary', _("binary")),
    ('integer', _("integer")),
    ('number', _("number")),
    ('boolean', _("boolean")),
    ('url', _("url")),
    ('uri', _("uri")),
    ('image', _("image")),
    ('geometry', _("geometry")),
    ('spatial', _("spatial")),
    ('ref', _("ref")),
    ('backref', _("backref")),
    ('generic', _("generic")),
    ('object', _("object")),
    ('file', _("file")),
    ('rql', _("rql")),
    ('json', _("json")),
    ('denorm', _("denorm")),
    ('inherit', _("inherit")),
)


class PropertyForm(forms.ModelForm):
    dataset_id = forms.IntegerField(widget=forms.HiddenInput)
    name = forms.CharField(label=_("Kodinis pavadinimas"))
    type = forms.ChoiceField(label=_("Tipas"), choices=TYPES)
    ref = forms.ModelChoiceField(
        label=_("Ryšys"),
        required=False,
        widget=PropertyRefWidget(attrs={'data-width': '100%', 'data-minimum-input-length': 0}),
        queryset=Model.objects.all()
    )
    ref_others = forms.CharField(label=_("Ryšys"), required=False)
    source = forms.CharField(label=_("Duomenų šaltinis"), required=False)
    prepare = forms.CharField(label=_("Duomenų transformacija"), required=False)
    uri = forms.CharField(label=_("Klasė"), required=False)
    level = forms.ChoiceField(
        label=_("Brandos lygis"),
        required=False,
        widget=forms.RadioSelect,
        choices=PROPERTY_LEVEL_CHOICES,
    )
    access = forms.ChoiceField(label=_("Prieigos lygis"), required=False, choices=Metadata.ACCESS_TYPES)
    title = forms.CharField(label=_("Pavadinimas"), required=False)
    description = forms.CharField(
        label=_("Aprašymas"),
        required=False,
        widget=forms.Textarea(attrs={'rows': 8})
    )

    class Meta:
        model = Metadata
        fields = ('dataset_id', 'name', 'type', 'ref', 'ref_others', 'source',
                  'prepare', 'uri', 'level', 'access', 'title', 'description',)

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.model = model
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "property-form"
        self.helper.layout = Layout(
            Field('dataset_id'),
            Field('name'),
            Field('type'),
            Field('ref'),
            Field('ref_others'),
            Field('source'),
            Field('prepare'),
            Field('uri'),
            Field('level'),
            Field('access'),
            Field('title'),
            Field('description'),
            Submit('submit', _("Redaguoti") if instance else _("Sukurti"), css_class='button is-primary')
        )

        self.initial['dataset_id'] = self.model.dataset.pk
        self.initial['level'] = 'None'
        if instance:
            self.initial['level'] = instance.level_given if instance.level_given is not None else 'None'
            self.initial['access'] = instance.access
            if instance.object.ref_model:
                self.initial['ref'] = instance.object.ref_model
                self.initial['ref_others'] = None
            else:
                self.initial['ref_others'] = instance.ref
                self.initial['ref'] = None

            if self.instance.object not in self.model.get_props_excluding_base():
                self.fields['name'].widget.attrs['readonly'] = True

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            if not name[0].islower():
                raise ValidationError(_("Pirmas kodinio pavadinimo simbolis turi būti mažoji raidė."))
            elif any((not c.isalnum() and c != '_') for c in name):
                raise ValidationError(_("Pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, "
                                        "žodžiai gali būti atskirti _ simboliu,"
                                        "jokie kiti simboliai negalimi."))
        return name

    def clean_level(self):
        level = self.cleaned_data.get('level')
        if level and level != 'None':
            return int(level)
        return None

    def clean_prepare(self):
        prepare = self.cleaned_data.get('prepare')
        props = self.model.model_properties.values_list('metadata__name', flat=True)
        if prepare:
            try:
                prepare_ast = spyna.parse(prepare)
            except ParseError as e:
                raise ValidationError(e)
            _check_prepare_ast(prepare_ast, props)
        return prepare

    def clean_uri(self):
        uri = self.cleaned_data.get('uri')
        if uri:
            if '://' not in uri and ':' not in uri:
                raise ValidationError(_(f'Nevalidus uri "{uri}" formatas.'))
            if '://' not in uri and ':' in uri:
                parts = uri.split(':')
                if len(parts) != 2:
                    raise ValidationError(_(f'Nevalidus uri "{uri}" formatas.'))
                else:
                    prefix = parts[0]
                    if not Prefix.objects.filter(
                            Q(content_type=None, object_id=None, name=prefix) |
                            Q(metadata__dataset=self.model.dataset, name=prefix)
                    ).exists():
                        raise ValidationError(_(f'Neatpažintas "{prefix}" prefiksas.'))
        return uri

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            md = markdown.Markdown()
            try:
                md.convert(description)
            except:
                raise ValidationError(_("Aprašymas neatitinka Markdown formato."))
        return description

    def clean_ref(self):
        type = self.cleaned_data.get('type')
        ref = self.cleaned_data.get('ref')
        if type == 'ref' and not ref:
            raise ValidationError(_("Šis laukas yra privalomas."))
        return ref

    def clean_ref_others(self):
        type = self.cleaned_data.get('type')
        ref = self.cleaned_data.get('ref_others')
        if ref:
            if type == 'date' or type == 'datetime':
                if not is_time_unit(ref):
                    raise ValidationError(_("Netinkami matavimo vienetai."))
            elif type == 'integer' or type == 'number' or type == 'geometry':
                if not is_si_unit(ref):
                    raise ValidationError(_("Netinkami matavimo vienetai."))
        return ref

    def clean_access(self):
        access = self.cleaned_data.get('access')
        if access == '':
            return None
        return access


class ParamForm(forms.ModelForm):
    name = forms.CharField(label=_("Kodinis pavadinimas"))
    prepare = forms.CharField(label=_("Formulė"))

    class Meta:
        model = Metadata
        fields = ('name', 'source', 'prepare', 'title', 'description')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "param-form"
        self.helper.layout = Layout(
            Field('name'),
            Field('source'),
            Field('prepare'),
            Field('title'),
            Field('description', rows="2"),
            Submit('submit', _("Redaguoti") if instance else _("Sukurti"), css_class='button is-primary'),
        )

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            if not name[0].islower():
                raise ValidationError(_("Pirmas kodinio pavadinimo simbolis turi būti mažoji raidė."))
            elif any((not c.isalnum() and c != '_') for c in name):
                raise ValidationError(_("Pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, "
                                        "žodžiai gali būti atskirti _ simboliu,"
                                        "jokie kiti simboliai negalimi."))
        return name

    def clean_prepare(self):
        prepare = self.cleaned_data.get('prepare')
        if prepare:
            try:
                spyna.parse(prepare)
            except ParseError as e:
                raise ValidationError(e)
        return prepare

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:
            md = markdown.Markdown()
            try:
                md.convert(description)
            except:
                raise ValidationError(_("Aprašymas neatitinka Markdown formato."))
        return description

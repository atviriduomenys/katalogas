import datetime

import markdown
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, HTML
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Case, When, Q, Count
from django.forms import CheckboxSelectMultiple
from django.forms.models import ModelChoiceIterator
from django.utils.functional import lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _, gettext
from django_select2.forms import ModelSelect2MultipleWidget, ModelSelect2Widget
from lark import ParseError

from vitrina.classifiers.models import Status
from vitrina.resources.models import DatasetDistribution
from vitrina.structure import spyna, AccessType
from vitrina.structure.helpers import is_time_unit, is_si_unit
from vitrina.structure.models import (
    EnumItem,
    Metadata,
    Property,
    Model,
    Prefix,
    Version,
    VersionStatus,
    VersionType,
)


class ModelChoiceTypeField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.description:
            return mark_safe(f'{obj.name}<br/><p class="help">{obj.description}</p>')
        else:
            return obj.name


def _get_level_title(title: str, description: str | None = None) -> str:
    def _render() -> str:
        title_text = gettext(title)
        if description:
            description_text = gettext(description)
            return mark_safe(f'{title_text}<br/><p class="help">{description_text}</p>')
        return title_text

    return lazy(_render, str)()


def _get_visibility(visibility: int) -> str:
    if visibility == Metadata.PRIVATE:
        return "private"
    elif visibility == Metadata.PROTECTED:
        return "protected"
    elif visibility == Metadata.PACKAGE:
        return "package"
    elif visibility == Metadata.VISIBILITY_PUBLIC:
        return "public"
    return ""


VISIBILITY_LEVEL_CHOICES = (
    (None, _get_level_title(_("Nepasirinkta"))),
    (
        0,
        _get_level_title(
            _("Metaduomenys nepublikuojami (private)"),
        ),
    ),
    (
        1,
        _get_level_title(
            _("Naudojamas informacinės sistemos (IS) lygmeniu (protected)"),
            _(
                "Nėra jokios Informacinės sistemos, kurioje tvarkomi duomenys arba Informacinė sistema nėra registruota Kataloge"
            ),
        ),
    ),
    (
        2,
        _get_level_title(
            _("Naudojamas LT lygmeniu (package)"),
            _("Įteisintas Informacinės sistemos nuostatuose ir kituose LT teisės aktuose"),
        ),
    ),
    (
        3,
        _get_level_title(
            _("Naudojamas EU lygmeniu (public)"),
        ),
    ),
)


class EnumForm(forms.ModelForm):
    value = forms.CharField(label=_("Reikšmė"), help_text=_("Fiksuotos reikšmės vertė."))
    source = forms.CharField(
        label=_("Reikšmė šaltinyje"),
        required=False,
        help_text=_("Fiksuotos reikšmės vertė šaltinyje."),
    )
    access = forms.ChoiceField(
        label=_("Prieigos lygmuo"),
        choices=AccessType.choices,
        required=False,
        help_text=_("Prieigos lygis, naudojamas pagal nutylėjimą visiems šios vardų erdvės elementams."),
    )
    status = ModelChoiceTypeField(
        label=_("Būsena"),
        required=False,
        queryset=(
            Status.objects.exclude(Q(codename__in=["develop", "completed"]) | Q(codename__isnull=True)).order_by("id")
        ),
        widget=forms.RadioSelect,
        help_text=_("Savybė nurodanti modelio metaduomenų gyvavimo ciklo būseną."),
    )
    visibility = forms.ChoiceField(
        label=_("Metaduomenų matomumas"),
        required=False,
        widget=forms.RadioSelect,
        choices=VISIBILITY_LEVEL_CHOICES,
        help_text=_("Savybė nurodanti modelio laukų metaduomenų matomumo ir prieinamumo lygį. "),
    )
    eli = forms.URLField(
        label=_("Europos teisės akto identifikatorius (ELI)"),
        required=False,
        help_text=_(
            "Teisės akto identifikavimo standartas, leidžiantis nurodyti ne tik patį teisės akto dokumentą, bet ir konkrečią vietą dokumente. <br> "
            """Pateikti konkrečią vietą teisės akto dokumente: po # pateikite konkrečią vietą: "#17.2" <br>"""
            "Tais atvejais, kai yra keli dokumentai su priedais: "
            """ "#priedas1/17.2" """
            """ "17.2/17.2.5", """
            """kur "priedas1" yra dokumento failo pavadinimas."""
        ),
    )
    title = forms.CharField(
        label=_("Pavadinimas"),
        required=False,
        help_text=_("Duomenų rinkinio ar vardų erdvės pavadinimas."),
    )
    description = forms.CharField(
        label=_("Aprašymas"),
        widget=forms.Textarea(attrs={"rows": 8}),
        required=False,
        help_text=_("Duomenų rinkinio ar vardų erdvės aprašymas."),
    )

    class Meta:
        model = EnumItem
        fields = (
            "value",
            "source",
            "access",
            "status",
            "visibility",
            "eli",
            "title",
            "description",
        )

    def __init__(self, prop=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.prop = prop
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "enum-form"
        self.helper.layout = Layout(
            Field("value"),
            Field("source"),
            Field("access"),
            Field("status"),
            Field("visibility"),
            Field("eli"),
            Field("title"),
            Field("description"),
            Submit(
                "submit",
                _("Redaguoti") if instance else _("Sukurti"),
                css_class="button is-primary",
            ),
        )

        if instance and instance.metadata.first():
            metadata = instance.metadata.first()
            if self.prop.metadata.first() and self.prop.metadata.first().type == "string":
                value = metadata.prepare.replace('"', "")
            else:
                value = metadata.prepare
            self.initial["value"] = value
            self.initial["source"] = metadata.source
            self.initial["access"] = metadata.access
            self.initial["title"] = metadata.title
            self.initial["description"] = metadata.description
            self.initial["visibility"] = metadata.visibility if metadata.visibility is not None else "None"
            self.initial["eli"] = metadata.eli
            self.initial["status"] = metadata.status
        else:
            self.initial["visibility"] = "None"

    def clean_value(self):
        value = self.cleaned_data.get("value")
        if value:
            if metadata := self.prop.metadata.first():
                if metadata.type == "integer":
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
        description = self.cleaned_data.get("description")
        if description:
            md = markdown.Markdown()
            try:
                md.convert(description)
            except Exception:
                raise ValidationError(_("Aprašymas neatitinka Markdown formato."))
        return description

    def clean_visibility(self):
        visibility = self.cleaned_data.get("visibility")
        if visibility == "None":
            return None
        visibility = int(visibility)
        visibility_str = _get_visibility(visibility)

        if metadata := self.prop.metadata.first():
            if metadata.visibility is None:
                model_metadata = self.prop.model.metadata.first()
                if model_metadata and model_metadata.visibility is not None:
                    if visibility > model_metadata.visibility:
                        model_visibility_str = _get_visibility(model_metadata.visibility)
                        raise ValidationError(
                            _(
                                "Metaduomenų matomumas '{0}' negali būti didesnis nei duomenų modelio matomumas '{1}'."
                            ).format(visibility_str, model_visibility_str)
                        )
            else:
                if visibility > metadata.visibility:
                    property_visibility_str = _get_visibility(metadata.visibility)
                    raise ValidationError(
                        _("Metaduomenų matomumas '{0}' negali būti didesnis nei duomenų lauko matomumas '{1}'.").format(
                            visibility_str, property_visibility_str
                        )
                    )

        return visibility


MODEL_LEVEL_CHOICES = (
    (None, _get_level_title(_("Nenurodyta"))),
    (
        0,
        _get_level_title(
            _("Nėra identifikatoriaus"),
            _("Duomenyse nėra tokio duomenų lauko, kuris unikaliai identifikuoja objektą."),
        ),
    ),
    (
        1,
        _get_level_title(
            _("Neunikalus identifikatorius"),
            _(
                "Duomenų laukas parinktas kaip identifikatorius nėra unikalus arba parinktas "
                "laukas nėra privalomas ir ne visi objektai gali turėti reikšmę."
            ),
        ),
    ),
    (
        2,
        _get_level_title(
            _("Nepatikimas identifikatorius"),
            _("Duomenų lauko, kuris yra parinktas kaip identifikatorius, reikšmės gali keistis."),
        ),
    ),
    (
        3,
        _get_level_title(
            _("Patikimas identifikatorius"),
            _(
                "Naudojamas patikimas lokalus identifikatorius, tačiau objektams nėra priskirtas "
                "globalus nekintantis identifikatorius."
            ),
        ),
    ),
    (
        4,
        _get_level_title(
            _("Globalus identifikatorius"),
            _("Objektams priskirtas globalus nekintantis identifikatorius."),
        ),
    ),
)

BASE_LEVEL_CHOICES = (
    (None, _get_level_title(_("Nenurodyta"))),
    (
        0,
        _get_level_title(
            _("Nėra per ką sieti"),
            _("Nėra tokių duomenų laukų, per kuriuos būtų galima daryti susiejimą."),
        ),
    ),
    (
        1,
        _get_level_title(
            _("Susiejimas neįmanomas"),
            _(
                "Modelio ir jo bazės susiejimas nėra įmanomas, kadangi laukai, per kuriuos "
                "siejama turi skirtingos formos reikšmes, nors semantiškai laukai, per kuriuos "
                "galimas susiejimas turi tą pačią prasmę."
            ),
        ),
    ),
    (
        2,
        _get_level_title(
            _("Susiejimas nepatikimas"),
            _(
                "Modelio ir jo bazės susiejimas galimas per duomenų laukus, kurie nėra objekto "
                "identifikatoriai ir gali keistis, pavyzdžiui siejimas pagal pavadinimą ar aprašymą. "
                "Daugelis objektų, gali būti susieti, nes tarkim pavadinimai sutampa, bet gali būti "
                "tokių atvejų, kur pavadinimai nesutampa."
            ),
        ),
    ),
    (
        3,
        _get_level_title(
            _("Susiejimas netikrinant"),
            _(
                "Modelio ir jo bazės susiejimas daromas per patikimą identifikatorių, tačiau nėra "
                "daromas patikrinimas ar duomenys tikrai susisieja."
            ),
        ),
    ),
    (
        4,
        _get_level_title(
            _("Susiejimas tikrinant"),
            _(
                "Modelio ir jo bazės siejimas atliekamas ne tik naudojant patikimą identifikatorių, "
                "tačiau teikiant duomenis užtikrinamas identifikatorių vientisumas."
            ),
        ),
    ),
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
        selected_choices = {c for c in selected_choices if c not in self.choices.field.empty_values}
        field_name = self.choices.field.to_field_name or "pk"

        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(value)])
        query = Q(**{"%s__in" % field_name: selected_choices})
        for obj in self.choices.queryset.filter(query).order_by(preserved):
            option_value = self.choices.choice(obj)[0]
            option_label = self.label_from_instance(obj)

            selected = str(option_value) in value and (has_selected is False or self.allow_multiple_selected)
            if selected is True and has_selected is False:
                has_selected = True
            index = len(default[1])
            subgroup = default[1]
            subgroup.append(self.create_option(name, option_value, option_label, selected_choices, index))
        return groups


class RefWidget(OrderMixin, ModelSelect2MultipleWidget):
    model = Property
    search_fields = ["metadata__name__icontains"]
    dependent_fields = {"model_id": "model__pk"}


class BaseWidget(ModelSelect2Widget):
    model = Model
    search_fields = ["metadata__name__icontains", "metadata__title__icontains"]

    def label_from_instance(self, obj):
        if obj.title:
            return f"{obj.name} - {obj.title}"
        else:
            return obj.name


class BaseRefWidget(OrderMixin, ModelSelect2MultipleWidget):
    model = Property
    search_fields = ["metadata__name__icontains"]
    dependent_fields = {"base": "model"}


def _check_prepare_ast(ast, model_props, bind=False):
    if isinstance(ast, dict):
        if ast.get("name") == "bind":
            bind = True
        for arg in ast.get("args", []):
            _check_prepare_ast(arg, model_props, bind)
    elif bind:
        if ast not in model_props:
            raise ValidationError(_(f'Duomenų filtre nurodytas modelyje neegzistuojantis laukas: "{ast}".'))


class ModelCreateForm(forms.ModelForm):
    name = forms.CharField(
        label=_("Kodinis pavadinimas"),
        help_text=_("Savybė nurodanti duomenų lauko pavadinimą, modelio atributas."),
    )
    source = forms.CharField(
        label=_("Duomenų šaltinis"),
        required=False,
        help_text=_("Duomenų lauko pavadinimas šaltinyje. Prasmė priklauso nuo resource.type."),
    )
    prepare = forms.CharField(
        label=_("Duomenų filtras"),
        required=False,
        help_text=_("Formulė skirta duomenų tikrinimui ir transformavimui arba statinės reikšmės pateikimui."),
    )
    uri = forms.CharField(
        label=_("Klasė"),
        required=False,
        help_text=_("Sąsaja su išoriniu žodynu."),
    )
    level = forms.ChoiceField(
        label=_("Brandos lygis"),
        required=False,
        widget=forms.RadioSelect,
        choices=MODEL_LEVEL_CHOICES,
        help_text=_(
            "Modelio brandos lygis, nusakantis modelio brandos lygį, pavyzdžiui ar nurodytas pirminis raktas, "
            "ar modelio pavadinimas atitinka kodiniams pavadinimams keliamus reikalavimus."
        ),
    )
    status = ModelChoiceTypeField(
        label=_("Būsena"),
        required=False,
        queryset=(
            Status.objects.exclude(Q(codename__in=["develop", "completed"]) | Q(codename__isnull=True)).order_by("id")
        ),
        widget=forms.RadioSelect,
        help_text=_("Savybė nurodanti modelio metaduomenų gyvavimo ciklo būseną."),
    )
    distribution = forms.ModelChoiceField(
        label=_("Duomenų distribucija"),
        required=False,
        queryset=DatasetDistribution.objects.none(),
        help_text=_("Savybė nurodanti modelio duomenų distribuciją."),
    )
    visibility = forms.ChoiceField(
        label=_("Metaduomenų matomumas"),
        required=False,
        widget=forms.RadioSelect,
        choices=VISIBILITY_LEVEL_CHOICES,
        help_text=_("Savybė nurodanti modelio laukų metaduomenų matomumo ir prieinamumo lygį."),
    )
    eli = forms.URLField(
        label=_("Europos teisės akto identifikatorius (ELI)"),
        required=False,
        help_text=_(
            "Teisės akto identifikavimo standartas, leidžiantis nurodyti ne tik patį teisės akto dokumentą, bet ir konkrečią vietą dokumente. <br> "
            """Pateikti konkrečią vietą teisės akto dokumente: po # pateikite konkrečią vietą: "#17.2" <br>"""
            "Tais atvejais, kai yra keli dokumentai su priedais: "
            """ "#priedas1/17.2" """
            """ "17.2/17.2.5", """
            """kur "priedas1" yra dokumento failo pavadinimas."""
        ),
    )
    title = forms.CharField(
        label=_("Pavadinimas"),
        required=False,
        help_text=_(
            "Trumpas modelio pavadinimas. Pirmas žodis iš didžiosios raidės, pavadinimo gale taško nereikia. "
            "Pavadinime nereikia kartoti duomenų rinkinio pavadinimo. "
            "Modelio pavadinimas rašomas duomenų rinkinio kontekste."
        ),
    )
    description = forms.CharField(
        label=_("Aprašymas"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        help_text=_("Modelio aprašymas."),
    )

    base = forms.ModelChoiceField(
        label=_("Modelio bazė"),
        required=False,
        queryset=Model.objects.all(),
        widget=BaseWidget(attrs={"data-width": "100%", "data-minimum-input-length": 0}),
        help_text=_(
            "Modelio bazė naudojama objekto identifikatoriams susieti, "
            "kai keli skirtingi duomenų modeliai aprašo tą pačią realaus pasaulio esybę."
        ),
    )
    base_ref = OrderedModelMultipleChoiceField(
        label=_("Pirminis raktas"),
        required=False,
        widget=BaseRefWidget(attrs={"data-width": "100%", "data-minimum-input-length": 0}),
        queryset=Property.objects.all(),
        help_text=_(
            "model.property reikšmė, kurios pagalba model objektai siejami su base objektais. "
            "Jei susiejimas pagal vieną model.property yra neįmanomas, galima nurodyti kelis model.property pavadinimus, "
            "atskirtus kableliu. Galima naudoti tik tuos model.property, kurie neturi nurodyto property.type, "
            "kas reiškia, kad toks pat laukas turi būti tiek base, tiek model laukų sąraše."
        ),
    )
    base_level = forms.ChoiceField(
        label=_("Brandos lygis"),
        required=False,
        widget=forms.RadioSelect,
        choices=BASE_LEVEL_CHOICES,
        help_text=_(
            "Brandos lygis, nurodantis modelio susiejamumą su nurodytu baziniu modeliu. "
            "Plačiau žiūrėti Ryšiai tarp modelių | Brandos lygis. Jei brandos lygis yra žemesnis nei 3, "
            "tada identifikatorių siejimas nėra atliekamas, "
            "tokiu būdu tiesiog nurodomas semantinis susiejimas metaduomenų, o ne duomenų lygmenyje."
        ),
    )

    comment = forms.CharField(
        label=_("Keitimo komentaras"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 6}),
        help_text=_(
            "Pateikiamas komentaras apie šio modelio pakeitimus ar jų priežastis. "
            "Naudinga versijavimui ir bendradarbiavimui."
        ),
    )
    is_parameterized = forms.BooleanField(
        label=_("Parametrizuotas"),
        required=False,
        help_text=_("Žymė, nurodanti ar modelis yra parametrizuotas - t.y. turi dinamiškai kintančių dalių ar filtrų."),
    )

    class Meta:
        model = Metadata
        fields = (
            "name",
            "source",
            "prepare",
            "uri",
            "level",
            "status",
            "visibility",
            "eli",
            "title",
            "description",
            "base",
            "base_ref",
            "base_level",
            "comment",
            "is_parameterized",
        )

    def __init__(self, dataset, metadata_version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset = dataset
        self.metadata_version = metadata_version
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "model-form"
        self.helper.layout = Layout(
            Field("name"),
            Field("source"),
            Field("prepare"),
            Field("uri"),
            Field("level"),
            Field("status"),
            Field("visibility"),
            Field("eli"),
            Field("title"),
            Field("distribution"),
            Field("description"),
            Field("is_parameterized"),
            HTML(f'<hr><h4 class="custom-title mt-5">{_("Modelio bazė")}</h4>'),
            Field("base"),
            Field("base_ref"),
            Field("base_level"),
            HTML(f'<hr><h4 class="custom-title mt-5">{_("Istorija")}</h4>'),
            Field("comment"),
            Submit("submit", _("Sukurti"), css_class="button is-primary"),
        )
        self.fields["distribution"].queryset = (
            DatasetDistribution.objects.exclude(format__extension="UAPI")
            .filter(dataset=dataset)
            .filter(Q(metadata_version=self.metadata_version) | Q(metadata_version__isnull=True))
        )
        self.initial["level"] = "None"
        self.initial["base_level"] = "None"
        self.initial["visibility"] = "None"
        self.initial["status"] = self.instance.status

    def clean_level(self):
        level = self.cleaned_data.get("level")
        if level and level != "None":
            return int(level)
        return None

    def clean_base_level(self):
        level = self.cleaned_data.get("base_level")
        if level and level != "None":
            return int(level)
        return None

    def clean_prepare(self):
        prepare = self.cleaned_data.get("prepare")
        instance = self.instance if self.instance and self.instance.pk else None
        if instance:
            props = instance.object.model_properties.values_list("metadata__name", flat=True)
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
        name = self.cleaned_data.get("name")
        if self.dataset.name:
            metadata_name = self.dataset.name + "/" + name
        else:
            metadata_name = name

        if self.instance and self.instance.pk:
            metadata = Metadata.objects.filter(
                content_type=ContentType.objects.get_for_model(Model),
                name=metadata_name,
                metadata_version=self.metadata_version,
            ).exclude(pk=self.instance.pk)
        else:
            metadata = Metadata.objects.filter(
                content_type=ContentType.objects.get_for_model(Model),
                name=metadata_name,
                metadata_version=self.metadata_version,
            )

        if name:
            if not name[0].isupper():
                raise ValidationError(_("Pirmas kodinio pavadinimo simbolis turi būti didžioji raidė."))
            elif any(not c.isalnum() for c in name):
                raise ValidationError(
                    _("Pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, jokie kiti simboliai negalimi.")
                )
            elif not name.isascii():
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))
            elif metadata:
                raise ValidationError(_("Modelis su tokiu kodiniu pavadinimu jau egzistuoja."))
        return name

    def clean_uri(self):
        uri = self.cleaned_data.get("uri")
        if uri:
            if "://" not in uri and ":" not in uri:
                raise ValidationError(_(f'Nevalidus uri "{uri}" formatas.'))
            if "://" not in uri and ":" in uri:
                parts = uri.split(":")
                if len(parts) != 2:
                    raise ValidationError(_(f'Nevalidus uri "{uri}" formatas.'))
                else:
                    prefix = parts[0]
                    if not Prefix.objects.filter(
                        Q(content_type=None, object_id=None, name=prefix)
                        | Q(metadata__dataset=self.dataset, name=prefix)
                    ).exists():
                        raise ValidationError(_(f'Neatpažintas "{prefix}" prefiksas.'))
        return uri

    def clean_description(self):
        description = self.cleaned_data.get("description")
        if description:
            md = markdown.Markdown()
            try:
                md.convert(description)
            except Exception:
                raise ValidationError(_("Aprašymas neatitinka Markdown formato."))
        return description

    def clean_visibility(self):
        visibility = self.cleaned_data.get("visibility")
        uri = self.cleaned_data.get("uri")

        if visibility == "None":
            return None

        visibility = int(visibility)

        if visibility == Metadata.VISIBILITY_PUBLIC and not uri:
            raise ValidationError(_("Stulpelis 'Klasė' turi būti užpildytas pasirenkant šį metaduomenų matomumo lygį."))

        return visibility


class ModelUpdateForm(ModelCreateForm):
    model_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    ref = OrderedModelMultipleChoiceField(
        label=_("Pirminis raktas"),
        required=False,
        widget=RefWidget(attrs={"data-width": "100%", "data-minimum-input-length": 0}),
        queryset=Property.objects.all(),
    )

    class Meta:
        model = Metadata
        fields = (
            "model_id",
            "name",
            "ref",
            "source",
            "prepare",
            "uri",
            "is_parameterized",
            "level",
            "status",
            "distribution",
            "visibility",
            "eli",
            "title",
            "description",
            "base",
            "base_ref",
            "base_level",
            "comment",
        )

    def __init__(self, dataset, metadata_version, *args, **kwargs):
        super().__init__(dataset, metadata_version, *args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None

        self.helper.layout = Layout(
            Field("model_id"),
            Field("name"),
            Field("ref"),
            Field("source"),
            Field("prepare"),
            Field("uri"),
            Field("level"),
            Field("status"),
            Field("visibility"),
            Field("eli"),
            Field("title"),
            Field("distribution"),
            Field("description"),
            Field("is_parameterized"),
            HTML(f'<hr><h4 class="custom-title mt-5">{_("Modelio bazė")}</h4>'),
            Field("base"),
            Field("base_ref"),
            Field("base_level"),
            HTML(f'<hr><h4 class="custom-title mt-5">{_("Istorija")}</h4>'),
            Field("comment"),
            Submit("submit", _("Redaguoti"), css_class="button is-primary"),
        )

        if instance:
            default_status = Status.objects.filter(is_default=True).first()
            model = instance.object
            self.initial["model_id"] = model.pk
            self.initial["name"] = instance.name.split("/")[-1]
            self.initial["level"] = instance.level_given if instance.level_given is not None else "None"
            self.initial["ref"] = model.property_list.order_by("order").values_list("property", flat=True)
            self.initial["is_parameterized"] = model.is_parameterized
            self.initial["base_level"] = "None"
            self.initial["visibility"] = instance.visibility if instance.visibility is not None else "None"
            self.initial["status"] = instance.status if instance.status is not None else default_status
            self.initial["eli"] = instance.eli
            self.initial["distribution"] = model.distribution_id
            if model.base:
                self.initial["base"] = model.base.model
                self.initial["base_ref"] = model.base.property_list.order_by("order").values_list("property", flat=True)
                if model.base.metadata.first():
                    self.initial["base_level"] = model.base.metadata.first().level_given or "None"


PROPERTY_LEVEL_CHOICES = (
    (None, _get_level_title(_("Nenurodyta"))),
    (
        0,
        _get_level_title(_("Duomenų nėra"), _("Tokių duomenų nėra, tačiau jie yra reikalingi.")),
    ),
    (
        1,
        _get_level_title(
            _("Laisvos formos duomenys"),
            _(
                "Duomenys pateikti nesilaikant vientisumo ar aiškios struktūros, dažnai tai "
                "yra laisvos formos tekstas arba duomenys įvedami ranka."
            ),
        ),
    ),
    (
        2,
        _get_level_title(
            _("Nestandartiniai duomenys"),
            _("Duomenyse išlaikytas vientisumas ir aiški struktūra, tačiau duomenys pateikti nestandartine forma."),
        ),
    ),
    (
        3,
        _get_level_title(
            _("Standartinė forma"),
            _("Duomenys pateikti standartine forma, tačiau nėra nurodyti vienetai ar duomenų tikslumas."),
        ),
    ),
    (
        4,
        _get_level_title(
            _("Identifikatoriai"),
            _("Duomenys susieti su kitais duomenimis, vienetais, klasifikatoriais, nurodytas duomenų tikslumas."),
        ),
    ),
    (
        5,
        _get_level_title(
            _("Standartai"),
            _("Duomenys susieti su standartiniais žodynais/ontologijomis."),
        ),
    ),
)


class PropertyRefWidget(ModelSelect2Widget):
    model = Model
    search_fields = ["metadata__name__icontains", "metadata__title__icontains"]
    dependent_fields = {"dataset_id": "dataset__pk"}

    def label_from_instance(self, obj):
        if obj.title:
            return f"{obj.name} - {obj.title}"
        else:
            return obj.name

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        dataset_id = None
        if "dataset__pk" in dependent_fields:
            dataset_id = dependent_fields.pop("dataset__pk")
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)

        top_models = (
            queryset.annotate(count=Count("ref_model_properties")).order_by("-count")[:5].values_list("pk", flat=True)
        )
        dataset_models = []
        if dataset_id:
            dataset_models = (
                queryset.filter(dataset__pk=dataset_id).exclude(pk__in=top_models).values_list("pk", flat=True)
            )
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
    ("any", _("any")),
    ("pk", _("pk")),
    ("date", _("date")),
    ("time", _("time")),
    ("datetime", _("datetime")),
    ("temporal", _("temporal")),
    ("string", _("string")),
    ("binary", _("binary")),
    ("integer", _("integer")),
    ("number", _("number")),
    ("boolean", _("boolean")),
    ("url", _("url")),
    ("uri", _("uri")),
    ("image", _("image")),
    ("geometry", _("geometry")),
    ("spatial", _("spatial")),
    ("ref", _("ref")),
    ("backref", _("backref")),
    ("generic", _("generic")),
    ("object", _("object")),
    ("file", _("file")),
    ("rql", _("rql")),
    ("json", _("json")),
    ("denorm", _("denorm")),
    ("inherit", _("inherit")),
)


class PropertyForm(forms.ModelForm):
    dataset_id = forms.IntegerField(widget=forms.HiddenInput)
    name = forms.CharField(
        label=_("Kodinis pavadinimas"),
        help_text=_(
            "Duomenų lauko kodinis pavadinimas. "
            "Galimi simboliai: lotyniškos mažosios raidės, skaičiai ir apatinio pabraukimo (`_`) simbolis."
        ),
    )
    type = forms.ChoiceField(
        label=_("Tipas"),
        choices=TYPES,
        help_text=_(
            "Nurodomas loginis duomenų tipas. Loginis duomenų tipas yra toks tipas, "
            "kurį tikitės gauti publikuojant duomenis per API. Loginis tipas gali skirtis nuo duomenų šaltinio tipo."
        ),
    )
    ref = forms.ModelChoiceField(
        label=_("Ryšys"),
        required=False,
        widget=PropertyRefWidget(attrs={"data-width": "100%", "data-minimum-input-length": 0}),
        queryset=Model.objects.all(),
        help_text=_(
            "Priklauso nuo property.type, nurodo matavimo vienetus, laiko ar vietos tikslumą, "
            "klasifikatorių arba ryšį su kitais modeliais."
        ),
    )
    ref_others = forms.CharField(
        label=_("Ryšys"),
        required=False,
        help_text=_("Savybė nurodo sąryšį su papildomais modeliais."),
    )
    source = forms.CharField(
        label=_("Duomenų šaltinis"),
        required=False,
        help_text=_("Duomenų lauko pavadinimas šaltinyje. Prasmė priklauso nuo resource.type."),
    )
    prepare = forms.CharField(
        label=_("Duomenų transformacija"),
        required=False,
        help_text=_("Formulė skirta duomenų tikrinimui ir transformavimui arba statinės reikšmės pateikimui."),
    )
    uri = forms.CharField(label=_("Klasė"), required=False, help_text=_("Sąsaja su išoriniu žodynu."))
    level = forms.ChoiceField(
        label=_("Brandos lygis"),
        required=False,
        widget=forms.RadioSelect,
        choices=PROPERTY_LEVEL_CHOICES,
        help_text=_("Nurodo duomenų lauko brandos lygį."),
    )
    status = ModelChoiceTypeField(
        label=_("Būsena"),
        required=False,
        queryset=(
            Status.objects.exclude(Q(codename__in=["develop", "completed"]) | Q(codename__isnull=True)).order_by("id")
        ),
        widget=forms.RadioSelect,
        help_text=_("Savybė nurodanti modelio metaduomenų gyvavimo ciklo būseną."),
    )
    visibility = forms.ChoiceField(
        label=_("Metaduomenų matomumas"),
        required=False,
        widget=forms.RadioSelect,
        choices=VISIBILITY_LEVEL_CHOICES,
        help_text=_("Savybė nurodanti modelio laukų metaduomenų matomumo ir prieinamumo lygį."),
    )
    access = forms.ChoiceField(
        label=_("Prieigos lygis"),
        required=False,
        choices=AccessType.choices,
        help_text=_("Nurodo prieigos prie duomenų lygį."),
    )
    eli = forms.URLField(
        label=_("Europos teisės akto identifikatorius (ELI)"),
        required=False,
        help_text=_(
            "Teisės akto identifikavimo standartas, leidžiantis nurodyti ne tik patį teisės akto dokumentą, bet ir konkrečią vietą dokumente. <br> "
            """Pateikti konkrečią vietą teisės akto dokumente: po # pateikite konkrečią vietą: "#17.2" <br>"""
            "Tais atvejais, kai yra keli dokumentai su priedais: "
            """ "#priedas1/17.2" """
            """ "17.2/17.2.5", """
            """kur "priedas1" yra dokumento failo pavadinimas."""
        ),
    )
    title = forms.CharField(
        label=_("Pavadinimas"),
        required=False,
        help_text=_(
            "Duomenų lauko pavadinimas. "
            "Šis pavadinimas yra skirtas skaityti žmonėms ir bus rodomas duomenų laukų sąrašuose ir antraštėse. "
            "Jei nenurodyta, bus naudojamas property kodinis pavadinimas."
        ),
    )
    description = forms.CharField(
        label=_("Aprašymas"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        help_text=_("Duomenų lauko aprašymas."),
    )
    type_args = forms.CharField(
        label=_("Tipo parametrai"),
        required=False,
        help_text=_("Nurodo duomenų lauko tipo parametrus."),
    )

    class Meta:
        model = Metadata
        fields = (
            "dataset_id",
            "name",
            "type",
            "type_args",
            "ref",
            "ref_others",
            "source",
            "prepare",
            "uri",
            "level",
            "status",
            "visibility",
            "access",
            "eli",
            "title",
            "description",
        )

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.model = model
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "property-form"
        self.helper.layout = Layout(
            Field("dataset_id"),
            Field("name"),
            Field("type"),
            Field("type_args"),
            Field("ref"),
            Field("ref_others"),
            Field("source"),
            Field("prepare"),
            Field("uri"),
            Field("level"),
            Field("status"),
            Field("visibility"),
            Field("access"),
            Field("eli"),
            Field("title"),
            Field("description"),
            Submit(
                "submit",
                _("Redaguoti") if instance else _("Sukurti"),
                css_class="button is-primary",
            ),
        )

        self.initial["dataset_id"] = self.model.dataset.pk
        self.initial["level"] = "None"
        self.initial["visibility"] = "None"
        self.initial["status"] = Status.objects.filter(is_default=True).first()
        if instance:
            self.initial["level"] = instance.level_given if instance.level_given is not None else "None"
            self.initial["access"] = instance.access
            self.initial["eli"] = instance.eli
            self.initial["visibility"] = instance.visibility if instance.visibility is not None else "None"
            self.initial["status"] = instance.status
            if instance.object.ref_model:
                self.initial["ref"] = instance.object.ref_model
                self.initial["ref_others"] = None
            else:
                self.initial["ref_others"] = instance.ref
                self.initial["ref"] = None

            if self.instance.object not in self.model.get_props_excluding_base():
                self.fields["name"].widget.attrs["readonly"] = True

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name:
            if not name[0].islower():
                raise ValidationError(_("Pirmas kodinio pavadinimo simbolis turi būti mažoji raidė."))
            elif any([ch.isupper() for ch in name]):
                raise ValidationError(_("Kodiniame pavadinime negali būti naudojamos didžiosios raidės."))
            elif any((not c.isalnum() and c != "_") for c in name):
                raise ValidationError(
                    _(
                        "Pavadinime gali būti mažosios raidės ir skaičiai, "
                        "žodžiai gali būti atskirti _ simboliu, "
                        "jokie kiti simboliai negalimi."
                    )
                )
            elif not name.isascii():
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))
        return name

    def clean_level(self):
        level = self.cleaned_data.get("level")
        if level and level != "None":
            return int(level)
        return None

    def clean_prepare(self):
        prepare = self.cleaned_data.get("prepare")
        props = self.model.model_properties.values_list("metadata__name", flat=True)
        if prepare:
            try:
                prepare_ast = spyna.parse(prepare)
            except ParseError as e:
                raise ValidationError(e)
            _check_prepare_ast(prepare_ast, props)
        return prepare

    def clean_uri(self):
        uri = self.cleaned_data.get("uri")
        if uri:
            if "://" not in uri and ":" not in uri:
                raise ValidationError(_(f'Nevalidus uri "{uri}" formatas.'))
            if "://" not in uri and ":" in uri:
                parts = uri.split(":")
                if len(parts) != 2:
                    raise ValidationError(_(f'Nevalidus uri "{uri}" formatas.'))
                else:
                    prefix = parts[0]
                    if not Prefix.objects.filter(
                        Q(content_type=None, object_id=None, name=prefix)
                        | Q(metadata__dataset=self.model.dataset, name=prefix)
                    ).exists():
                        raise ValidationError(_(f'Neatpažintas "{prefix}" prefiksas.'))
        return uri

    def clean_description(self):
        description = self.cleaned_data.get("description")
        if description:
            md = markdown.Markdown()
            try:
                md.convert(description)
            except Exception:
                raise ValidationError(_("Aprašymas neatitinka Markdown formato."))
        return description

    def clean_ref(self):
        type = self.cleaned_data.get("type")
        ref = self.cleaned_data.get("ref")
        if type == "ref" and not ref:
            raise ValidationError(_("Šis laukas yra privalomas."))
        return ref

    def clean_ref_others(self):
        type = self.cleaned_data.get("type")
        ref = self.cleaned_data.get("ref_others") or None
        if ref:
            if type == "date" or type == "datetime":
                if not is_time_unit(ref):
                    raise ValidationError(_("Netinkami matavimo vienetai."))
            elif type == "integer" or type == "number" or type == "geometry":
                if not is_si_unit(ref):
                    raise ValidationError(_("Netinkami matavimo vienetai."))
        return ref

    def clean_access(self):
        access = self.cleaned_data.get("access")
        if access == "":
            return None
        return access

    def clean_visibility(self):
        visibility = self.cleaned_data.get("visibility")
        if visibility == "None":
            return None
        visibility = int(visibility)
        visibility_str = _get_visibility(visibility)

        if metadata := self.model.metadata.first():
            if metadata.visibility is None:
                return visibility
            if int(visibility) > metadata.visibility:
                model_visibility_str = _get_visibility(metadata.visibility)
                raise ValidationError(
                    _("Metaduomenų matomumas '{0}' negali būti didesnis nei duomenų modelio matomumas '{1}'.").format(
                        visibility_str, model_visibility_str
                    )
                )
        return int(visibility)


class ParamForm(forms.ModelForm):
    name = forms.CharField(label=_("Kodinis pavadinimas"))
    prepare = forms.CharField(label=_("Formulė"))

    class Meta:
        model = Metadata
        fields = ("name", "source", "prepare", "title", "description")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "param-form"
        self.helper.layout = Layout(
            Field("name"),
            Field("source"),
            Field("prepare"),
            Field("title"),
            Field("description", rows="2"),
            Submit(
                "submit",
                _("Redaguoti") if instance else _("Sukurti"),
                css_class="button is-primary",
            ),
        )

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name:
            if not name[0].islower():
                raise ValidationError(_("Pirmas kodinio pavadinimo simbolis turi būti mažoji raidė."))
            elif any((not c.isalnum() and c != "_") for c in name):
                raise ValidationError(
                    _(
                        "Pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, "
                        "žodžiai gali būti atskirti _ simboliu,"
                        "jokie kiti simboliai negalimi."
                    )
                )
            elif not name.isascii():
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))
        return name

    def clean_prepare(self):
        prepare = self.cleaned_data.get("prepare")
        if prepare:
            try:
                spyna.parse(prepare)
            except ParseError as e:
                raise ValidationError(e)
        return prepare

    def clean_description(self):
        description = self.cleaned_data.get("description")
        if description:
            md = markdown.Markdown()
            try:
                md.convert(description)
            except Exception:
                raise ValidationError(_("Aprašymas neatitinka Markdown formato."))
        return description


class PublishForm(forms.ModelForm):
    released = forms.DateField(label=_("Įsigalioja"), widget=forms.DateInput(attrs={"type": "date"}))
    metadata = forms.MultipleChoiceField(label=_("Įtraukiama į versiją"), required=False, widget=CheckboxSelectMultiple)
    version_type = forms.ChoiceField(
        label=_("Versijos tipas"),
        required=True,
        choices=VersionType.choices,
        widget=forms.RadioSelect(),
        help_text=_("Pagal semantinio versijų numeravimo (SemVer) principą. Dokumentacija:")
        + " https://atviriduomenys.readthedocs.io/latest/katalogas.html#versijos-tipas",
    )
    related_version = forms.ModelChoiceField(
        label=_("Priklauso versijai"),
        required=False,
        queryset=Version.objects.none(),
    )

    class Meta:
        model = Version
        fields = (
            "released",
            "description",
            "version_type",
        )

    def __init__(self, dataset, metadata_version, *args, **kwargs):
        self.dataset = dataset
        self.metadata_version = metadata_version
        super().__init__(*args, **kwargs)
        latest_versions = []
        major_versions = Version.objects.filter(dataset=self.dataset, version_type=VersionType.MAJOR).order_by("major")

        for major_version in major_versions:
            latest_version_of_major = Version.objects.filter(dataset=self.dataset, major=major_version.major).last()
            latest_versions.append(latest_version_of_major.id)

        self.fields["related_version"].queryset = Version.objects.filter(id__in=latest_versions).order_by("major")

        self.fields["related_version"].label_from_instance = lambda obj: obj.external_version

        all_choices = set(VersionType.choices)
        allowed_types = [VersionType.MAJOR]

        if self.fields["related_version"].queryset.exists():
            allowed_types.append(VersionType.MINOR)
            allowed_types.append(VersionType.PATCH)

        self.fields["version_type"].choices = sorted([choice for choice in all_choices if choice[0] in allowed_types])

        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "version-form"
        self.helper.layout = Layout(
            Field("released"),
            Field("description"),
            Field("version_type"),
            Field("related_version"),
            Field("metadata"),
            Submit("submit", _("Publikuoti"), css_class="button is-primary"),
        )
        self.fields["metadata"].choices = self.dataset.get_metadata_objects_for_version(self.metadata_version)

    def clean(self) -> dict:
        cleaned_data = super().clean()
        version_type = cleaned_data.get("version_type")
        related_version = cleaned_data.get("related_version")

        if (version_type == VersionType.MINOR or version_type == VersionType.PATCH) and not related_version:
            self.add_error("related_version", _("Tėvinė versija turi būti pasirinkta"))

        return cleaned_data

    def clean_released(self):
        released = self.cleaned_data.get("released")
        if released < (datetime.datetime.today().date() + datetime.timedelta(days=14)):
            raise ValidationError(_("Versija gali įsigalioti ne anksčiau kaip po 2 savaičių."))
        latest_version = self.dataset.dataset_version.exclude(status=VersionStatus.DRAFT).order_by("-created").first()
        if latest_version and released < latest_version.released:
            raise ValidationError(_("Versija negali įsigalioti anksčiau už praėjusią versiją."))
        return released

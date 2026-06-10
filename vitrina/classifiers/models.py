from django.db import models
from django.utils.translation import gettext_lazy as _, get_language

from parler.models import TranslatableModel, TranslatedFields
from treebeard.mp_tree import MP_Node, MP_NodeManager

from vitrina.models import UUIDBaseModel


class Category(MP_Node):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1, blank=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    uri = models.CharField(_("Nuoroda į kontroliuojamą žodyną"), max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    title_en = models.CharField(max_length=255, blank=True, null=True)
    edp_title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        "self",
        related_name="children_set",
        null=True,
        db_index=True,
        on_delete=models.SET_NULL,
        editable=False,
    )
    featured = models.BooleanField()
    thematic = models.BooleanField(default=False)
    icon = models.CharField(
        max_length=255,
        blank=True,
        help_text="Piktogramas rasite https://fontawesome.com/search?ic=free.",
    )

    node_order_by = ["title"]

    objects = MP_NodeManager()

    class Meta:
        db_table = "category"

    def __str__(self):
        lang = get_language()
        if lang == "en" and self.title_en:
            return self.title_en
        return self.title

    def get_family_objects(self):
        yield from self.get_ancestors()
        yield from self.get_descendants()


class Licence(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    identifier = models.CharField(unique=True, max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)

    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "licence"

    def __str__(self):
        return self.title


class Frequency(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    title = models.TextField(blank=True, null=True)
    title_en = models.TextField(blank=True, null=True)
    uri = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    hours = models.IntegerField(verbose_name=_("Valandos"), blank=True, null=True)
    code = models.CharField(unique=True, max_length=255, verbose_name="Kodas", null=True, blank=True)

    class Meta:
        db_table = "frequency"
        ordering = ["hours"]

    def __str__(self):
        lang = get_language()
        if lang == "en" and self.title_en:
            return self.title_en
        return self.title


class AreaOfManagement(models.Model):
    name_lt = models.CharField(max_length=255, verbose_name=_("Pavadinimas lietuviškai"), default="Nepriskirta")
    name_en = models.CharField(max_length=255, verbose_name=_("Pavadinimas angliškai"), default="Unassigned")

    class Meta:
        db_table = "area_of_management"
        verbose_name = _("Valdymo sritis")
        verbose_name_plural = _("Valdymo sritys")

    def __str__(self):
        lang = get_language()
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name_lt


class GeoportalCategory(models.Model):
    title = models.CharField(_("Pavadinimas"), max_length=255)
    categories = models.ManyToManyField(Category, verbose_name=_("Atitinkančios kategorijos"), blank=True)

    objects = models.Manager()

    class Meta:
        db_table = "geoportal_category"
        verbose_name = _("Geoportalo kategorija")
        verbose_name_plural = _("Geoportalo kategorijos")

    def __str__(self):
        return self.title


class GeoportalFrequency(models.Model):
    title = models.CharField(_("Pavadinimas"), max_length=255)
    frequency = models.ForeignKey(
        Frequency,
        verbose_name=_("Atitinkantis atnaujinimo periodiškumas"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    objects = models.Manager()

    class Meta:
        db_table = "geoportal_frequency"
        verbose_name = _("Geoportalo atnaujinimo periodiškumas")
        verbose_name_plural = _("Geoportalo atnaujinimo periodiškumai")

    def __str__(self):
        return self.title


class Status(TranslatableModel):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    codename = models.CharField(
        unique=True,
        max_length=255,
        verbose_name=_("Kodinis pavadinimas"),
        help_text=_(
            "Savybė nurodanti prieigos prie metaduomenų lygį. "
            "DCAT-AP rekomenduoja naudoti šias klasifikatoriaus reikšmes: <br>"
            "- develop <br>"
            "- completed <br>"
            "- discont <br>"
            "- deprecated <br>"
            "- withdrawn <br>"
        ),
        blank=True,
        null=True,
    )
    url = models.CharField(
        max_length=512,
        verbose_name=_("Nuoroda į kontroliuojamą EU žodyną"),
        blank=True,
        null=True,
    )
    translations = TranslatedFields(
        name=models.CharField(
            _("Pavadinimas"),
            help_text=_(
                "Būsenos lauko pavadinimas. "
                "Šis pavadinimas yra skirtas skaityti žmonėms ir bus rodomas duomenų laukų sąrašuose ir antraštėse. "
            ),
            unique=True,
            max_length=255,
            blank=False,
        ),
        description=models.CharField(
            _("Aprašymas"),
            help_text=_(
                "Būsenos lauko aprašymas. "
                "Šis aprašymas yra skirtas skaityti žmonėms ir bus rodomas duomenų laukų sąrašuose ir antraštėse. "
            ),
            max_length=255,
            blank=True,
        ),
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "status"
        verbose_name = _("Būsena")
        verbose_name_plural = _("Būsenos")


class ConceptSchema(TranslatableModel, UUIDBaseModel):
    uri = models.CharField(max_length=255, unique=True, verbose_name=_("uri"))

    translations = TranslatedFields(
        label=models.CharField(max_length=255, verbose_name=_("Pavadinimas")),
        description=models.TextField(verbose_name=_("Aprašymas")),
    )

    class Meta:
        verbose_name = _("Sąvokų schema")
        verbose_name_plural = _("Sąvokų schemos")

    def __str__(self) -> str:
        return f"{self.label} ({self.uri})"


class Concept(TranslatableModel, UUIDBaseModel):
    concept_schemas = models.ManyToManyField(
        ConceptSchema,
        related_name="concepts",
        verbose_name=_("Sąvokų schemos"),
    )
    uri = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("uri"))
    code = models.CharField(unique=True, max_length=255, verbose_name=_("Kodinis pavadinimas"))
    valid_since = models.DateField(verbose_name=_("Galioja nuo"))
    valid_until = models.DateField(null=True, blank=True, verbose_name=_("Galioja iki"))

    translations = TranslatedFields(
        label=models.CharField(max_length=255, verbose_name=_("Pavadinimas")),
        description=models.TextField(verbose_name=_("Aprašymas")),
    )

    class Meta:
        verbose_name = _("Sąvoka")
        verbose_name_plural = _("Sąvokos")

    def __str__(self) -> str:
        return self.translated_label

    @property
    def translated_label(self) -> str:
        return self.safe_translation_getter("label", language_code=self.get_current_language()) or self.code


class ApplicableLegislation(UUIDBaseModel):
    description = models.CharField(max_length=255, verbose_name=_("Pavadinimas"), null=True, blank=True)
    url = models.URLField(max_length=255, verbose_name=_("Nuoroda"))

    class Meta:
        verbose_name = _("Teisinis pagrindas")
        verbose_name_plural = _("Teisiniai pagrindai")

    def __str__(self) -> str:
        return self.description or self.url

import re
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from vitrina.datasets.models import Dataset
from vitrina.models import UUIDBaseModel


class Agency(UUIDBaseModel):
    RISR_CODE = "risr"

    class IdentifierValidationType(models.TextChoices):
        REGEXP = "REGEXP", _("Reguliarioji išraiška")

    name = models.CharField(_("Schemos atstovybės pavadinimas"), unique=True, max_length=255)
    code = models.CharField(_("Schemos atstovybės kodas"), unique=True, max_length=100)
    uri = models.URLField(
        unique=True, verbose_name=_("Schemos atstovybės URI"), help_text=_("adms:schemeAgency – schemos atstovybės URI")
    )
    identifier_validation_type = models.CharField(
        _("Identifikatoriaus tikrinimo tipas"),
        choices=IdentifierValidationType.choices,
        default=IdentifierValidationType.REGEXP,
        max_length=100,
        null=True,
        blank=True,
        help_text=_(
            "Pasirinkite metodą, kaip tikrinti identifikatorių formatą. "
            "Reguliarioji išraiška leidžia nustatyti tikslų šabloną."
        ),
    )
    identifier_validation_options = models.CharField(
        _("Identifikatoriaus tikrinimo parinktys"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Tikrinimo parametrai pagal pasirinktą tipą. Reguliariajai išraiškai - įveskite regex šabloną "),
    )

    class Meta:
        verbose_name = _("Atstovybė")
        verbose_name_plural = _("Atstovybės")

    def __str__(self) -> str:
        return self.name

    def clean(self):
        if bool(self.identifier_validation_type) ^ bool(self.identifier_validation_options):
            raise ValidationError(
                _(
                    "Jei nustatytas vienas laukų „Identifikatoriaus tikrinimo tipas“ arba „parinktys“, "
                    "abu turi būti užpildyti."
                )
            )


class Identifier(UUIDBaseModel):
    class IdentifierType(models.TextChoices):
        URI = "URI", _("Nuoroda (URI)")
        LOCAL = "LOCAL", _("Lokalus")
        OTHER = "OTHER", _("Kita")

    resource = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="identifiers", verbose_name=_("Resursas")
    )
    notation = models.CharField(
        max_length=255,
        verbose_name=_("Žymėjimas"),
        help_text=_("skos:notation – identifikatorius išorinėje sistemoje"),
    )
    scheme_agency = models.ForeignKey(
        Agency,
        on_delete=models.PROTECT,
        related_name="identifiers",
        verbose_name=_("Atstovybės"),
    )
    identifier_type = models.CharField(
        max_length=100,
        choices=IdentifierType.choices,
        verbose_name=_("Identifikatoriaus tipas"),
        help_text=_("dct:type – identifikatoriaus tipas"),
    )

    class Meta:
        verbose_name = _("Identifikatorius")
        verbose_name_plural = _("Identifikatoriai")
        constraints = [
            models.UniqueConstraint(
                fields=["resource", "notation", "scheme_agency"], name="unique_identifier_per_scheme_and_resource"
            )
        ]

    def __str__(self) -> str:
        return f"Identifier ({self.identifier_type}) {self.notation} of {self.scheme_agency or '-'}"

    def clean(self):
        super().clean()
        agency = self.scheme_agency
        if not agency.identifier_validation_type or not agency.identifier_validation_options:
            return
        is_regexp = agency.identifier_validation_type == Agency.IdentifierValidationType.REGEXP
        if is_regexp and (pattern := agency.identifier_validation_options) and not re.fullmatch(pattern, self.notation):
            raise ValidationError(
                {"notation": _("Žymėjimas turi atitikti šabloną: %(pattern)s") % {"pattern": pattern}}
            )

    def save(self, *args, **kwargs):
        self.full_clean()  # ensures clean() is called
        super().save(*args, **kwargs)

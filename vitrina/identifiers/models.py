from django.db import models
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import Dataset
from vitrina.models import UUIDBaseModel


class Agency(UUIDBaseModel):
    name = models.CharField(_("Schemos atstovybės pavadinimas"), unique=True, max_length=255)
    uri = models.URLField(
        unique=True, verbose_name=_("Schemos atstovybės URI"), help_text=_("adms:schemeAgency – schemos atstovybės URI")
    )

    class Meta:
        verbose_name = _("Atstovybė")
        verbose_name_plural = _("Atstovybės")

    def __str__(self) -> str:
        return self.name


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

from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from vitrina.models import UUIDBaseModel
from vitrina.projects.models import Project


class SmartContractTemplate(UUIDBaseModel):
    default_template = models.FileField(
        upload_to="data/files/smart_contract_default_templates",
        verbose_name=_("Išmaniųjų sutarčių numatytasis šablonas"),
        validators=[FileExtensionValidator(allowed_extensions=["md"], message=_("Failas turi būti Markdown formato (.md)."))],
    )
    organization = models.ForeignKey(
        "vitrina_orgs.Organization",
        verbose_name=_("Organizacija"),
        on_delete=models.CASCADE,
        help_text=_("Nurodoma organizacija, kuriai priskirtas šablonas."),
        null=True,
        blank=True,
    )


class Agreement(UUIDBaseModel):
    CREATED = "CREATED"
    FORMED = "FORMED"
    INITIATED = "INITIATED"
    SIGNED = "SIGNED"
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"

    STATUSES = (
        (CREATED, _("Pateiktas")),
        (FORMED, _("Suformuotas")),
        (INITIATED, _("Inicijuota")),
        (SIGNED, _("Pasirašyta")),
        (ACTIVE, _("Aktyvi")),
        (DEACTIVATED, _("Nutraukta")),
    )

    use_case = models.ForeignKey(
        Project,
        related_name="agreement_set",
        on_delete=models.PROTECT,
        verbose_name=_("Panaudos atvejis"),
    )
    organization = models.ForeignKey(
        "vitrina_orgs.Organization",
        models.PROTECT,
        verbose_name=_("Organizacija"),
    )
    status = models.CharField(
        max_length=255, choices=STATUSES, blank=False, null=True, verbose_name=_("Statusas")
    )

    agent_sync_enabled = models.BooleanField(default=False, verbose_name=_("Agento sinchronizacija įjungta"))
    last_sync_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Paskutinė sinchronizacijos data"))

    class Meta:
        managed = True
        db_table = "usecase_agreement"
        verbose_name = _("Sutartis")
        verbose_name_plural = _("Sutartys")

    def __str__(self) -> str:
        return f"{self.use_case} - {self.organization} sutartis. Statusas: {self.status}"


class AgreementScope(models.Model):
    agreement = models.ForeignKey(
        Agreement,
        models.PROTECT,
        verbose_name=_("Leidimai"),
    )
    resource = models.CharField(max_length=255, verbose_name=_("Leidimas"))
    action = models.CharField(max_length=255, verbose_name=_("Leidimo veiksmas"))

    class Meta:
        managed = True
        db_table = "usecase_agreement_scope"
        verbose_name = _("Sutarties leidimas")
        verbose_name_plural = _("Sutarties leidimai")

from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from vitrina.models import UUIDBaseModel
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.utils import generate_pdf_checksum


class SmartContractTemplate(UUIDBaseModel):
    default_template = models.FileField(
        upload_to="data/files/smart_contract_default_templates",
        verbose_name=_("Išmaniųjų sutarčių numatytasis šablonas"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=["md"],
                message=_("Failas turi būti Markdown formato (.md)."),
            )
        ],
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
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        verbose_name=_("Panaudojimo atvejis"),
    )
    assigner = models.ForeignKey(
        "vitrina_orgs.Organization",
        on_delete=models.PROTECT,
        verbose_name=_("Duomenis teikianti organizacija"),
    )
    status = models.CharField(
        max_length=255,
        choices=AgreementStatuses.choices,
        default=AgreementStatuses.CREATED,
        verbose_name=_("Būsena"),
    )
    is_agent_sync_enabled = models.BooleanField(
        default=False, verbose_name=_("Agento sinchronizacija įjungta")
    )
    last_sync_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Paskutinės sinchronizacijos data")
    )

    class Meta:
        verbose_name = _("Sutartis")
        verbose_name_plural = _("Sutartys")

    def __str__(self) -> str:
        return f"{self.project} - {self.assigner} sutartis. Statusas: {self.status}"

    def get_acl_parents(self) -> list["Agreement"]:
        return [self]


class AgreementScope(UUIDBaseModel):
    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.PROTECT,
        verbose_name=_("Leidimai"),
    )
    resource = models.CharField(max_length=255, verbose_name=_("Leidimo resursas"))
    action = models.CharField(max_length=255, verbose_name=_("Leidimo veiksmas"))
    scope = models.CharField(max_length=255, verbose_name=_("Leidimas"))

    class Meta:
        verbose_name = _("Sutarties leidimas")
        verbose_name_plural = _("Sutarties leidimai")


class AgreementFile(UUIDBaseModel):
    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.PROTECT,
        verbose_name=_("Sutartis"),
    )
    file_name = models.CharField(max_length=255)
    file = models.FileField(
        upload_to="data/files/agreements",
        verbose_name=_("Sutarties dokumentas"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=["md", "pdf", "adoc"],
                message=_("Dokumentas gali būti md, pdf arba adoc formato."),
            )
        ],
    )
    is_template = models.BooleanField(
        default=False,
        verbose_name=_("Sutarties šablonas"),
    )
    checksum = models.CharField(max_length=128, blank=True,null=True, editable=False)


    class Meta:
        verbose_name = _("Sutarties dokumentas")
        verbose_name_plural = _("Sutarties dokumentai")

    def __str__(self) -> str:
        return f"{self.agreement} - {self.file_name}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.checksum and self.file_name.endswith(".pdf"):
            self.checksum = generate_pdf_checksum(self.file.path)
        return super().save(*args, **kwargs)

import os
from datetime import datetime
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from vitrina.models import UUIDBaseModel
from vitrina.orgs.models import Representative
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.services import generate_contract
from vitrina.smart_contracts.utils import generate_pdf_checksum, format_lithuanian_datetime, generate_checksum
from vitrina.users.models import User


class SmartContractTemplate(UUIDBaseModel):
    file = models.FileField(
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

    def __str__(self) -> str:
        name = os.path.basename(self.file.name)
        if self.organization:
            name += f" ({self.organization.title})"
        return name



class Agreement(UUIDBaseModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="agreements",
        verbose_name=_("Panaudojimo atvejis"),
    )
    assigner = models.ForeignKey(
        "vitrina_orgs.Organization",
        on_delete=models.PROTECT,
        related_name="agreements_as_assigner",
        verbose_name=_("Duomenis teikianti organizacija"),
    )
    assignee = models.ForeignKey(
        "vitrina_orgs.Organization",
        on_delete=models.PROTECT,
        related_name="agreements_as_assignee",
        verbose_name=_("Duomenis gaunanti organizacija"),
    )
    status = models.CharField(
        max_length=255,
        choices=AgreementStatuses.choices,
        default=AgreementStatuses.CREATED,
        verbose_name=_("Būsena"),
    )
    is_agent_sync_enabled = models.BooleanField(default=False, verbose_name=_("Agento sinchronizacija įjungta"))
    last_sync_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Paskutinės sinchronizacijos data"))
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_agreements", verbose_name=_("Sutarties iniciatorius")
    )
    other_assigner_legislations = models.TextField(
        default="", blank=True, verbose_name=_("Papildomi tiekėjo teisės aktai")
    )
    other_assignee_legislations = models.TextField(
        default="", blank=True, verbose_name=_("Papildomi gavėjo teisės aktai")
    )
    payment_terms = models.TextField(default="", blank=True, verbose_name=_("Mokėjimo sąlygos"))

    class Meta:
        verbose_name = _("Sutartis")
        verbose_name_plural = _("Sutartys")

    def __str__(self) -> str:
        return f"{self.project} - {self.assigner} sutartis. Statusas: {self.status}"

    def get_acl_parents(self) -> list["Agreement"]:
        return [self]

    def generate_contract_pdf_file(self, template: SmartContractTemplate) -> "AgreementFile":
        odrl_jsonld = self.generate_odrl_jsonld()
        file_name = slugify(f"{self.project}_{self.assigner}_{self.assignee}_{datetime.now().isoformat()}") + ".pdf"
        pdf_buffer = BytesIO()
        generate_contract(template.file.path, odrl_jsonld, pdf_buffer)
        pdf_buffer.seek(0)

        return self.files.create(
            file=ContentFile(pdf_buffer.read(), name=file_name),
            odrl=odrl_jsonld,
            file_name=file_name,
        )


    def generate_odrl_jsonld(self):
        NON_VALUE = " - "

        assignee_representative: Representative = (
            (Representative.objects.filter(user=self.created_by).first()) if self.created_by else None
        )
        scopes = list(self.scopes.values_list("scope", flat=True))
        return {
            "@context": {"@vocab": "http://www.w3.org/ns/odrl.jsonld", "ex": "http://example.org/vocab#"},
            "uid": f"uuid:{self.pk}",
            "type": "Agreement",
            "profile": "http://www.w3.org/ns/odrl/profile/core",
            "issued": format_lithuanian_datetime(),
            "assigner": [
                {
                    "uid": f"{self.assigner.pk}",
                    "ex:companyName": self.assigner.title,
                    "ex:companyCode": self.assigner.company_code,
                    "ex:address": self.assigner.address,
                    "ex:representative": assignee_representative.email if assignee_representative else NON_VALUE,
                    "ex:email": self.assigner.email or NON_VALUE,
                    "ex:phone": self.assigner.phone or NON_VALUE,
                    "ex:personalCode": NON_VALUE,
                }
            ],
            "assignee": [
                {
                    "uid": f"{self.assignee.pk}",
                    "ex:companyName": self.assignee.title,
                    "ex:companyCode": self.assignee.company_code,
                    "ex:address": self.assignee.address,
                    "ex:representative": NON_VALUE,
                    "ex:email": self.assignee.email or NON_VALUE,
                    "ex:phone": self.assignee.phone or NON_VALUE,
                    "ex:personalCode": NON_VALUE,
                }
            ],
            "permission": [
                {
                    "target": {
                        "uid": dataset.pk,
                        "ex:name": dataset.title,
                        "ex:scopes": scopes,
                    }
                } for dataset in self.project.datasets.filter(organization=self.assigner)

            ],
            "ex:paymentTerms": self.payment_terms or NON_VALUE,
            "ex:otherAssignerLegislations": self.other_assigner_legislations or NON_VALUE,
            "ex:otherAssigneeLegislations": self.other_assignee_legislations or NON_VALUE,
        }


class AgreementScope(UUIDBaseModel):
    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.PROTECT,
        verbose_name=_("Leidimai"),
        related_name="scopes",
    )
    resource = models.CharField(max_length=255, verbose_name=_("Leidimo resursas"))
    action = models.CharField(max_length=255, verbose_name=_("Leidimo veiksmas"))
    scope = models.CharField(max_length=255, verbose_name=_("Leidimas"))

    class Meta:
        verbose_name = _("Sutarties leidimas")
        verbose_name_plural = _("Sutarties leidimai")


class AgreementFile(UUIDBaseModel):
    class AllowedFileTypes(models.TextChoices):
        MD = "md", "Markdown"
        PDF = "pdf", "PDF"
        ADOC = "adoc", "Adoc"

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.PROTECT,
        verbose_name=_("Sutartis"),
        related_name="files",
    )
    file_name = models.CharField(max_length=255)
    file = models.FileField(
        upload_to="data/files/agreements",
        verbose_name=_("Sutarties dokumentas"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=AllowedFileTypes.values,
                message=_("Dokumentas gali būti md, pdf arba adoc formato."),
            )
        ],
    )
    is_template = models.BooleanField(
        default=False,
        verbose_name=_("Sutarties šablonas"),
    )
    checksum = models.CharField(
        max_length=128, blank=True, default="", editable=False, help_text=_("Failo turinio kontrolinė suma.")
    )
    odrl = models.JSONField(
        blank=True, default=dict, help_text=_("ODRL kuris buvo naudotas genertuoti sutartį."), editable=False
    )

    class Meta:
        verbose_name = _("Sutarties dokumentas")
        verbose_name_plural = _("Sutarties dokumentai")

    def __str__(self) -> str:
        return f"{self.agreement} - {self.file_name}"

    @property
    def file_type(self) -> AllowedFileTypes:
        return self.AllowedFileTypes(self.file_name.split(".")[-1])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.checksum and self.file:
            if self.file_type == self.AllowedFileTypes.PDF:
                self.checksum = generate_pdf_checksum(self.file.path)
            else:
                self.checksum = generate_checksum(self.file.read())
            self.save()

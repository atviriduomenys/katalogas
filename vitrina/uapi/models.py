from django.db import models

from vitrina.models import UUIDBaseModel
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from vitrina.uapi import AgentType, ChangedBy, ChangeType, PossibleResults, HTTPMethods, Environment
from django.utils.translation import gettext_lazy as _


class Agent(UUIDBaseModel):
    synchronized_at = models.DateTimeField(
        verbose_name=_("Paskutinės sinchronizacijos data"),
        blank=True,
        null=True,
        help_text=_("Nurodoma data, kada paskutinį kartą buvo bandyta vykdyti sinchronizaciją."),
    )
    is_last_sync_successful = models.BooleanField(
        verbose_name=_("Ar paskutinė sinchronizacija įvyko sėkmingai?"),
        blank=True,
        null=True,
        help_text=_("Nurodoma, ar paskutinė sinchronizacija įvyko sėkmingai t.y. jos metu nekilo klaidų."),
    )
    title = models.CharField(
        verbose_name=_("Pavadinimas"),
        max_length=255,
        help_text=_("Nurodomas Agento pavadinimas."),
    )
    codename = models.CharField(
        verbose_name=_("Kodinis pavadinimas"),
        max_length=255,
        blank=True,
        help_text=_("Nurodomas Agento kodinis pavadinimas."),
    )
    object_type = models.CharField(
        verbose_name=_("Rūšis"),
        max_length=64,
        choices=AgentType.choices,
        default=AgentType.SPINTA,
        help_text=_('Nurodoma Agento rūšis t.y. ar bus naudojama "Spinta" ar kitas sprendimas.'),
    )
    is_open_data_published = models.BooleanField(
        verbose_name=_("Atviri duomenys publikuojami Saugykloje"),
        default=False,
        help_text=_("Nurodo, ar Agentas papildomai publikuoja `access=open` duomenis į atvirų duomenų Saugyklą."),
    )
    open_data_publish_url = models.URLField(
        _("Atvirų duomenų publikavimo nuoroda"),
        max_length=1024,
        blank=True,
        default="https://get.data.gov.lt/",
        help_text=_("Nuoroda, kur turėtų būti publikuojami atviri duomenys."),
    )
    is_enabled = models.BooleanField(
        verbose_name=_("Agentas įjungtas"),
        default=False,
        help_text=_("Nurodoma, ar Agentas yra įjungtas ar išjungtas."),
    )
    is_archived = models.BooleanField(
        verbose_name=_("Agentas archyvuotas"),
        default=False,
        help_text=_(
            "Nurodo ar Agentas yra archyvuotas. Archyvuoti agentai nėra pasiekiami įprastiems platformos vartotojams"
        ),
    )
    service = models.ForeignKey(
        "vitrina_datasets.Dataset",
        verbose_name=_("Duomenų paslauga"),
        on_delete=models.CASCADE,
        help_text=_("Nurodoma su Agentu susieta duomenų paslauga. Atitinka DCAT:DataService."),
    )
    organization = models.ForeignKey(
        "vitrina_orgs.Organization",
        verbose_name=_("Organizacija"),
        on_delete=models.CASCADE,
        help_text=_("Nurodoma organizacija, kuriai priskirtas Agentas."),
    )
    oauth_client_id = models.CharField(
        verbose_name=_("Autorizacijos kliento identifikatorius"),
        max_length=255,
        blank=True,
        help_text=_("Jei kliento identifikatorius egzistuoja - agentas gali vykdyti užklausas į katalogą."),
    )
    environment = models.CharField(
        verbose_name=_("Aplinka"),
        max_length=32,
        choices=Environment.choices,
        default=Environment.DEVELOPMENT,
        help_text=_("Aplinka, kurioje diegiamas agentas."),
    )
    auth_server_url = models.URLField(
        verbose_name=_("Autorizacijos serverio adresas"),
        max_length=255,
        blank=True,
        help_text=_("Nurodomas autorizacijos serverio adresas."),
    )
    api_gate_server_url = models.URLField(
        verbose_name=_("API vartų serverio adresas"),
        max_length=255,
        blank=True,
        help_text=_("Nurodomas API vartų serverio adresas."),
    )
    agent_address = models.CharField(
        verbose_name=_("Agento adresas"),
        max_length=255,
        blank=True,
        help_text=_(
            "Jei yra nurodytas vartų adresas, tada agento adresas yra vidinis adresas, kurį mato API vartai. Jei API vartai nenurodyti, tada yra nurodomas išorinis agento adresas"
        ),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["codename", "organization"],
                condition=models.Q(is_archived=False),
                name="unique_name_and_organization_for_not_archived_agents",
            )
        ]

    def save(self, *args, **kwargs) -> None:
        self.codename = self.get_codename(self.title)

        if (update_fields := kwargs.get("update_fields")) and "title" in update_fields:
            kwargs["update_fields"] = set(update_fields) | {"codename"}

        if not self.service.service:
            raise ValidationError(_('Susietas duomenų išteklius turi būti "paslaugos" tipo.'))

        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.title} ({self.codename})"

    @staticmethod
    def get_codename(title: str) -> str:
        return slugify(title).replace("-", "_")

    @property
    def global_codename(self) -> str:
        return f"{self.codename}_{self.organization_id}"


class RequestHistory(UUIDBaseModel):
    agent = models.ForeignKey(
        "vitrina_uapi.Agent", on_delete=models.CASCADE, verbose_name=_("Agentas"), related_name="requesthistory"
    )
    endpoint = models.CharField(max_length=255, verbose_name=_("API galinis taškas"))
    method = models.CharField(max_length=10, choices=HTTPMethods.choices, verbose_name=_("HTTP metodas"))
    http_result = models.IntegerField(verbose_name=_("HTTP rezultatas"))
    result = models.CharField(max_length=30, choices=PossibleResults.choices, verbose_name=_("Rezultatas"))
    details = models.TextField(blank=True, null=True, verbose_name=_("Informacija"))
    error = models.TextField(blank=True, null=True, verbose_name=_("Klaida"))

    class Meta:
        verbose_name = _("Užklausų istorija")
        verbose_name_plural = _("Užklausų istorijos")


class RequestHistoryChanges(UUIDBaseModel):
    request_history = models.ForeignKey(
        "RequestHistory", on_delete=models.CASCADE, related_name="changes", verbose_name=_("Užklausų istorija")
    )
    element = models.ForeignKey("vitrina_structure.Metadata", on_delete=models.CASCADE, verbose_name=_("Elementas"))
    changed_by = models.CharField(max_length=255, choices=ChangedBy.choices, verbose_name=_("Pakeitimo autorius"))
    change_type = models.CharField(max_length=255, choices=ChangeType.choices, verbose_name=_("Pakeitimo tipas"))

    class Meta:
        verbose_name = _("Užklausų istorijos pakeitimas")
        verbose_name_plural = _("Užklausų istorijos pakeitimai")

from django.db import models

from vitrina.models import UUIDBaseModel
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from vitrina.uapi import AgentType
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
        help_text=_('Nurodoma Agento rūšis t.y. ar bus naudojama "Spinta" ar kitas sprendimas.')
    )
    is_open_data_published = models.BooleanField(
        verbose_name=_("Atviri duomenys publikuojami Saugykloje"),
        default=False,
        help_text=_("Nurodo, ar Agentas papildomai publikuoja `access=open` duomenis į atvirų duomenų Saugyklą.")
    )
    open_data_publish_url = models.URLField(
        _("Atvirų duomenų publikavimo nuoroda"),
        max_length=1024,
        blank=True,
        default="https://get.data.gov.lt/",
        help_text=_("Nuoroda, kur turėtų būti publikuojami atviri duomenys.")
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
        )
    )
    service = models.ForeignKey(
        "vitrina_datasets.Dataset",
        verbose_name=_("Duomenų paslauga"),
        on_delete=models.CASCADE,
        help_text=_("Nurodoma su Agentu susieta duomenų paslauga."),
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


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["codename", "organization"],
                condition=models.Q(is_archived=False),
                name="unique_name_and_organization_for_not_archived_agents"
            )
        ]


    def save(self, *args, **kwargs) -> None:
        self.codename = self.get_codename(self.title)

        if not self.service.service:
            raise ValidationError(_('Susietas duomenų išteklius turi būti "paslaugos" tipo.'))

        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.title} ({self.codename})"

    @staticmethod
    def get_codename(title: str) -> str:
        return slugify(title).replace('-', '_')

    @property
    def global_codename(self) -> str:
        return f"{self.codename}_{self.organization_id}"
    
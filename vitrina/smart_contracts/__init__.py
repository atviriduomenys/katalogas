from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class AgreementStatuses(TextChoices):
    CREATED = "CREATED", _("Sukurta")
    SUBMITTED = "SUBMITTED", _("Pateikta")
    APPROVED = "APPROVED", _("Patvirtinta")
    FORMED = "FORMED", _("Suformuota")
    INITIATED = "INITIATED", _("Inicijuota")
    SIGNED = "SIGNED", _("Pasirašyta")
    ACTIVE = "ACTIVE", _("Aktyvi")
    TERMINATED = "TERMINATED", _("Nutraukta")


AGREEMENT_STATUS_DESCRIPTIONS = {
    AgreementStatuses.CREATED: _("Sutartis sukurta. Sutarties dokumentas dar nesukurtas."),
    AgreementStatuses.SUBMITTED: _("Pateiktas pasiūlymas iš duomenų gavėjo pusės."),
    AgreementStatuses.APPROVED: _("Duomenų gavėjo pasiūlymas duomenims gauti yra patvirtintas duomenų teikėjo."),
    AgreementStatuses.FORMED: _("Sutarties dokumentas sukurtas, bet nepasirašytas."),
    AgreementStatuses.INITIATED: _("Sutarties dokumentas pasirašytas duomenų gavėjo."),
    AgreementStatuses.SIGNED: _("Sutarties dokumentas pasirašytas duomenų gavėjo ir duomenų teikėjo."),
    AgreementStatuses.ACTIVE: _("Sutartis sėkmingai sinchronizuota su agentu."),
    AgreementStatuses.TERMINATED: _("Sutartis nutraukta."),
}

from django.conf import settings
from django.db import migrations, models

import parler.fields
import parler.models


FOUR_DIGIT_PATTERN = r"^\d{4}$"
FOUR_DIGIT_MESSAGE = "Žymėjimas turi būti sudarytas iš keturių skaitmenų."
DEFAULT_REGEXP_MESSAGE_TEMPLATE = (
    "Žymėjimas neatitinka reikalaujamo šablono „{pattern}“. "
    "Šablono formatą galima patikrinti naudojant įrankį: https://regex101.com/"
)


class MakeAgencyTranslatableInState(migrations.operations.base.Operation):
    """Add parler's TranslatableModelMixin to Agency's bases in migration state.

    Needed so that the AgencyTranslation FK can attach to Agency during migration
    state processing (parler asserts the master inherits from TranslatableModel).
    Purely a state-level change — no DB effect.
    """

    reduces_to_sql = False
    reversible = True

    def state_forwards(self, app_label, state):
        model_state = state.models[app_label, "agency"]
        model_state.bases = (parler.models.TranslatableModelMixin, models.Model)
        state.reload_model(app_label, "agency")

    def state_backwards(self, app_label, state):
        model_state = state.models[app_label, "agency"]
        model_state.bases = (models.Model,)
        state.reload_model(app_label, "agency")

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def describe(self):
        return "Mark Agency as translatable in migration state"


def _configured_language_codes():
    parler_languages = getattr(settings, "PARLER_LANGUAGES", {}) or {}
    codes = []
    for key, value in parler_languages.items():
        if key == "default":
            continue
        for entry in value:
            code = entry.get("code")
            if code and code not in codes:
                codes.append(code)
    return codes or ["lt"]


def prefill_error_messages(apps, schema_editor):
    Agency = apps.get_model("vitrina_identifiers", "Agency")
    AgencyTranslation = apps.get_model("vitrina_identifiers", "AgencyTranslation")

    language_codes = _configured_language_codes()

    for agency in Agency.objects.filter(identifier_validation_type="REGEXP"):
        if agency.identifier_validation_options == FOUR_DIGIT_PATTERN:
            message = FOUR_DIGIT_MESSAGE
        else:
            message = DEFAULT_REGEXP_MESSAGE_TEMPLATE.format(pattern=agency.identifier_validation_options)

        for language_code in language_codes:
            AgencyTranslation.objects.update_or_create(
                master=agency,
                language_code=language_code,
                defaults={"identifier_validation_error_message": message},
            )


class Migration(migrations.Migration):

    dependencies = [
        ("vitrina_identifiers", "0005_add_pasis_agency"),
    ]

    operations = [
        MakeAgencyTranslatableInState(),
        migrations.CreateModel(
            name="AgencyTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language_code", models.CharField(db_index=True, max_length=15, verbose_name="Language")),
                (
                    "identifier_validation_error_message",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Pranešimas, rodomas naudotojui, kai identifikatorius neatitinka nustatyto šablono. "
                            "Privalomas, kai pasirinkta reguliarioji išraiška."
                        ),
                        null=True,
                        verbose_name="Identifikatoriaus tikrinimo klaidos pranešimas",
                    ),
                ),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=models.CASCADE,
                        related_name="translations",
                        to="vitrina_identifiers.agency",
                    ),
                ),
            ],
            options={
                "verbose_name": "Atstovybė Translation",
                "db_table": "vitrina_identifiers_agency_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.RunPython(prefill_error_messages, reverse_code=migrations.RunPython.noop),
    ]

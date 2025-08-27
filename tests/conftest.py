import builtins
from datetime import date

import pytest

from django.apps import apps
from django.core.management import call_command

from pytest_django.lazy_django import skip_if_no_django

from pprintpp import pprint as pp

from vitrina.classifiers.models import Concept, ConceptSchema
from vitrina.datasets.models import DCATResourceSubclass

builtins.pp = pp


@pytest.fixture(scope="session", autouse=True)
def manage_unmanaged_models():
    unmanaged_models = [m for m in apps.get_models() if not m._meta.managed]
    for model in unmanaged_models:
        model._meta.managed = True
    yield
    for model in unmanaged_models:
        model._meta.managed = False


@pytest.fixture()
def app(django_app_factory):
    yield django_app_factory(csrf_checks=False)


def pytest_configure(config):
    config.addinivalue_line("markers", "haystack: use a search index")


@pytest.fixture(autouse=True)
def _haystack_marker(request):
    if request.keywords.get("haystack"):
        # Skip if Django is not configured
        skip_if_no_django()

        # Haystack requires database
        request.getfixturevalue("db")

        # Switch to test index
        settings = request.getfixturevalue("settings")
        settings.HAYSTACK_CONNECTIONS = {
            "default": settings.HAYSTACK_CONNECTIONS["test"],
        }

        call_command("clear_index", interactive=False, using=["default"])


@pytest.fixture(autouse=True)
def ensure_default_subclasses(db):
    obj, _ = DCATResourceSubclass.objects.get_or_create(name="dataset")
    if not obj.has_translation("lt"):
        obj.set_current_language("lt")
        obj.title = "Duomenų rinkinys"
        obj.save()

    obj2, _ = DCATResourceSubclass.objects.get_or_create(name="service")
    if not obj2.has_translation("lt"):
        obj2.set_current_language("lt")
        obj2.title = "Duomenų publikavimo paslauga"
        obj2.save()


# TODO: remove this after the pipeline starts running migrations before testing
@pytest.fixture(autouse=True)
def ensure_needed_concepts_exist():
    schema, _ = ConceptSchema.objects.get_or_create(
        uri="http://publications.europa.eu/resource/authority/distribution-status"
    )

    concepts_data = [
        {
            "uri": "http://publications.europa.eu/resource/authority/distribution-status/COMPLETED",
            "code": "COMPLETED",
            "valid_since": date(2015, 10, 23),
            "translations": {
                "en": {
                    "label": "Completed",
                    "description": "This distribution is considered to be complete, it holds all information that is intended.",
                },
                "lt": {
                    "label": "Įgyvendintas – veikiantis",
                    "description": "Ši distribucija laikoma įgyvendinta – veikiančia, joje yra visa reikiama informacija.",
                },
            },
        },
        {
            "uri": "http://publications.europa.eu/resource/authority/distribution-status/DEVELOP",
            "code": "DEVELOP",
            "valid_since": date(2015, 10, 23),
            "translations": {
                "en": {
                    "label": "Under development",
                    "description": "This distribution is currently being assembled. It may be in an incomplete or faulty state.",
                },
                "lt": {
                    "label": "Kuriamas",
                    "description": "Ši distribucija yra kuriama. Ji gali būti nebaigta arba klaidinga.",
                },
            },
        },
        {
            "code": "PLANNED",
            "valid_since": date(2019, 1, 1),
            "translations": {
                "en": {
                    "label": "Development planned",
                    "description": "The development of this distribution is planned.",
                },
                "lt": {"label": "Kūrimas suplanuotas", "description": "Šios distribucijos kūrimas suplanuotas."},
            },
        },
    ]

    for data in concepts_data:
        concept, created = Concept.objects.get_or_create(
            code=data["code"],
            defaults={
                "uri": data.get("uri"),
                "valid_since": data["valid_since"],
            },
        )
        if created:
            for lang, fields in data["translations"].items():
                concept.set_current_language(lang)
                concept.label = fields["label"]
                concept.description = fields["description"]
            concept.save()
        concept.concept_schemas.add(schema)

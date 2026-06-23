import pytest
from django.utils import timezone

from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution

EMPTY_TITLE = {"en": "", "lt": ""}


@pytest.mark.django_db
def test_data_last_updated_field_is_nullable():
    distribution = DatasetDistributionFactory()
    distribution.data_last_updated = None
    distribution.save(update_fields=["data_last_updated"])
    distribution.refresh_from_db()
    assert distribution.data_last_updated is None


@pytest.mark.django_db
def test_display_title_returns_title_when_set():
    distribution = DatasetDistributionFactory(title={"en": "My distribution", "lt": "Mano pateiktis"})
    distribution.set_current_language("lt")
    assert distribution.display_title == "Mano pateiktis"


@pytest.mark.django_db
def test_display_title_falls_back_to_access_url():
    distribution = DatasetDistributionFactory(title=EMPTY_TITLE, access_url="https://example.com/data")
    assert distribution.display_title == "https://example.com/data"


@pytest.mark.django_db
def test_display_title_falls_back_to_id():
    distribution = DatasetDistributionFactory(title=EMPTY_TITLE)
    assert distribution.display_title == f"#{distribution.pk}"


@pytest.mark.django_db
def test_data_last_updated_save_does_not_trigger_auto_now_on_modified():
    distribution = DatasetDistributionFactory()
    original_modified = distribution.modified

    distribution.data_last_updated = timezone.now()
    DatasetDistribution.objects.bulk_update([distribution], ["data_last_updated"])

    distribution.refresh_from_db()
    assert distribution.modified == original_modified

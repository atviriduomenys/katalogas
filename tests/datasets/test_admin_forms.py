from typing import Collection

import pytest
from vitrina.datasets.admin_forms import QualityAnnotationAdminForm
from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory

pytestmark = pytest.mark.django_db


class TestQualityAnnotationAdminFormClean:
    def _form_data(self, datasets: Collection = (), distributions: Collection = ()):
        return {
            "codename": "accuracy",
            "has_target_dataset": [d.pk for d in datasets],
            "has_target_distribution": [d.pk for d in distributions],
        }

    def test_both_filled_is_invalid(self):
        dataset = DatasetFactory()
        distribution = DatasetDistributionFactory()

        form = QualityAnnotationAdminForm(data=self._form_data([dataset], [distribution]))

        assert not form.is_valid()
        assert form.non_field_errors() == ["Pasirinkite arba duomenų rinkinį, arba pateiktį — ne abu."]

    def test_neither_filled_is_invalid(self):
        form = QualityAnnotationAdminForm(data=self._form_data())

        assert not form.is_valid()
        assert form.non_field_errors() == ["Būtina pasirinkti arba duomenų rinkinį, arba pateiktį."]

    def test_only_dataset_is_valid(self):
        dataset = DatasetFactory()

        form = QualityAnnotationAdminForm(data=self._form_data([dataset]))

        assert form.is_valid(), form.errors

    def test_only_distribution_is_valid(self):
        dist = DatasetDistributionFactory()

        form = QualityAnnotationAdminForm(data=self._form_data(distributions=[dist]))

        assert form.is_valid(), form.errors

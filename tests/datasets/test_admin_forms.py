from typing import Collection

import pytest
from django.forms import inlineformset_factory
from vitrina.datasets.admin_forms import QualityAnnotationAdminForm, QualityMeasurementAdminForm
from vitrina.datasets.admin import MeasurementTitleItemInline
from vitrina.datasets.factories import (
    DatasetFactory,
    MeasurementFactory,
    MeasurementTitleFactory,
    DCATResourceSubclassFactory,
)
from vitrina.datasets.models import DCATResourceSubclass, Measurement, MeasurementTitleItem
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


class TestQualityMeasurementAdminFormClean:
    def _form_data(self, measurements: Collection = (), datasets: Collection = (), distributions: Collection = ()):
        return {
            "codename": "codename_001",
            "is_measurement_of": [measurement.pk for measurement in measurements],
            "computed_on_dataset": [dataset.pk for dataset in datasets],
            "computed_on_distribution": [distribution.pk for distribution in distributions],
        }

    def _dataset_subclass(self) -> DCATResourceSubclass:
        return DCATResourceSubclassFactory(name=DCATResourceSubclass.DATASET)

    def test_all_fields_missing_is_invalid(self):
        form = QualityMeasurementAdminForm(data=self._form_data())

        assert not form.is_valid()
        errors = form.non_field_errors()
        assert "Turi būti nurodytas bent vienas matavimo rodiklis." in errors
        assert "Turi būti nurodytas bent vienas duomenų rinkinys." in errors
        assert "Turi būti nurodyta bent viena pateiktis." in errors

    def test_missing_is_measurement_of_is_invalid(self):
        dataset = DatasetFactory(subclass=self._dataset_subclass())
        distribution = DatasetDistributionFactory()

        form = QualityMeasurementAdminForm(data=self._form_data(datasets=[dataset], distributions=[distribution]))

        assert not form.is_valid()
        assert "Turi būti nurodytas bent vienas matavimo rodiklis." in form.non_field_errors()

    def test_missing_computed_on_dataset_is_invalid(self):
        measurement = MeasurementFactory()
        distribution = DatasetDistributionFactory()

        form = QualityMeasurementAdminForm(
            data=self._form_data(measurements=[measurement], distributions=[distribution])
        )

        assert not form.is_valid()
        assert "Turi būti nurodytas bent vienas duomenų rinkinys." in form.non_field_errors()

    def test_missing_computed_on_distribution_is_invalid(self):
        measurement = MeasurementFactory()
        dataset = DatasetFactory(subclass=self._dataset_subclass())

        form = QualityMeasurementAdminForm(data=self._form_data(measurements=[measurement], datasets=[dataset]))

        assert not form.is_valid()
        assert "Turi būti nurodyta bent viena pateiktis." in form.non_field_errors()

    def test_all_fields_filled_is_valid(self):
        measurement = MeasurementFactory()
        dataset = DatasetFactory(subclass=self._dataset_subclass())
        distribution = DatasetDistributionFactory()

        form = QualityMeasurementAdminForm(
            data=self._form_data(measurements=[measurement], datasets=[dataset], distributions=[distribution])
        )

        assert form.is_valid(), form.errors


class TestMeasurementTitleItemInline:
    def _make_formset_class(self):
        return inlineformset_factory(
            Measurement,
            MeasurementTitleItem,
            fields="__all__",
            min_num=MeasurementTitleItemInline.min_num,
            validate_min=MeasurementTitleItemInline.validate_min,
            extra=0,
        )

    def test_zero_titles_is_invalid(self):
        measurement = MeasurementFactory()
        FormSet = self._make_formset_class()
        prefix = FormSet(instance=measurement).prefix
        data = {
            f"{prefix}-TOTAL_FORMS": "0",
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "1",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }

        assert not FormSet(data=data, instance=measurement).is_valid()

    def test_one_title_is_valid(self):
        measurement = MeasurementFactory()
        title = MeasurementTitleFactory()
        item = MeasurementTitleItem.objects.create(measurement=measurement, title=title)
        FormSet = self._make_formset_class()
        prefix = FormSet(instance=measurement).prefix
        data = {
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "1",
            f"{prefix}-MIN_NUM_FORMS": "1",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-id": str(item.pk),
            f"{prefix}-0-measurement": str(measurement.pk),
            f"{prefix}-0-title": str(title.pk),
        }

        assert FormSet(data=data, instance=measurement).is_valid()

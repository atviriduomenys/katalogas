from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import QualityAnnotation, QualityMeasurement


class QualityAnnotationAdminForm(forms.ModelForm):
    class Meta:
        model = QualityAnnotation
        fields = "__all__"

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        has_dataset = bool(cleaned.get("has_target_dataset"))
        has_distribution = bool(cleaned.get("has_target_distribution"))
        if has_dataset and has_distribution:
            raise forms.ValidationError(_("Pasirinkite arba duomenų rinkinį, arba pateiktį — ne abu."))
        if not has_dataset and not has_distribution:
            raise forms.ValidationError(_("Būtina pasirinkti arba duomenų rinkinį, arba pateiktį."))
        return cleaned


class QualityMeasurementAdminForm(forms.ModelForm):
    class Meta:
        model = QualityMeasurement
        fields = "__all__"

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        has_is_measurement_of = bool(cleaned.get("is_measurement_of"))
        has_computed_on_dataset = bool(cleaned.get("computed_on_dataset"))
        has_computed_on_distribution = bool(cleaned.get("computed_on_distribution"))

        errors = []
        if not has_is_measurement_of:
            errors.append(_("Turi būti nurodytas bent vienas matavimo rodiklis."))
        if not has_computed_on_dataset:
            errors.append(_("Turi būti nurodytas bent vienas duomenų rinkinys."))
        if not has_computed_on_distribution:
            errors.append(_("Turi būti nurodyta bent viena pateiktis."))

        if errors:
            raise forms.ValidationError(errors)

        return cleaned

from typing import Any

from django import forms

from vitrina.datasets.models import QualityAnnotation


class QualityAnnotationAdminForm(forms.ModelForm):
    class Meta:
        model = QualityAnnotation
        fields = "__all__"

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        has_dataset = bool(cleaned.get("has_target_dataset"))
        has_dist = bool(cleaned.get("has_target_distribution"))
        if has_dataset and has_dist:
            raise forms.ValidationError("Pasirinkite arba duomenų rinkinį, arba pateiktį — ne abu.")
        if not has_dataset and not has_dist:
            raise forms.ValidationError("Būtina pasirinkti arba duomenų rinkinį, arba pateiktį.")
        return cleaned

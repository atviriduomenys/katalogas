import pytest
from django.utils.translation import override as translation_override

from vitrina.classifiers.factories import ConceptFactory
from vitrina.classifiers.models import Concept

pytestmark = pytest.mark.django_db


def _set_label(concept: Concept, lang: str, label: str, description: str = "desc") -> Concept:
    concept.set_current_language(lang)
    concept.label = label
    concept.description = description
    concept.save()
    return concept


class TestConceptOrderedByLabelManager:
    def test_concepts_ordered_alphabetically_by_translated_label(self):
        concept1 = _set_label(ConceptFactory(code="c_zebra"), "lt", "Zebra")
        concept2 = _set_label(ConceptFactory(code="c_apple"), "lt", "Apple")
        concept3 = _set_label(ConceptFactory(code="c_mango"), "lt", "Mango")

        with translation_override("lt"):
            ordered_ids = list(
                Concept.ordered_by_label_objects.filter(pk__in=[concept1.pk, concept2.pk, concept3.pk]).values_list(
                    "pk", flat=True
                )
            )

        assert ordered_ids == [concept2.pk, concept3.pk, concept1.pk]

    def test_falls_back_to_code_when_no_translation_for_current_language(self):
        concept_with_label = _set_label(ConceptFactory(code="zzz_code"), "lt", "Apple")
        concept_no_label = ConceptFactory(code="aaa_code")

        with translation_override("lt"):
            ordered_ids = list(
                Concept.ordered_by_label_objects.filter(
                    pk__in=[concept_with_label.pk, concept_no_label.pk]
                ).values_list("pk", flat=True)
            )

        assert ordered_ids == [concept_no_label.pk, concept_with_label.pk]

    def test_ordering_uses_current_language(self):
        concept1 = ConceptFactory(code="c_lang1")
        concept2 = ConceptFactory(code="c_lang2")
        _set_label(concept1, "lt", "Zebra")
        _set_label(concept2, "lt", "Apple")
        _set_label(concept1, "en", "Apple")
        _set_label(concept2, "en", "Zebra")

        with translation_override("lt"):
            lt_ids = list(
                Concept.ordered_by_label_objects.filter(pk__in=[concept1.pk, concept2.pk]).values_list("pk", flat=True)
            )

        with translation_override("en"):
            en_ids = list(
                Concept.ordered_by_label_objects.filter(pk__in=[concept1.pk, concept2.pk]).values_list("pk", flat=True)
            )

        assert lt_ids == [concept2.pk, concept1.pk]
        assert en_ids == [concept1.pk, concept2.pk]

    def test_sort_label_annotation_is_code_when_no_translation(self):
        concept = ConceptFactory(code="my_code")

        with translation_override("lt"):
            result = Concept.ordered_by_label_objects.filter(pk=concept.pk).values("_sort_label").first()

        assert result["_sort_label"] == "my_code"

    def test_sort_label_annotation_is_translated_label_when_translation_exists(self):
        concept = _set_label(ConceptFactory(code="irrelevant_code"), "lt", "My Label")

        with translation_override("lt"):
            result = Concept.ordered_by_label_objects.filter(pk=concept.pk).values("_sort_label").first()

        assert result["_sort_label"] == "My Label"

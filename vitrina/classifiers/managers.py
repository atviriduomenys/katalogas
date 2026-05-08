from django.db.models import OuterRef, Subquery, QuerySet
from django.db.models.functions import Coalesce
from django.utils.translation import get_language
from parler.managers import TranslatableManager


class ConceptOrderedByLabelManager(TranslatableManager):
    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        language = get_language()
        translation_model = queryset.model._parler_meta.root_model
        label_subquery = Subquery(
            translation_model.objects.filter(master_id=OuterRef("pk"), language_code=language).values("label")[:1]
        )
        return queryset.annotate(_sort_label=Coalesce(label_subquery, "code")).order_by("_sort_label")

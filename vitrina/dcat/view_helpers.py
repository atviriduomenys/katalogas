from typing import TYPE_CHECKING

from django.contrib import messages
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import (
    Attribution,
    Dataset,
    DatasetAttribution,
    DatasetQualifiedRelation,
    DatasetRelation,
    Relation,
)

if TYPE_CHECKING:
    from vitrina.dcat.forms.dataset_forms import BaseResourceForm

RELATION_FIELD_MAP = [
    # (field_name, relation_name, is_inverse)
    ("has_part", Relation.CATALOG, False),
    ("relates_to_information_system", Relation.RELATES_TO_INFORMATION_SYSTEM, True),
    ("related_information_system", Relation.RELATES_TO_INFORMATION_SYSTEM, False),
    ("serves_datasets", Relation.SERVICE, False),
]


@transaction.atomic
def save_dataset_relations(request: WSGIRequest, dataset: Dataset, form: "BaseResourceForm") -> None:
    for field_name, relation_name, is_inverse in RELATION_FIELD_MAP:
        if field_name not in form.cleaned_data or field_name not in form.changed_data:
            continue

        try:
            relation = Relation.objects.get(name=relation_name)
        except Relation.DoesNotExist:
            warning_message = _(
                "Lauko '{label}' ryšio tipas '{relation_name}' nerastas, todėl šio lauko reikšmė neišsaugota. "
                "Susisiekite su administratoriumi."
            ).format(label=form.fields[field_name].label, relation_name=relation_name)
            messages.warning(request, warning_message)
            continue

        selected_datasets = form.cleaned_data[field_name]

        if is_inverse:
            DatasetRelation.objects.filter(relation=relation, part_of=dataset).delete()
            for selected_dataset in selected_datasets:
                dataset_relation = DatasetRelation.objects.create(
                    relation=relation, dataset=selected_dataset, part_of=dataset
                )
                selected_dataset.part_of.add(dataset_relation)
        else:
            DatasetRelation.objects.filter(relation=relation, dataset=dataset).delete()
            for selected_dataset in selected_datasets:
                dataset_relation = DatasetRelation.objects.create(
                    relation=relation, dataset=dataset, part_of=selected_dataset
                )
                dataset.part_of.add(dataset_relation)

    dataset.save()


@transaction.atomic
def save_dataset_attribution(request: WSGIRequest, dataset: Dataset, form: "BaseResourceForm") -> None:
    if "qualified_attribution" not in form.cleaned_data or "qualified_attribution" not in form.changed_data:
        return

    try:
        attribution = Attribution.objects.get(name=Attribution.CONTRIBUTOR)
    except Attribution.DoesNotExist:
        messages.warning(
            request,
            _(
                "Priskyrimo tipas '{name}' nerastas, todėl priskyrimo reikšmė neišsaugota. "
                "Susisiekite su administratoriumi."
            ).format(name=Attribution.CONTRIBUTOR),
        )
        return

    selected_organizations = form.cleaned_data["qualified_attribution"]
    DatasetAttribution.objects.filter(dataset=dataset, attribution=attribution).delete()
    for organization in selected_organizations:
        DatasetAttribution.objects.create(dataset=dataset, attribution=attribution, organization=organization)
    dataset.save()


@transaction.atomic
def save_dataset_qualified_relations(dataset: Dataset, form: "BaseResourceForm") -> None:
    if "qualified_relation" not in form.cleaned_data or "qualified_relation" not in form.changed_data:
        return
    DatasetQualifiedRelation.objects.filter(dataset=dataset).delete()
    for url in form.cleaned_data["qualified_relation"]:
        DatasetQualifiedRelation.objects.get_or_create(dataset=dataset, url=url)
    dataset.save()

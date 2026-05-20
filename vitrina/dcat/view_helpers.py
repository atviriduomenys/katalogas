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
    DCATResourceSubclass,
    Relation,
)

if TYPE_CHECKING:
    from vitrina.dcat.forms.dataset_forms import BaseResourceForm

_SUBCLASS_CRUMB_LABELS = {
    DCATResourceSubclass.INFORMATION_SYSTEM: _("Informacinė sistema"),
    DCATResourceSubclass.SERVICE: _("Paslauga"),
    DCATResourceSubclass.DATASET: _("Duomenų rinkinys"),
}


def wizard_breadcrumb_ancestors(dataset: "Dataset | None", organization, include_self: bool = False) -> list[dict]:
    """Build the breadcrumb ancestor list for wizard fragment templates.

    Returns one dict per crumb that precedes the current item (the last shown separately in the template).
    Pass include_self=True to also append dataset itself — use this for distribution views where the
    dataset is an ancestor of the distribution being shown.
    """

    def _crumb(ds: Dataset) -> dict:
        subclass_name = ds.subclass.name if ds.subclass_id else None
        return {
            "type_label": str(_SUBCLASS_CRUMB_LABELS.get(subclass_name, _("Duomenų rinkinys"))),
            "title": ds.safe_translation_getter("title", any_language=True) or f"#{ds.pk}",
        }

    crumbs: list[dict] = [{"type_label": str(_("Organizacija")), "title": organization.title}]
    if dataset is None:
        return crumbs

    for ancestor in dataset.get_ancestors().select_related("subclass"):
        crumbs.append(_crumb(ancestor))

    if include_self:
        crumbs.append(_crumb(dataset))

    return crumbs


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

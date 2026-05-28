from typing import TYPE_CHECKING

from django.contrib import messages
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.db.models import Q, QuerySet
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
from vitrina.resources.models import DatasetDistribution

if TYPE_CHECKING:
    from vitrina.orgs.models import Organization
    from vitrina.dcat.forms.dataset_forms import BaseResourceForm, ISPublicServiceRelationshipForm


def datasets_in_org_scope(organization: "Organization") -> QuerySet:
    """Return a Dataset queryset scoped to the wizard organization.

    Includes datasets directly owned by the org AND datasets that are
    descendants of IS nodes owned by the org (which may have a different
    organization FK set as their data provider).
    """
    is_paths = list(
        Dataset.objects.filter(
            organization=organization,
            is_public=False,
            subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM,
        ).values_list("path", flat=True)
    )
    conditions = Q(organization=organization)
    for path in is_paths:
        conditions |= Q(path__startswith=path)
    return Dataset.objects.filter(conditions)


def wizard_breadcrumb_ancestors(
    dataset: "Dataset | None", organization: "Organization", include_self: bool = False
) -> list[dict]:
    """Build the breadcrumb ancestor list for wizard fragment templates.

    Returns one dict per crumb that precedes the current item (the last shown separately in the template).
    Pass include_self=True to also append dataset itself — use this for distribution views where the
    dataset is an ancestor of the distribution being shown.
    """

    def _crumb(ds: Dataset) -> dict:
        type_label = (ds.subclass.translated_title if ds.subclass_id else None) or str(_("Duomenų rinkinys"))
        return {
            "type_label": type_label,
            "title": ds.safe_translation_getter("title", any_language=True) or f"#{ds.pk}",
        }

    crumbs: list[dict] = [{"type_label": str(_("Organizacija")), "title": organization.title}]
    if dataset is None:
        return crumbs

    for ancestor in dataset.get_ancestors().select_related("subclass").prefetch_related("subclass__translations"):
        crumbs.append(_crumb(ancestor))

    if include_self:
        crumbs.append(_crumb(dataset))

    return crumbs


RELATION_FIELD_MAP = [
    # (field_name, relation_name, is_inverse)
    ("has_part", Relation.CATALOG, False),
    ("relates_to_information_system", Relation.RELATES_TO_INFORMATION_SYSTEM, True),
    ("related_information_system", Relation.RELATES_TO_INFORMATION_SYSTEM, False),
    ("relates_to_data_service", Relation.RELATES_TO_DATA_SERVICE, False),
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


PRODUCES_FIELDS = ["produces_datasets", "produces_services", "produces_catalogs"]


@transaction.atomic
def save_produces_relations(request: WSGIRequest, dataset: Dataset, form: "ISPublicServiceRelationshipForm") -> None:
    if not any(field in form.changed_data for field in PRODUCES_FIELDS):
        return

    try:
        relation = Relation.objects.get(name=Relation.PRODUCES)
    except Relation.DoesNotExist:
        warning_message = _(
            "Ryšio tipas '{relation_name}' nerastas, todėl laukų '{datasets}', '{services}', '{catalogs}' "
            "reikšmės neišsaugotos. Susisiekite su administratoriumi."
        ).format(
            relation_name=Relation.PRODUCES,
            datasets=form.fields["produces_datasets"].label,
            services=form.fields["produces_services"].label,
            catalogs=form.fields["produces_catalogs"].label,
        )
        messages.warning(request, warning_message)
        return

    DatasetRelation.objects.filter(relation=relation, dataset=dataset).delete()
    for field_name in PRODUCES_FIELDS:
        for selected_dataset in form.cleaned_data.get(field_name) or []:
            dataset_relation = DatasetRelation.objects.create(
                relation=relation, dataset=dataset, part_of=selected_dataset
            )
            dataset.part_of.add(dataset_relation)


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


def can_delete_dataset_in_wizard(dataset: Dataset) -> bool:
    return (
        not dataset.is_public and not dataset.get_children().exists() and not dataset.datasetdistribution_set.exists()
    )


def can_delete_distribution_in_wizard(distribution: DatasetDistribution) -> bool:
    return not distribution.dataset.is_public

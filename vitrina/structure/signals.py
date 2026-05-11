from typing import Any

from django.db.models import Model as DjangoModel
from django.db.models.signals import post_save, post_delete

from vitrina.resources.models import DatasetDistribution
from vitrina.structure.models import (
    Metadata,
    Model,
    Property,
    Base,
    Enum,
    EnumItem,
    Param,
    ParamItem,
    Prefix,
    PropertyList,
    UMLDiagram,
)

METADATA_STRUCTURE_FIELDS = {
    "name",
    "type",
    "ref",
    "visibility",
    "required",
}

STRUCTURE_MODELS = (
    Metadata,
    Model,
    Property,
    Base,
    Enum,
    EnumItem,
    Param,
    ParamItem,
    Prefix,
    PropertyList,
    DatasetDistribution,
)


def _bump_uml_version(instance: DjangoModel) -> None:
    metadata_version_id = getattr(instance, "metadata_version_id", None)
    if not metadata_version_id:
        return
    try:
        UMLDiagram.objects.get(metadata_version_id=metadata_version_id).invalidate()
    except UMLDiagram.DoesNotExist:
        pass


def _on_save(
    sender: type[DjangoModel],
    instance: DjangoModel,
    update_fields: frozenset[str] | None = None,
    **kwargs: Any,
) -> None:
    if sender is Metadata and update_fields is not None:
        if not METADATA_STRUCTURE_FIELDS.intersection(update_fields):
            return
    _bump_uml_version(instance)


def _on_delete(
    sender: type[DjangoModel],
    instance: DjangoModel,
    **kwargs: Any,
) -> None:
    _bump_uml_version(instance)


for _model in STRUCTURE_MODELS:
    post_save.connect(_on_save, sender=_model, weak=False)
    post_delete.connect(_on_delete, sender=_model, weak=False)

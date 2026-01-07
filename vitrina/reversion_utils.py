import json
from typing import Any
from uuid import UUID
from dataclasses import dataclass
from django.db import models
from reversion.models import Version
from django.db.models import Q


@dataclass
class VersionRelationSpec:
    target_model: type[models.Model]
    parent_fk: models.ForeignKey
    nested: list["VersionRelationSpec"] | None = None


def extract_fields_from_version_serialized_data(serialized_data: str) -> dict[str, Any]:
    payload = json.loads(serialized_data)
    return payload[0].get("fields", {})


def get_child_version_ids(parent_id: int | str | UUID, children: list[VersionRelationSpec]) -> set[int]:
    matching_versions: set[int] = set()
    for child in children:
        child_model: type[models.Model] = child.target_model
        relation_field: str = child.parent_fk.field.name
        grand_children = child.nested

        candidate_versions = Version.objects.get_for_model(child_model).filter(
            Q(serialized_data__contains=f'"{relation_field}": {parent_id}')
            | Q(serialized_data__contains=f'"{relation_field}": "{parent_id}"')
        )

        for version in candidate_versions.iterator():
            fields = extract_fields_from_version_serialized_data(version.serialized_data)
            if str(fields.get(relation_field)) == str(parent_id):
                matching_versions.add(version.id)
                if grand_children:
                    matching_versions.update(get_child_version_ids(version.object_id, grand_children))
    return matching_versions


def get_version_ids(instance: models.Model, children: list[VersionRelationSpec] | None = None) -> set[int]:
    """
    Collect django-reversion Version IDs for an instance and optionally its related (child) objects.

    This function is safe even if the underlying Django model instances were deleted,
    because it never loads the objects from the database—only Version rows.

    Args:
        instance:
            Model instance that Versions IDs are needed.
        children:
            Optional traversal specification for related models.
            Notes:
                - "relation" must be a Django relation (e.g. ForeignKey descriptor),
                and `relation.field.name` is used to read the FK value from
                reversion's serialized_data.
                - Nested "children" allows recursive traversal to any depth.

    Returns:
        A set of Version ids matching the parent and related objects.
    """

    matching_versions: set[int] = set()

    matching_versions.update(Version.objects.get_for_object(instance).values_list("id", flat=True))

    if children:
        matching_versions.update(get_child_version_ids(instance.pk, children))

    return matching_versions

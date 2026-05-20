import csv
import json
import logging
import uuid
from io import StringIO
from json import JSONDecodeError
from typing import Union, Tuple, List, Dict, Generator
from functools import lru_cache, cache


import requests
from django.db.models import Q, Prefetch, QuerySet
from pyproj import Transformer

import vitrina.datasets.structure as struct

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext, gettext_lazy as _, get_language

from vitrina import settings
from vitrina.classifiers.models import Status
from vitrina.comments.models import Comment
from vitrina.datasets.helpers import get_name_prefixes, match_name_prefix
from vitrina.datasets.models import DatasetStructure, Dataset
from vitrina.datasets.structure import detect_read_errors, read
from vitrina.helpers import none_to_string, get_encoding
from vitrina.orgs.services import (
    determine_user_role,
    MODEL_VISIBILITY_ACL,
    Action,
    PROPERTY_VISIBILITY_ACL,
    ENUM_VISIBILITY_ACL,
)
from vitrina.resources.models import DatasetDistribution, Format
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure import spyna
from vitrina.structure.helpers import get_type_repr
from vitrina.structure.models import (
    Metadata,
    Model,
    Property,
    Prefix,
    Enum,
    EnumItem,
    PropertyList,
    Param,
    ParamItem,
    Base,
    Version,
    VersionStatus,
    MetadataVersion,
)
from vitrina.tasks.models import Task
from vitrina.users.models import User
from spinta.core.context import create_context
from spinta.manifests.mermaid.helpers import write_mermaid_manifest
from spinta.manifests.components import ManifestPath
from spinta.cli.manifest import _read_and_return_manifest

logger = logging.getLogger(__name__)

MetadataCache = Dict[str, Metadata]


def _metadata_uuid_key(value) -> str:
    """Normalize manifest vs DB metadata ids for dict lookups and uuid__in (CharField vs uuid.UUID)."""
    return str(value) if value is not None else ""


def _build_metadata_cache(
    dataset: Dataset,
    metadata_version: Version,
    metadata_objects: List[Metadata] = None,
) -> MetadataCache:
    """
    Fetch Metadata rows into a ``{uuid_str: Metadata}`` dict with the latest
    MetadataVersion prefetched (DISTINCT ON metadata_id).

    Returns ``{}`` for a brand-new version (no existing rows → all items go to the
    create path).
    """
    if not metadata_version or not metadata_version.pk:
        return {}

    qs = Metadata.objects.filter(dataset=dataset, metadata_version=metadata_version)

    if metadata_objects is not None:
        metadata_uuids = list(
            dict.fromkeys(_metadata_uuid_key(meta.uuid) for meta in metadata_objects if getattr(meta, "uuid", None))
        )
        if not metadata_uuids:
            return {}
        qs = qs.filter(uuid__in=metadata_uuids)

    return {
        _metadata_uuid_key(m.uuid): m
        for m in qs.prefetch_related(
            Prefetch(
                "metadataversion_set",
                # Postgres DISTINCT ON — only the latest MetadataVersion per row.
                queryset=MetadataVersion.objects.select_related("base__model", "status")
                .only(
                    "metadata_id",
                    "name",
                    "type",
                    "required",
                    "unique",
                    "type_args",
                    "ref",
                    "source",
                    "prepare",
                    "level_given",
                    "access",
                    "base_id",
                    "status_id",
                )
                .order_by("metadata_id", "-version__created")
                .distinct("metadata_id"),
                to_attr="_prefetched_metadataversions",
            )
        )
    }


@cache
def _get_sys_user() -> User:
    user, _ = User.objects.get_or_create(email=settings.SYSTEM_USER_EMAIL)
    return user


def create_structure_objects(structure: DatasetStructure, metadata_version: Version = None) -> Version:
    sys_user = _get_sys_user()
    ct = ContentType.objects.get_for_model(DatasetStructure)
    if structure.file:
        Comment.objects.filter(content_type=ct, object_id=structure.pk, type=Comment.STRUCTURE_ERROR).delete()

        encoding = get_encoding(structure.file.path)
        if errors := detect_read_errors(structure.file.path, encoding):
            pass
        else:
            with open(
                structure.file.path,
                encoding=encoding,
                errors="replace",
            ) as f:
                reader = csv.DictReader(f)
                state = read(reader)
                if state.errors:
                    errors = state.errors
                else:
                    if not metadata_version:
                        latest_version = structure.dataset.latest_version()
                        max_version = latest_version.version if latest_version else 0

                        metadata_version = Version.objects.create(
                            dataset=structure.dataset,
                            status=VersionStatus.DRAFT,
                            version=max_version + 1,
                        )
                    existing_structure_comments = list(
                        Comment.objects.filter(content_type=ct, object_id=structure.pk, type=Comment.STRUCTURE).only(
                            "pk", "object_id"
                        )
                    )
                    _load_comments(
                        structure.dataset,
                        state.manifest.comments,
                        structure,
                        metadata_version,
                        existing_comments=existing_structure_comments,
                    )
                    _load_prefixes(structure.dataset, state.manifest.prefixes, structure, metadata_version)
                    _load_datasets(state, structure.dataset, metadata_version)
                    structure.dataset.update_level()

        for error in errors:
            Comment.objects.create(
                body=error,
                user=sys_user,
                content_type=ct,
                object_id=structure.pk,
                type=Comment.STRUCTURE_ERROR,
            )
            Task.objects.create(
                title=f"Rasta klaida duomenyse: {ct}, id: {structure.pk}",
                description=f"Duomenyse {ct}, id: {structure.pk} aptikta klaida.",
                content_type=ct,
                object_id=structure.pk,
                status=Task.CREATED,
                user=sys_user,
            )

    return metadata_version


def create_or_get_uapi_format():
    format_obj, created = Format.objects.get_or_create(extension="UAPI")
    if created:
        format_obj.title = "Saugyklos API"
        format_obj.mimetype = "application/vnd.api+json"
        format_obj.save()

    return format_obj


def _load_datasets(state: struct.State, dataset: Dataset, metadata_version: Version) -> None:
    ct = ContentType.objects.get_for_model(dataset)
    existing_metadata = list(
        Metadata.objects.filter(content_type=ct, object_id=dataset.pk, metadata_version=metadata_version)
    )
    loaded_metadata = []
    has_errors = False
    _clean_errors(dataset.current_structure)
    existing_dataset_comments = list(
        Comment.objects.filter(
            content_type=ct,
            object_id=dataset.pk,
            type=Comment.STRUCTURE,
        ).only("pk", "object_id")
    )
    to_process, main_prefix, whitelisted = _get_manifest_datasets_to_import(state, dataset)
    if not to_process:
        if whitelisted:
            message = _(
                "Kodinis pavadinimas turi prasidėti nuo „%(expected)s“ arba vieno iš leidžiamų kodinio pavadinimo pradžių: „%(whitelisted)s“."
            ) % {"expected": main_prefix, "whitelisted": ", ".join(whitelisted)}
        else:
            message = _("Kodinis pavadinimas turi prasidėti nuo „%(expected)s“.") % {"expected": main_prefix}
        _create_errors([message], dataset.current_structure)
        return

    manifest_names = list({manifest.name for _, manifest in to_process if manifest.name})
    dataset_meta_uuid_by_name: dict[str, uuid.UUID] = {}
    if manifest_names:
        for metadata in Metadata.objects.filter(
            content_type=ct,
            object_id=dataset.pk,
            metadata_version=metadata_version,
            name__in=manifest_names,
        ).only("uuid", "name"):
            dataset_meta_uuid_by_name.setdefault(metadata.name, metadata.uuid)

    # One query: names already claimed by another dataset for this version (replaces N loop queries).
    conflict_by_name: dict[str, Metadata] = {}
    if manifest_names:
        for metadata in (
            Metadata.objects.filter(
                content_type=ct,
                name__in=manifest_names,
                metadata_version=metadata_version,
            )
            .exclude(dataset=dataset)
            .order_by("pk")
            .only("pk", "name", "uuid", "dataset_id")
        ):
            conflict_by_name.setdefault(metadata.name, metadata)

    # One query to pre-fetch all existing Metadata for this dataset+version.
    metadata_cache = _build_metadata_cache(dataset, metadata_version)

    for order, meta in to_process:
        if meta.name:
            metadata = conflict_by_name.get(meta.name)
        else:
            metadata = (
                Metadata.objects.filter(
                    content_type=ct,
                    name=meta.name,
                    metadata_version=metadata_version,
                )
                .exclude(dataset=dataset)
                .first()
            )
        if metadata:
            meta.errors.append(_(f'Duomenų išteklius "{meta.name}" jau egzistuoja.'))
        elif not meta.name.isascii():
            meta.errors.append(_(f'"{meta.name}" kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės.'))
        elif any([ch.isupper() for ch in meta.name]):
            meta.errors.append(_(f'"{meta.name}" kodiniame pavadinime gali būti naudojamos tik mažosios raidės.'))
        else:
            if not meta.id and (uid := dataset_meta_uuid_by_name.get(meta.name)):
                meta.id = uid

            dataset, metadata = _create_or_update_metadata(
                dataset,
                meta,
                dataset,
                order,
                metadata_version=metadata_version,
                metadata_cache=metadata_cache,
            )
            _load_prefixes(dataset, meta.prefixes, dataset, metadata_version, metadata_cache=metadata_cache)
            _load_enums(dataset, meta.enums, dataset, metadata_version, metadata_cache=metadata_cache)
            _load_params(dataset, meta.params, dataset, metadata_version, metadata_cache=metadata_cache)
            _load_comments(
                dataset,
                meta.comments,
                dataset,
                metadata_version,
                existing_comments=existing_dataset_comments,
                metadata_cache=metadata_cache,
            )
            _load_models(meta, dataset, metadata_version, metadata_cache=metadata_cache)
            _link_distributions(meta, dataset, metadata_version, metadata_cache=metadata_cache)
            _link_models(dataset, meta, metadata_version, metadata_cache=metadata_cache)
            loaded_metadata.append(metadata)

        if errors := meta.errors:
            _create_errors(errors, dataset.current_structure)
            has_errors = True

    if not has_errors:
        removed_metadata = list(set(existing_metadata) - set(loaded_metadata))
        for meta in removed_metadata:
            meta.delete()


def _get_manifest_datasets_to_process(state: struct.State, dataset: Dataset) -> list[tuple[int, struct.Dataset]]:
    """
    Get manifest datasets to process, accounting for dependency exports.

    - Export with dependencies: dependent datasets appear first, main dataset is last.
    - First import: dataset.name may be empty/generic, so can't match by name.
    - Re-import: dataset.name matches the CSV name.

    Process dataset if:
    1. Name matches dataset.name (re-import case), OR
    2. Is the last dataset (first import OR main dataset in export with dependencies).

    This automatically skips dependency datasets since they:
    - Don't match dataset.name (different datasets).
    - Are not last (main dataset is always last in export).
    """
    datasets = list(state.manifest.datasets.values())
    result: list[tuple[int, struct.Dataset]] = []
    for order, meta in enumerate(datasets, 1):
        is_last = order == len(datasets)
        if meta.name == dataset.name or is_last:
            result.append((order, meta))
    return result


def _get_manifest_datasets_to_import(
    state: struct.State, dataset: Dataset
) -> tuple[list[tuple[int, struct.Dataset]], str, list[str]]:
    """
    Get manifest datasets to import.

    - Re-import: matches by dataset.name.
    - First import: falls back to last dataset with a matching organization prefix.

    Also returns main_prefix and whitelisted for error reporting.
    """
    datasets = list(state.manifest.datasets.values())
    result: list[tuple[int, struct.Dataset]] = []
    main_prefix, whitelisted = "", []
    for order, meta in enumerate(datasets, 1):
        is_last = order == len(datasets)
        main_prefix, whitelisted = get_name_prefixes(dataset.organization, dataset)
        matched_prefix = match_name_prefix(meta.name, [main_prefix] + whitelisted)
        if meta.name == dataset.name or (matched_prefix and is_last):
            result.append((order, meta))
    return result, main_prefix, whitelisted


def _load_prefixes(
    dataset: Dataset,
    prefixes: Dict[str, struct.Prefix],
    obj: models.Model,
    metadata_version: Version,
    metadata_cache: MetadataCache = None,
) -> None:
    ct = ContentType.objects.get_for_model(obj)
    prefix_ct = ContentType.objects.get_for_model(Prefix)

    prefixes_qs = Prefix.objects.filter(content_type=ct, object_id=obj.pk, metadata_version=metadata_version)
    loaded_prefixes = []

    incoming_metas = [prefix for prefix in prefixes.values() if not prefix.errors]
    incoming_names = [meta.name for meta in incoming_metas]
    existing_by_name: dict[str, Prefix] = {}
    local_cache: MetadataCache = metadata_cache if metadata_cache is not None else {}
    if incoming_names:
        existing_prefixes = prefixes_qs.filter(name__in=incoming_names).prefetch_related(
            Prefetch(
                "metadata",
                queryset=Metadata.objects.filter(dataset=dataset, content_type=prefix_ct).only("uuid"),
                to_attr="_md_for_dataset",
            )
        )
        existing_by_name = {p.name: p for p in existing_prefixes}
        if metadata_cache is None:
            local_cache = _build_metadata_cache(
                dataset,
                metadata_version,
                [metadata[0] for prefix in existing_prefixes if (metadata := getattr(prefix, "_md_for_dataset", None))],
            )

    for order, meta in enumerate(prefixes.values(), 1):
        if meta.errors:
            if isinstance(obj, Dataset):
                _create_errors(meta.errors, obj.current_structure)
            else:
                _create_errors(meta.errors, obj)
        else:
            if (prefix := existing_by_name.get(meta.name)) and not meta.id:
                metadata = getattr(prefix, "_md_for_dataset", None)
                if metadata:
                    meta.id = metadata[0].uuid

            prefix = Prefix(
                name=meta.name, uri=meta.uri, content_type=ct, object_id=obj.pk, metadata_version=metadata_version
            )
            prefix, metadata = _create_or_update_metadata(
                dataset, meta, prefix, order, metadata_version=metadata_version, metadata_cache=local_cache
            )
            loaded_prefixes.append(prefix)

    loaded_names = [prefix.name for prefix in loaded_prefixes]
    prefixes_qs.exclude(name__in=loaded_names).delete()


def _load_enums(
    dataset: Dataset,
    enums: Dict[str, List[struct.Enum]],
    obj: Union[Dataset, Property],
    metadata_version: Version,
    metadata_cache: MetadataCache = None,
) -> None:
    ct = ContentType.objects.get_for_model(obj)
    enum_ct = ContentType.objects.get_for_model(EnumItem)
    existing_enums_qs = Enum.objects.filter(content_type=ct, object_id=obj.pk, metadata_version=metadata_version)
    existing_enum_map = {enum.name: enum for enum in existing_enums_qs}

    loaded_enums = []

    for name, enum_items in enums.items():
        if isinstance(obj, Property) and name:
            _create_errors(
                [
                    _(
                        'Reikšmių sąrašas "{0}" negali turėti pavadinimo (ref), kai yra deklaruojamas savybės dimensijoje.'
                    ).format(name)
                ],
                obj,
            )
            enum_name = ""
        else:
            enum_name = name

        enum = existing_enum_map.get(enum_name)
        if not enum:
            enum = Enum.objects.create(
                name=enum_name, content_type=ct, object_id=obj.pk, metadata_version=metadata_version
            )

        existing_enum_items = list(
            EnumItem.objects.filter(enum=enum, metadata_version=metadata_version).prefetch_related("metadata")
        )
        if metadata_cache is not None:
            local_cache = metadata_cache
        elif any(item.id for item in enum_items):
            local_cache = _build_metadata_cache(
                dataset,
                metadata_version,
                [
                    metadata
                    for item in existing_enum_items
                    for metadata in item.metadata.all()
                    if metadata.content_type_id == enum_ct.pk and metadata.dataset_id == dataset.pk
                ],
            )
        else:
            local_cache: MetadataCache = {}

        # Build a lookup dict to eliminate N+1 .filter() inside the item loop
        existing_items_map = {}
        for item in existing_enum_items:
            for metadata in item.metadata.all():
                if metadata.content_type_id == enum_ct.pk:
                    key = (metadata.name, metadata.prepare, metadata.source, metadata.dataset_id)
                    existing_items_map[key] = item
                    break

        loaded_enum_items = []

        for order, meta in enumerate(enum_items, 1):
            if meta.errors:
                if isinstance(obj, Dataset):
                    _create_errors(meta.errors, obj.current_structure)
                else:
                    _create_errors(meta.errors, obj)
            else:
                key = (meta.name, meta.prepare, meta.source, dataset.pk)
                en = existing_items_map.get(key)

                if en and not meta.id:
                    first_meta = next(iter(en.metadata.all()), None)
                    if first_meta:
                        meta.id = first_meta.uuid

                enum_item = EnumItem(enum=enum, metadata_version=metadata_version)
                enum_item, metadata = _create_or_update_metadata(
                    dataset, meta, enum_item, order, metadata_version=metadata_version, metadata_cache=local_cache
                )
                loaded_enum_items.append(enum_item)

        loaded_enums.append(enum)

        removed_enum_item_ids = [enum_item.pk for enum_item in set(existing_enum_items) - set(loaded_enum_items)]
        if removed_enum_item_ids:
            EnumItem.objects.filter(pk__in=removed_enum_item_ids).delete()

    removed_enum_ids = [e.pk for e in set(existing_enums_qs) - set(loaded_enums)]
    if removed_enum_ids:
        EnumItem.objects.filter(enum_id__in=removed_enum_ids).delete()
        Enum.objects.filter(pk__in=removed_enum_ids).delete()


def _load_params(
    dataset: Dataset,
    params: Dict[str, List[struct.Param]],
    obj: Union[Dataset, Model, DatasetDistribution],
    metadata_version: Version,
    metadata_cache: MetadataCache = None,
):
    ct = ContentType.objects.get_for_model(obj)
    param_ct = ContentType.objects.get_for_model(ParamItem)

    existing_params_qs = Param.objects.filter(content_type=ct, object_id=obj.pk, metadata_version=metadata_version)
    existing_param_map = {p.name: p for p in existing_params_qs}

    loaded_params = []

    for name, param_items in params.items():
        param = existing_param_map.get(name)
        if not param:
            param = Param.objects.create(
                name=name, content_type=ct, object_id=obj.pk, metadata_version=metadata_version
            )

        existing_param_items = list(
            ParamItem.objects.filter(param=param, metadata_version=metadata_version).prefetch_related("metadata")
        )
        # Use full cache if available; fall back to a local build only when running standalone.
        if metadata_cache is not None:
            local_cache = metadata_cache
        elif any(item.id for item in param_items):
            local_cache = _build_metadata_cache(
                dataset,
                metadata_version,
                [
                    metadata
                    for item in existing_param_items
                    for metadata in item.metadata.all()
                    if metadata.content_type_id == param_ct.pk and metadata.dataset_id == dataset.pk
                ],
            )
        else:
            local_cache: MetadataCache = {}

        # Build lookup dict to eliminate N+1 .filter() in the inner loop
        existing_items_map = {}
        for item in existing_param_items:
            for metadata in item.metadata.all():  # uses prefetch cache — no DB hit
                if metadata.content_type_id == param_ct.pk:
                    key = (metadata.name, metadata.prepare, metadata.dataset_id)
                    existing_items_map[key] = item
                    break

        loaded_param_items = []

        for order, meta in enumerate(param_items, 1):
            if meta.errors:
                if isinstance(obj, Dataset):
                    _create_errors(meta.errors, obj.current_structure)
                else:
                    _create_errors(meta.errors, obj)
            else:
                key = (meta.name, meta.prepare, dataset.pk)
                param_item = existing_items_map.get(key)

                if param_item and not meta.id:
                    first_meta = next(iter(param_item.metadata.all()), None)
                    if first_meta:
                        meta.id = first_meta.uuid

                param_item = ParamItem(param=param, metadata_version=metadata_version)
                param_item, metadata = _create_or_update_metadata(
                    dataset, meta, param_item, order, metadata_version=metadata_version, metadata_cache=local_cache
                )
                loaded_param_items.append(param_item)

        loaded_params.append(param)

        # Bulk delete removed ParamItems — one DELETE instead of N
        removed_param_item_ids = [p.pk for p in set(existing_param_items) - set(loaded_param_items)]
        if removed_param_item_ids:
            ParamItem.objects.filter(pk__in=removed_param_item_ids).delete()

    # Bulk delete removed Params and their items — two DELETEs total
    removed_param_ids = [p.pk for p in set(existing_params_qs) - set(loaded_params)]
    if removed_param_ids:
        ParamItem.objects.filter(param_id__in=removed_param_ids).delete()
        Param.objects.filter(pk__in=removed_param_ids).delete()


def _load_models(
    meta_dataset: struct.Dataset,
    dataset: Dataset,
    metadata_version: Version,
    metadata_cache: MetadataCache | None = None,
) -> None:
    ct = ContentType.objects.get_for_model(Model)

    existing_models = list(
        Model.objects.filter(dataset=dataset, metadata_version=metadata_version).prefetch_related("metadata")
    )
    local_cache: MetadataCache
    if metadata_cache is not None:
        local_cache = metadata_cache
    else:
        model_metas = []
        for model in existing_models:
            for metadata in model.metadata.all():
                if metadata not in model_metas:
                    model_metas.append(metadata)
        local_cache = _build_metadata_cache(dataset, metadata_version, model_metas)

    # Build lookup dict — eliminates N+1 .filter() inside the loop
    existing_models_map = {}
    for model in existing_models:
        for metadata in model.metadata.all():
            if metadata.content_type_id == ct.pk and metadata.dataset_id == dataset.pk:
                existing_models_map[metadata.name] = model
                break

    loaded_models = []

    existing_model_ids = [model.pk for model in existing_models]
    existing_comments_by_object_id: dict[int, list[Comment]] = {}
    if existing_model_ids:
        model_comment_ct = ContentType.objects.get_for_model(Model)
        existing_comments = Comment.objects.filter(
            content_type=model_comment_ct,
            object_id__in=existing_model_ids,
            type=Comment.STRUCTURE,
        ).only("pk", "object_id")
        for comment in existing_comments:
            existing_comments_by_object_id.setdefault(comment.object_id, []).append(comment)

    for order, meta in enumerate(meta_dataset.models.values(), 1):
        if meta.errors:
            _create_errors(meta.errors, dataset.current_structure)
        else:
            # dict lookup instead of per-iteration DB query
            model = existing_models_map.get(meta.name)
            if model and not meta.id:
                first_meta = next(iter(model.metadata.all()), None)
                if first_meta:
                    meta.id = first_meta.uuid

            model = Model(dataset=dataset, metadata_version=metadata_version)
            model, metadata = _create_or_update_metadata(
                dataset, meta, model, order, metadata_version=metadata_version, metadata_cache=local_cache
            )
            _check_uri(dataset, meta, meta.uri)
            _clean_errors(model)
            _load_comments(
                dataset,
                meta.comments,
                model,
                metadata_version,
                existing_comments=existing_comments_by_object_id.get(model.pk, []),
                metadata_cache=local_cache,
            )
            _load_params(dataset, meta.params, model, metadata_version, metadata_cache=local_cache)
            _load_properties(dataset, meta, model, metadata_version, metadata_cache=local_cache)
            loaded_models.append(model)
            _create_errors(meta.errors, model)

    # Bulk delete removed models — one DELETE instead of N
    removed_model_ids = [model.pk for model in set(existing_models) - set(loaded_models)]
    if removed_model_ids:
        Model.objects.filter(pk__in=removed_model_ids).delete()


def _load_properties(
    dataset: Dataset,
    model_meta: struct.Model,
    model: Model,
    metadata_version: Version,
    metadata_cache: MetadataCache = None,
) -> None:
    ct = ContentType.objects.get_for_model(Property)
    existing_props = list(
        Property.objects.filter(model=model, given=True, metadata_version=metadata_version).prefetch_related("metadata")
    )
    if metadata_cache is not None:
        local_cache = metadata_cache
    else:
        local_cache = _build_metadata_cache(
            dataset,
            metadata_version,
            [
                metadata
                for prop in existing_props
                for metadata in prop.metadata.all()
                if metadata.content_type_id == ct.pk and metadata.dataset_id == dataset.pk
            ],
        )

    # Build lookup dict — eliminates N+1 .filter() inside the loop
    existing_props_map = {}
    for prop in existing_props:
        for metadata in prop.metadata.all():
            if metadata.content_type_id == ct.pk and metadata.dataset_id == dataset.pk:
                existing_props_map[metadata.name] = prop
                break

    loaded_props = []

    # Preload existing structure comments for properties that already exist in DB
    existing_prop_ids = []
    for prop_meta in model_meta.properties.values():
        prop = existing_props_map.get(prop_meta.name)
        if prop is not None and prop.pk:
            existing_prop_ids.append(prop.pk)

    existing_comments_by_object_id: dict[int, list[Comment]] = {}
    if existing_prop_ids:
        prop_comment_ct = ContentType.objects.get_for_model(Property)
        existing_comments = Comment.objects.filter(
            content_type=prop_comment_ct,
            object_id__in=existing_prop_ids,
            type=Comment.STRUCTURE,
        ).only("pk", "object_id")
        for comment in existing_comments:
            existing_comments_by_object_id.setdefault(comment.object_id, []).append(comment)

    for order, meta in enumerate(model_meta.properties.values(), 1):
        if meta.errors:
            _create_errors(meta.errors, model)
        else:
            prop = existing_props_map.get(meta.name)
            if prop and not meta.id:
                # Reuse prefetch cache — avoids pr.metadata.first() extra query
                first_meta = next(iter(prop.metadata.all()), None)
                if first_meta:
                    meta.id = first_meta.uuid

            prop = Property(model=model, metadata_version=metadata_version)
            prop, metadata = _create_or_update_metadata(
                dataset, meta, prop, order, metadata_version=metadata_version, metadata_cache=local_cache
            )
            _check_uri(dataset, meta, metadata.uri)
            _clean_errors(prop)
            _load_comments(
                dataset,
                meta.comments,
                prop,
                metadata_version,
                existing_comments=existing_comments_by_object_id.get(prop.pk, []),
                metadata_cache=local_cache,
            )
            _load_enums(dataset, meta.enums, prop, metadata_version, metadata_cache=local_cache)
            loaded_props.append(prop)
            _create_errors(meta.errors, prop)

    # Bulk delete removed props — one DELETE instead of N
    removed_prop_ids = [prop.pk for prop in set(existing_props) - set(loaded_props)]
    if removed_prop_ids:
        Property.objects.filter(pk__in=removed_prop_ids).delete()


def _load_comments(
    dataset: Dataset,
    comments: List[struct.Comment],
    obj: models.Model,
    metadata_version: Version,
    existing_comments: list[Comment] | None = None,
    metadata_cache: MetadataCache = None,
) -> None:
    ct = ContentType.objects.get_for_model(obj)
    sys_user = _get_sys_user()

    if existing_comments is None:
        existing_comments = list(Comment.objects.filter(content_type=ct, object_id=obj.pk, type=Comment.STRUCTURE))

    existing_comment_ids = {comment.pk for comment in existing_comments if comment.pk}

    # Use the full pre-built cache when available (passed from _load_datasets).
    # Fall back to a targeted per-call query only when running standalone.
    local_cache: MetadataCache
    if metadata_cache is not None:
        local_cache = metadata_cache
    elif existing_comment_ids and any(comment.id for comment in comments):
        local_cache = {
            _metadata_uuid_key(metadata.uuid): metadata
            for metadata in Metadata.objects.filter(
                dataset=dataset,
                content_type=ct,
                object_id__in=list(existing_comment_ids),
                metadata_version=metadata_version,
            ).prefetch_related(
                Prefetch(
                    "metadataversion_set",
                    queryset=MetadataVersion.objects.select_related("version").order_by("-version__created"),
                    to_attr="_prefetched_metadataversions",
                )
            )
        }
    else:
        local_cache = {}

    loaded_comments = []

    for order, meta in enumerate(comments, 1):
        comment = Comment(
            user=sys_user,
            content_type=ct,
            object_id=obj.pk,
            type=Comment.STRUCTURE,
            body=meta.description if meta.description else "",
        )
        comment, metadata = _create_or_update_metadata(
            dataset, meta, comment, order, metadata_version=metadata_version, metadata_cache=local_cache
        )
        loaded_comments.append(comment)
        _create_errors(meta.errors, comment)

    # Bulk delete — remove comments that are not present in the incoming manifest.
    loaded_comment_ids = {c.pk for c in loaded_comments if c.pk}
    removed_comment_ids = existing_comment_ids - loaded_comment_ids
    if removed_comment_ids:
        Comment.objects.filter(pk__in=removed_comment_ids).delete()


def _clean_errors(obj: models.Model):
    ct = ContentType.objects.get_for_model(obj)
    Comment.objects.filter(content_type=ct, object_id=obj.pk, type=Comment.STRUCTURE_ERROR).delete()


def _create_errors(errors: List[str], obj: models.Model):
    ct = ContentType.objects.get_for_model(obj)
    sys_user = _get_sys_user()

    if not errors:
        return

    for error in errors:
        Comment.objects.create(
            user=sys_user,
            content_type=ct,
            object_id=obj.pk,
            type=Comment.STRUCTURE_ERROR,
            body=error,
        )

        Task.objects.create(
            title=f"Rasta klaida duomenyse: {ct}, id: {obj.pk}",
            description=f"Duomenyse {ct}, id: {obj.pk} aptikta klaida.",
            content_type=ct,
            object_id=obj.pk,
            status=Task.CREATED,
            user=sys_user,
        )


def _parse_prepare(prepare: str, meta: struct.Metadata) -> dict:
    if prepare:
        try:
            return spyna.parse(prepare)
        except BaseException as e:
            if hasattr(meta, "errors"):
                meta.errors.append(_(f'Klaida skaitant formulę "{prepare}"": {e}'))
    return {}


def _create_or_update_metadata(
    dataset: Dataset,
    obj_meta: struct.Metadata,
    obj: models.Model,
    order: int = None,
    metadata_version: Version = None,
    metadata_cache: MetadataCache | None = None,
) -> Tuple[models.Model, struct.Metadata]:
    metadata = None
    if obj_meta.id:
        if metadata_cache:
            metadata = metadata_cache.get(_metadata_uuid_key(obj_meta.id))
        if not metadata:
            ct = ContentType.objects.get_for_model(obj)
            metadata = (
                Metadata.objects.filter(
                    uuid=_metadata_uuid_key(obj_meta.id),
                    content_type=ct,
                    dataset=dataset,
                    metadata_version=metadata_version,
                )
                .prefetch_related(
                    Prefetch(
                        "metadataversion_set",
                        # Latest-only + slim columns (see _build_metadata_cache).
                        queryset=MetadataVersion.objects.select_related("base__model", "status")
                        .only(
                            "metadata_id",
                            "name",
                            "type",
                            "required",
                            "unique",
                            "type_args",
                            "ref",
                            "source",
                            "prepare",
                            "level_given",
                            "access",
                            "base_id",
                            "status_id",
                        )
                        .order_by("metadata_id", "-version__created")
                        .distinct("metadata_id"),
                        to_attr="_prefetched_metadataversions",
                    )
                )
                .first()
            )
    if metadata:
        # Avoid GenericForeignKey resolution (metadata.object) which triggers extra SELECTs.
        metadata_ct_id = metadata.content_type_id
        dataset_ct_id = ContentType.objects.get_for_model(Dataset).pk
        model_ct_id = ContentType.objects.get_for_model(Model).pk
        property_ct_id = ContentType.objects.get_for_model(Property).pk
        enum_item_ct_id = ContentType.objects.get_for_model(EnumItem).pk

        type_args = ", ".join(obj_meta.type_args) if hasattr(obj_meta, "type_args") and obj_meta.type_args else None
        access = _parse_access(obj_meta.access)
        visibility = _parse_visibility(obj_meta.visibility)
        status = _get_status(obj_meta.status)
        prefetched_versions = getattr(metadata, "_prefetched_metadataversions", None)
        if latest_version := (prefetched_versions[0] if prefetched_versions else None):
            if (
                (metadata_ct_id == dataset_ct_id and latest_version.name != obj_meta.name)
                or (
                    metadata_ct_id == model_ct_id
                    and (
                        latest_version.name != obj_meta.name
                        or none_to_string(latest_version.ref) != none_to_string(obj_meta.ref)
                        or latest_version.level_given != obj_meta.level_given
                        or latest_version.status != status
                        or (
                            latest_version.base
                            and obj_meta.base
                            and latest_version.base.model.full_name != obj_meta.base.name
                        )
                        or (not latest_version.base and obj_meta.base)
                        or (latest_version.base and not obj_meta.base)
                    )
                )
                or (
                    metadata_ct_id == property_ct_id
                    and (
                        latest_version.name != obj_meta.name
                        or latest_version.type != obj_meta.type
                        or latest_version.status != status
                        or latest_version.required != obj_meta.required
                        or latest_version.unique != obj_meta.unique
                        or latest_version.type_args != type_args
                        or none_to_string(latest_version.ref) != none_to_string(obj_meta.ref)
                        or latest_version.level_given != obj_meta.level_given
                        or latest_version.access != access
                    )
                )
                or (
                    metadata_ct_id == enum_item_ct_id
                    and (
                        none_to_string(latest_version.prepare) != none_to_string(obj_meta.prepare)
                        or none_to_string(latest_version.source) != none_to_string(obj_meta.source)
                    )
                )
            ):
                metadata.draft = True
            else:
                metadata.draft = False

        metadata.uuid = _metadata_uuid_key(obj_meta.id) if obj_meta.id else metadata.uuid
        metadata.name = obj_meta.name if hasattr(obj_meta, "name") else ""
        metadata.type = obj_meta.type if hasattr(obj_meta, "type") else ""
        metadata.ref = obj_meta.ref
        metadata.source = obj_meta.source
        metadata.prepare = obj_meta.prepare
        metadata.prepare_ast = _parse_prepare(obj_meta.prepare, obj_meta)
        metadata.level = obj_meta.level
        metadata.level_given = obj_meta.level_given
        metadata.access = access
        metadata.visibility = visibility
        metadata.eli = obj_meta.eli
        metadata.status = status
        metadata.uri = obj_meta.uri
        metadata.version = metadata.version + 1 if metadata.version else 1
        metadata.title = obj_meta.title
        metadata.count = obj_meta.count
        metadata.description = obj_meta.description
        metadata.order = order
        metadata.required = obj_meta.required if hasattr(obj_meta, "required") else None
        metadata.unique = obj_meta.unique if hasattr(obj_meta, "unique") else None
        metadata.type_args = type_args
        metadata.metadata_version = metadata_version
        metadata.save()

        # Don't resolve GenericForeignKey target (would cause extra reads).
        obj.pk = metadata.object_id
    else:
        ct = ContentType.objects.get_for_model(obj)
        if not obj.pk:
            obj.save()
        if not obj_meta.id:
            obj_meta.id = uuid.uuid4()

        metadata = Metadata.objects.create(
            dataset=dataset,
            uuid=_metadata_uuid_key(obj_meta.id),
            name=obj_meta.name if hasattr(obj_meta, "name") else "",
            type=obj_meta.type if hasattr(obj_meta, "type") else "",
            ref=obj_meta.ref,
            source=obj_meta.source,
            prepare=obj_meta.prepare,
            prepare_ast=_parse_prepare(obj_meta.prepare, obj_meta),
            level=obj_meta.level,
            level_given=obj_meta.level_given,
            access=_parse_access(obj_meta.access),
            visibility=_parse_visibility(obj_meta.visibility),
            eli=obj_meta.eli,
            count=obj_meta.count,
            status=_get_status(obj_meta.status),
            uri=obj_meta.uri,
            version=1,
            title=obj_meta.title,
            description=obj_meta.description,
            order=order,
            content_type=ct,
            object_id=obj.pk,
            required=obj_meta.required if hasattr(obj_meta, "required") else None,
            unique=obj_meta.unique if hasattr(obj_meta, "unique") else None,
            type_args=", ".join(obj_meta.type_args) if hasattr(obj_meta, "type_args") and obj_meta.type_args else None,
            metadata_version=metadata_version,
        )

    return obj, metadata


def _link_distributions(
    dataset_meta: struct.Dataset,
    dataset: Dataset,
    metadata_version: Version,
    metadata_cache: MetadataCache = None,
):
    """Link distribution metadata to dataset distributions."""
    if dataset_meta.resources:
        _link_resource_distributions(dataset_meta, dataset, metadata_version, metadata_cache=metadata_cache)


def _link_resource_distributions(
    dataset_meta: struct.Dataset,
    dataset: Dataset,
    metadata_version: Version,
    metadata_cache: MetadataCache = None,
):
    """Link each resource as a separate distribution."""
    distribution_content_type = ContentType.objects.get_for_model(DatasetDistribution)

    resources = list(dataset_meta.resources.values())
    if not resources:
        return

    resource_sources = [resource.source for resource in resources]
    resource_names = [resource.name for resource in resources]

    # Batch fetch all matching distributions in one query — eliminates N+1
    existing_distributions = (
        DatasetDistribution.objects.filter(
            dataset=dataset,
            download_url__in=resource_sources,
            metadata_version=metadata_version,
        )
        .filter(
            Q(metadata__name__in=resource_names, metadata__content_type=distribution_content_type)
            | Q(metadata__isnull=True)
        )
        .prefetch_related("metadata")
    )
    distribution_map = {}
    existing_distribution_ids: set[int] = set()
    for dist in existing_distributions:
        meta_names = [metadata.name for metadata in dist.metadata.all()]
        existing_distribution_ids.add(dist.pk)
        for name in meta_names:
            distribution_map[(dist.download_url, name)] = dist
        if not meta_names:
            distribution_map[(dist.download_url, None)] = dist

    distribution_comments_by_object_id: dict[int, list[Comment]] = {}
    if existing_distribution_ids:
        distribution_comment_ct = ContentType.objects.get_for_model(DatasetDistribution)
        existing_distribution_comments = Comment.objects.filter(
            content_type=distribution_comment_ct,
            object_id__in=list(existing_distribution_ids),
            type=Comment.STRUCTURE,
        ).only("pk", "object_id")
        for comment in existing_distribution_comments:
            distribution_comments_by_object_id.setdefault(comment.object_id, []).append(comment)

    for i, resource_meta in enumerate(resources):
        title = resource_meta.title or dataset_meta.title or resource_meta.name

        distribution = distribution_map.get((resource_meta.source, resource_meta.name)) or distribution_map.get(
            (resource_meta.source, None)
        )
        if not distribution:
            distribution = _create_distribution_with_status_update(
                dataset=dataset,
                download_url=resource_meta.source,
                title=resource_meta.name,
                description=resource_meta.description,
                metadata_version=metadata_version,
            )

        distribution.set_current_language("lt")
        distribution.title = title

        if not resource_meta.id:
            first_meta = next(iter(distribution.metadata.all()), None)
            if first_meta:
                resource_meta.id = first_meta.uuid

        distribution, metadata = _create_or_update_metadata(
            dataset,
            resource_meta,
            distribution,
            i,
            metadata_version=metadata_version,
            metadata_cache=metadata_cache,
        )

        _load_params(dataset, resource_meta.params, distribution, metadata_version, metadata_cache=metadata_cache)
        _clean_errors(distribution)
        _load_comments(
            dataset,
            resource_meta.comments,
            distribution,
            metadata_version,
            existing_comments=distribution_comments_by_object_id.get(distribution.pk, []),
            metadata_cache=metadata_cache,
        )
        _link_models_to_distribution(
            dataset, resource_meta, distribution, metadata_version, metadata_cache=metadata_cache
        )

        distribution.save()

        if resource_meta.errors:
            _create_errors(resource_meta.errors, dataset.current_structure)


def _create_distribution_with_status_update(
    dataset: Dataset,
    download_url: str,
    title: str | None = None,
    description: str | None = None,
    format=None,
    metadata_version: Version = None,
) -> DatasetDistribution:
    """Create a distribution and update dataset status if needed."""

    if not dataset.datasetdistribution_set.exists() and dataset.is_public:
        dataset.status = Dataset.HAS_DATA
        dataset.save()

        sys_user, _ = User.objects.get_or_create(email=settings.SYSTEM_USER_EMAIL)
        Comment.objects.create(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=sys_user,
            type=Comment.STATUS,
            status=Comment.OPENED,
        )

    distribution_data = {
        "dataset": dataset,
        "download_url": download_url,
        "type": "URL",
        "metadata_version": metadata_version,
    }

    if title:
        distribution_data["title"] = title
    if description:
        distribution_data["description"] = description
    if format:
        distribution_data["format"] = format

    return DatasetDistribution.objects.create(**distribution_data)


def _link_models_to_distribution(
    dataset: Dataset,
    meta_with_models: struct.Dataset,
    distribution: DatasetDistribution,
    metadata_version: Version = None,
    metadata_cache: MetadataCache | None = None,
):
    """Link models to the given distribution."""
    model_ids = [_metadata_uuid_key(meta.id) for meta in meta_with_models.models.values() if meta.id]
    models_by_uuid = {}
    if model_ids:
        model_ct = ContentType.objects.get_for_model(Model)
        # Always query the DB: this runs after _load_models has created/updated rows,
        # so newly inserted models are absent from the pre-built cache.
        model_metadata = list(
            Metadata.objects.filter(
                content_type=model_ct,
                uuid__in=model_ids,
                dataset=dataset,
                metadata_version=metadata_version,
            ).only("uuid", "object_id")
        )
        model_ids_to_obj = {_metadata_uuid_key(md.uuid): md.object_id for md in model_metadata}
        models = Model.objects.in_bulk(list(model_ids_to_obj.values()))
        models_by_uuid = {uid: models.get(obj_id) for uid, obj_id in model_ids_to_obj.items() if models.get(obj_id)}

    for model_meta in meta_with_models.models.values():
        if not model_meta.id:
            continue
        if model := models_by_uuid.get(_metadata_uuid_key(model_meta.id)):
            model.distribution = distribution
            model.save(update_fields=["distribution"])


def _link_models(
    dataset: Dataset,
    dataset_meta: struct.Dataset,
    metadata_version: Version,
    metadata_cache: MetadataCache | None = None,
) -> None:
    model_ct = ContentType.objects.get_for_model(Model)
    prop_ct = ContentType.objects.get_for_model(Property)
    base_ct = ContentType.objects.get_for_model(Base)
    base_comment_ct = ContentType.objects.get_for_model(Base)
    model_ids = [_metadata_uuid_key(meta.id) for meta in dataset_meta.models.values() if meta.id]
    models_by_uuid = {}
    if model_ids:
        # Always query the DB: this runs after _load_models, so newly inserted
        # models are absent from the pre-built cache.
        model_metadata = list(
            Metadata.objects.filter(
                content_type=model_ct,
                uuid__in=model_ids,
                dataset=dataset,
                metadata_version=metadata_version,
            ).only("uuid", "object_id")
        )
        model_ids_to_obj = {_metadata_uuid_key(md.uuid): md.object_id for md in model_metadata}
        models = Model.objects.in_bulk(list(model_ids_to_obj.values()))
        models_by_uuid = {uid: models.get(obj_id) for uid, obj_id in model_ids_to_obj.items() if models.get(obj_id)}

    base_meta_ids = [
        _metadata_uuid_key(meta.base.id) for meta in dataset_meta.models.values() if meta.base and meta.base.id
    ]
    base_comments_by_object_id: dict[int, list[Comment]] = {}
    if base_meta_ids:
        # Same reason — always query the DB for base PKs.
        base_metadata = Metadata.objects.filter(
            content_type=base_ct,
            uuid__in=base_meta_ids,
            dataset=dataset,
            metadata_version=metadata_version,
        ).only("uuid", "object_id")
        base_pks = [metadata.object_id for metadata in base_metadata if metadata.object_id]
        if base_pks:
            existing_base_comments = Comment.objects.filter(
                content_type=base_comment_ct,
                object_id__in=base_pks,
                type=Comment.STRUCTURE,
            ).only("pk", "object_id")
            for comment in existing_base_comments:
                base_comments_by_object_id.setdefault(comment.object_id, []).append(comment)

    for model_meta in dataset_meta.models.values():
        if not model_meta.id:
            continue
        if model := models_by_uuid.get(_metadata_uuid_key(model_meta.id)):
            _link_base(
                dataset,
                model_meta.base,
                model,
                metadata_version,
                existing_base_comments_by_object_id=base_comments_by_object_id,
                metadata_cache=metadata_cache,
            )

            if model_meta.ref and model_meta.ref_props:
                ref_prop_names = [name for name in model_meta.ref_props if name]
                props_by_name: dict[str, Property] = {}
                if ref_prop_names:
                    prop_metadata = Metadata.objects.filter(
                        content_type=prop_ct,
                        name__in=ref_prop_names,
                        metadata_version=metadata_version,
                        object_id__in=Property.objects.filter(model=model).values_list("id", flat=True),
                    ).only("name", "object_id")
                    model_props = Property.objects.in_bulk([md.object_id for md in prop_metadata])
                    props_by_name = {
                        md.name: model_props.get(md.object_id) for md in prop_metadata if model_props.get(md.object_id)
                    }

                PropertyList.objects.filter(
                    content_type=model_ct, object_id=model.pk, metadata_version=metadata_version
                ).delete()
                for order, prop_name in enumerate(model_meta.ref_props, 1):
                    if ref_prop := props_by_name.get(prop_name):
                        PropertyList.objects.create(
                            content_type=model_ct,
                            object_id=model.pk,
                            order=order,
                            property=ref_prop,
                            metadata_version=metadata_version,
                        )

            _link_properties(dataset, model, model_meta, metadata_version)
            model.update_level()


def resolve_base_model(base_metadata: struct.Base, metadata_version: Version) -> Model | None:
    """Retrieves a base model based on metadata, prioritizing specific version or stable status.

    This function attempts to find a Model object associated with a given base_metadata.
    It handles two scenarios for model import:
        1.  Model and Base in the same file: In this case, the function expects to find the model
            with the same `metadata_version` as provided.
        2.  Model imported after being referenced as Base: If the model is defined in a separate file and then
            referenced as a base, their `metadata_version`s might differ. In this scenario,
            the function falls back to searching for the newest `STABLE` version of the model.
    """
    model_content_type = ContentType.objects.get_for_model(Model)
    base_filter = Q(metadata__content_type=model_content_type, metadata__name=base_metadata.name)

    queryset = Model.objects.filter(base_filter).order_by("-created")
    return (
        queryset.filter(metadata_version=metadata_version).first()
        or queryset.filter(metadata_version__status=VersionStatus.STABLE).first()
    )


def _link_base(
    dataset: Dataset,
    meta: struct.Base,
    model: Model,
    metadata_version: Version,
    existing_base_comments_by_object_id: dict[int, list[Comment]] | None = None,
    metadata_cache: MetadataCache = None,
):
    if meta:
        if meta.errors:
            _create_errors(meta.errors, model)
        else:
            if base_model := resolve_base_model(meta, metadata_version):
                if base_object := Base.objects.filter(
                    metadata__content_type=ContentType.objects.get_for_model(Base),
                    metadata__name=meta.name,
                    model=base_model,
                    metadata_version=metadata_version,
                ).first():
                    if not meta.id:
                        meta.id = base_object.metadata.first().uuid

                base = Base(model=base_model, metadata_version=metadata_version)
                base, metadata = _create_or_update_metadata(
                    dataset, meta, base, metadata_version=metadata_version, metadata_cache=metadata_cache
                )
                existing_comments = None
                if existing_base_comments_by_object_id is not None:
                    existing_comments = existing_base_comments_by_object_id.get(base.pk)
                _load_comments(
                    dataset,
                    meta.comments,
                    base,
                    metadata_version,
                    existing_comments=existing_comments,
                    metadata_cache=metadata_cache,
                )

                model.base = base
                model.save()
                _create_errors(meta.errors, base)
            else:
                meta.errors.append(
                    _(
                        f"Nepavyko susieti bazinio modelio „{meta.name}“. "
                        f"Įsitikinkite, kad jis egzistuoja ir turi patvirtintą (stabilią) versiją."
                    )
                )
                _create_errors(meta.errors, model)

    elif model.base:
        base = model.base
        model.base = None
        model.save()

        if not base.base_models.exists():
            base.delete()


def _link_properties(
    dataset: Dataset,
    model: Model,
    model_meta: struct.Model,
    metadata_version: Version,
):
    ct = ContentType.objects.get_for_model(Property)
    model_ct = ContentType.objects.get_for_model(Model)
    prop_ids = [_metadata_uuid_key(meta.id) for meta in model_meta.properties.values() if meta.id]
    props_by_uuid = {}
    if prop_ids:
        prop_metadata = list(
            Metadata.objects.filter(
                content_type=ct,
                uuid__in=prop_ids,
                metadata_version=metadata_version,
                object_id__in=Property.objects.filter(model=model).values_list("id", flat=True),
            ).only("uuid", "object_id")
        )
        props = Property.objects.in_bulk([md.object_id for md in prop_metadata])
        props_by_uuid = {
            _metadata_uuid_key(md.uuid): props.get(md.object_id) for md in prop_metadata if props.get(md.object_id)
        }

    # Cache lookups per ref-model, but only for the ref-prop names we actually need.
    ref_model_props_by_name: dict[int, dict[str, Property]] = {}

    for prop_meta in model_meta.properties.values():
        if not prop_meta.id:
            continue
        if prop := props_by_uuid.get(_metadata_uuid_key(prop_meta.id)):
            if "." in prop_meta.name:
                _link_denorm_props(dataset, prop_meta, model, prop, metadata_version)

            if prop_meta.type in ("ref", "backref", "generic") and prop_meta.ref:
                # Stripping `property.ref` is needed during linking to find the related model, if it exists.
                property_meta_ref = prop_meta.ref.lstrip("/")
                # Resolve via Model↔Metadata join (not Metadata-only + in_bulk): batching that path
                # missed valid targets and left ref_model unset, breaking dependent export / Spinta.
                if ref_model := Model.objects.filter(
                    metadata__name=property_meta_ref,
                    metadata__content_type=model_ct,
                ).first():
                    prop.ref_model = ref_model
                    prop.save()

                    ref_props_needed = [n for n in prop_meta.ref_props if n]
                    if ref_props_needed:
                        ref_props_map = ref_model_props_by_name.setdefault(ref_model.pk, {})
                        missing_names = [n for n in set(ref_props_needed) if n not in ref_props_map]
                        if missing_names:
                            ref_prop_metadata = Metadata.objects.filter(
                                content_type=ct,
                                name__in=missing_names,
                                metadata_version=metadata_version,
                                object_id__in=Property.objects.filter(model=ref_model).values_list("id", flat=True),
                            ).only("name", "object_id")
                            ref_prop_rows = list(ref_prop_metadata.values("name", "object_id"))
                            model_props = Property.objects.in_bulk([row["object_id"] for row in ref_prop_rows])
                            ref_props_map.update(
                                {
                                    row["name"]: model_props.get(row["object_id"])
                                    for row in ref_prop_rows
                                    if model_props.get(row["object_id"])
                                }
                            )

                        PropertyList.objects.filter(
                            content_type=ct, object_id=prop.pk, metadata_version=metadata_version
                        ).delete()
                        for order, ref_prop_name in enumerate(prop_meta.ref_props, 1):
                            if ref_prop := ref_props_map.get(ref_prop_name):
                                PropertyList.objects.create(
                                    content_type=ct,
                                    object_id=prop.pk,
                                    property=ref_prop,
                                    order=order,
                                    metadata_version=metadata_version,
                                )
                    else:
                        # If there are no ref-props, still clear stale PropertyList rows.
                        PropertyList.objects.filter(
                            content_type=ct, object_id=prop.pk, metadata_version=metadata_version
                        ).delete()
                else:
                    message = _(
                        "Nepavyko susieti savybės „%(name)s“ per nurodytą ryšį „%(ref)s“. "
                        "Įsitikinkite, kad nurodytas modelis egzistuoja."
                    ) % {"name": prop_meta.name, "ref": prop_meta.ref}
                    _create_errors([message], model)


def _link_denorm_props(
    dataset: Dataset,
    prop_meta: struct.Property,
    model: Model,
    prop: Property,
    metadata_version: Version,
) -> Property:
    ct = ContentType.objects.get_for_model(Property)

    parent_prop = prop_meta.name.rsplit(".", 1)[0]
    if parent_prop_meta := Metadata.objects.filter(
        content_type=ct, name=parent_prop, dataset=dataset, metadata_version=metadata_version
    ).first():
        parent_prop = parent_prop_meta.object
    else:
        meta = struct.Property(
            id=str(uuid.uuid4()),
            name=parent_prop,
        )
        parent_prop = Property.objects.create(model=model, given=False, metadata_version=metadata_version)
        _create_or_update_metadata(dataset, meta, parent_prop, metadata_version=metadata_version)
        if "." in meta.name:
            parent_prop = _link_denorm_props(dataset, meta, model, parent_prop, metadata_version=metadata_version)

    prop.property = parent_prop
    prop.save()
    return prop


def _check_uri(dataset: Dataset, meta: struct.Metadata, uri: str):
    if uri and "://" not in uri and ":" not in uri:
        if hasattr(meta, "errors"):
            meta.errors.append(_(f'Neteisingas uri "{uri}" formatas.'))
    elif ":" in uri and "://" not in uri:
        prefix, name = uri.split(":")
        if not Prefix.objects.filter(
            (
                Q(
                    content_type=ContentType.objects.get_for_model(DatasetStructure),
                    object_id=dataset.current_structure.pk,
                )
                | Q(
                    content_type=ContentType.objects.get_for_model(Dataset),
                    object_id=dataset.pk,
                )
            )
            & Q(name=prefix)
        ):
            if hasattr(meta, "errors"):
                meta.errors.append(_(f'Prefiksas "{prefix}" duomenų ištekliuje neegzistuoja.'))


def get_data_from_spinta(model: Union[Model, str], uuid: str = None, query: str = "", timeout: int = 30):
    if uuid:
        url = f"{SPINTA_SERVER_URL}/{model}/{uuid}/?{query}"
    else:
        url = f"{SPINTA_SERVER_URL}/{model}/?{query}"
    try:
        res = requests.get(url, timeout=timeout)
    except requests.ReadTimeout:
        return {"errors": [gettext("Nepavyko gauti duomenų iš Saugyklos per nustatytą laiką")]}
    except requests.RequestException:
        logger.exception("Failed to fetch data from Spinta: %s", url)
        return {"errors": [gettext("Nepavyko gauti duomenų iš Saugyklos")]}

    try:
        data = json.loads(res.content)
        return data
    except JSONDecodeError:
        logger.exception("Invalid JSON response from Spinta: %s", url)
        return {"errors": [gettext("Gautas neteisingas duomenų formatas iš Saugyklos")]}


async def get_data_from_spinta_async(model: Union[Model, str], uuid: str = None, query: str = "", timeout: int = 30):
    if uuid:
        url = f"{SPINTA_SERVER_URL}/{model}/{uuid}/?{query}"
    else:
        url = f"{SPINTA_SERVER_URL}/{model}/?{query}"
    try:
        res = requests.get(url, timeout=timeout)
    except requests.ReadTimeout:
        return {"errors": [gettext("Nepavyko gauti duomenų iš Saugyklos per nustatytą laiką")]}
    except requests.RequestException:
        logger.exception("Failed to fetch data from Spinta: %s", url)
        return {"errors": [gettext("Nepavyko gauti duomenų iš Saugyklos")]}

    try:
        data = json.loads(res.content)
        return data
    except JSONDecodeError:
        logger.exception("Invalid JSON response from Spinta: %s", url)
        return {"errors": [gettext("Gautas neteisingas duomenų formatas iš Saugyklos")]}


def _parse_access(value: str):
    access = None
    if value:
        if value == "private":
            access = Metadata.PRIVATE
        elif value == "protected":
            access = Metadata.PROTECTED
        elif value == "public":
            access = Metadata.PUBLIC
        elif value == "open":
            access = Metadata.OPEN
    return access


def _parse_visibility(value: str) -> int:
    visibility_mapper = {
        "private": Metadata.PRIVATE,
        "protected": Metadata.PROTECTED,
        "package": Metadata.PACKAGE,
        "public": Metadata.VISIBILITY_PUBLIC,
    }
    return visibility_mapper.get(value)


@lru_cache(maxsize=64)
def _get_status(value: str) -> Status | None:
    if value:
        return Status.objects.filter(codename=value).first()
    return Status.objects.filter(is_default=True).first()


def get_model_name(dataset: Dataset, name: str) -> str:
    if name.startswith("/"):
        return name[1:]
    elif not dataset or not dataset.name:
        return name
    else:
        return "/".join(
            [
                dataset.name,
                name,
            ]
        )


DATASET = [
    "id",
    "dataset",
    "resource",
    "base",
    "model",
    "property",
    "type",
    "ref",
    "source",
    "source.type",
    "prepare",
    "origin",
    "count",
    "level",
    "status",
    "visibility",
    "access",
    "uri",
    "eli",
    "title",
    "description",
]


class IterableFile:
    def __init__(self):
        self.writes = []

    def __iter__(self):
        yield from self.writes
        self.writes = []

    def write(self, data):
        self.writes.append(data)


def export_dataset_structure(dataset: Dataset, version: Version | None = None) -> StringIO:
    if not version:
        version = dataset.latest_version()
    cols = DATASET
    rows = datasets_to_tabular(dataset, version=version)
    rows = ({c: row[c] for c in cols} for row in rows)
    stream = IterableFile()
    writer = csv.DictWriter(stream, fieldnames=cols)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
        yield from stream


def _export_dataset_structure_to_stringio(dataset: Dataset, version: Version) -> StringIO:
    """Wrapper that converts the generator output to StringIO"""

    result = StringIO()

    for chunk in export_dataset_structure(dataset, version):
        result.write(chunk)

    result.seek(0)
    return result


def datasets_to_tabular(dataset: Dataset, version: Version | None = None) -> Generator:
    if dataset.current_structure:
        yield from _prefixes_to_tabular(dataset.current_structure, separator=True, version=version)
    dependent_models = dataset.get_dependent_models(version=version)
    if dependent_models:
        yield from _dependent_models_to_tabular(dependent_models)
    yield from _dataset_to_tabular(dataset, separator=True, version=version)


def _dependent_models_to_tabular(dependent_models: list) -> Generator:
    """
    Render dependent (child) models in tabular format.
    """
    if not dependent_models:
        return

    child_model_ids = {dep["child_model_id"] for dep in dependent_models}
    models = (
        Model.objects.filter(pk__in=child_model_ids)
        .select_related("dataset", "metadata_version", "base")
        .prefetch_related("metadata", "property_list__property__metadata", "base__metadata")
    )

    def _pick_metadata(meta_qs: QuerySet[Metadata], version: Version | None) -> Metadata | None:
        if version is None:
            return meta_qs.first()
        return meta_qs.filter(metadata_version=version).first()

    models_by_dataset: dict[int, dict] = {}
    dependent_model_ids: set[int] = set()
    for model in models:
        meta = _pick_metadata(model.metadata.all(), model.metadata_version)
        if not meta:
            logger.warning(
                "Missing metadata for dependent model (model_id=%s, dataset_id=%s, metadata_version_id=%s).",
                model.id,
                model.dataset_id,
                model.metadata_version_id,
            )
            continue
        dependent_model_ids.add(model.id)

        dataset = model.dataset
        dataset_meta = _pick_metadata(dataset.metadata.all(), model.metadata_version)
        dataset_name = dataset_meta.name if dataset_meta else ""
        if (
            dataset_meta
            and model.metadata_version
            and model.metadata_version.status != VersionStatus.DRAFT
            and model.metadata_version.major is not None
        ):
            dataset_name = f"{dataset_meta.name}/{model.metadata_version.major}"

        prop_names = set()
        prop_list_qs = model.property_list.all()
        if model.metadata_version is not None:
            prop_list_qs = prop_list_qs.filter(metadata_version=model.metadata_version)

        for prop_list_item in prop_list_qs:
            prop_meta_qs = prop_list_item.property.metadata.all()
            if model.metadata_version is not None:
                prop_meta_qs = prop_meta_qs.filter(metadata_version=model.metadata_version)
            if prop_meta := prop_meta_qs.first():
                prop_names.add(prop_meta.name)

        dataset_bucket = models_by_dataset.setdefault(
            dataset.id,
            {
                "dataset": dataset,
                "dataset_meta": dataset_meta,
                "dataset_name": dataset_name,
                "models": [],
            },
        )
        if dataset_bucket["dataset_meta"] is None and dataset_meta is not None:
            dataset_bucket["dataset_meta"] = dataset_meta
            dataset_bucket["dataset_name"] = dataset_name

        dataset_bucket["models"].append(
            {
                "model": model,
                "meta": meta,
                "prop_names": prop_names,
            }
        )

    def _dataset_sort_key(entry: dict) -> str:
        dataset_name = entry["dataset_name"] or entry["dataset"].name or ""
        return dataset_name

    def _model_sort_key(entry: dict) -> tuple[int, str]:
        meta = entry["meta"]
        order = meta.order if meta.order is not None else 0
        return (order, meta.name)

    def _parse_ref_keys(ref_value: str | None) -> list[str]:
        if not ref_value:
            return []
        return [key.strip() for key in ref_value.split(",") if key.strip()]

    def _yield_pk_properties(target_model: Model, target_meta: Metadata, version: Version | None) -> Generator:
        prop_filter = {"model": target_model, "given": True}
        if version is not None:
            prop_filter["metadata_version"] = version
        pk_props = Property.objects.filter(**prop_filter).prefetch_related("metadata")
        pk_prop_meta_by_name = {}
        for prop in pk_props:
            prop_meta_qs = prop.metadata.all()
            if version is not None:
                prop_meta_qs = prop_meta_qs.filter(metadata_version=version)
            if prop_meta := prop_meta_qs.first():
                pk_prop_meta_by_name[prop_meta.name] = (prop, prop_meta)

        for ref_key in _parse_ref_keys(target_meta.ref):
            if ref_key in pk_prop_meta_by_name:
                prop, prop_meta = pk_prop_meta_by_name[ref_key]
                yield to_row(
                    DATASET,
                    {
                        "id": prop_meta.uuid,
                        "property": prop_meta.name,
                        "type": get_type_repr(prop_meta),
                        "level": prop_meta.level_given,
                        "access": _get_access(prop_meta.access),
                        "uri": prop_meta.uri,
                        "title": prop_meta.title,
                        "description": prop_meta.description,
                        "source": prop_meta.source,
                        "prepare": prop_meta.prepare,
                        "ref": _prop_ref_to_tabular(prop, prop_meta),
                        "status": _get_title(prop_meta.status),
                        "visibility": _get_visibility(prop_meta.visibility),
                        "eli": prop_meta.eli,
                        "count": prop_meta.count,
                    },
                )

    sorted_datasets = sorted(models_by_dataset.values(), key=_dataset_sort_key)
    for dataset_index, dataset_entry in enumerate(sorted_datasets):
        dataset = dataset_entry["dataset"]
        dataset_meta = dataset_entry["dataset_meta"]

        if dataset_meta:
            if lang := get_language():
                dataset.set_current_language(lang)
            yield to_row(
                DATASET,
                {
                    "id": dataset_meta.uuid,
                    "dataset": dataset_entry["dataset_name"],
                    "level": dataset_meta.level_given,
                    "access": _get_access(dataset_meta.access),
                    "title": dataset.title,
                    "description": dataset.description,
                },
            )

        rendered_model_ids: set[int] = set()
        base_models: list[dict] = []
        for model_entry in dataset_entry["models"]:
            base = model_entry["model"].base.model if model_entry["model"].base else None
            if base and base.id not in dependent_model_ids:
                base_meta = _pick_metadata(base.metadata.all(), base.metadata_version)
                if base_meta:
                    base_models.append(
                        {
                            "model": base,
                            "meta": base_meta,
                            "prop_names": set(),
                        }
                    )

        for base_entry in sorted(base_models, key=_model_sort_key):
            base_model = base_entry["model"]
            base_meta = base_entry["meta"]
            if base_model.id in rendered_model_ids:
                continue
            yield to_row(
                DATASET,
                {
                    "id": base_meta.uuid,
                    "model": _to_relative_model_name(base_meta.name, dataset),
                    "level": base_meta.level_given,
                    "access": _get_access(base_meta.access),
                    "title": base_meta.title,
                    "description": base_meta.description,
                    "uri": base_meta.uri,
                    "source": base_meta.source,
                    "status": _get_title(base_meta.status),
                    "visibility": _get_visibility(base_meta.visibility),
                    "count": base_meta.count,
                    "eli": base_meta.eli,
                    "prepare": base_meta.prepare,
                    "ref": base_meta.ref or "",
                },
            )
            yield from _yield_pk_properties(base_model, base_meta, base_model.metadata_version)
            rendered_model_ids.add(base_model.id)

        current_base_key: tuple[int, int | None] | None = None
        for model_entry in sorted(dataset_entry["models"], key=_model_sort_key):
            model = model_entry["model"]
            meta = model_entry["meta"]
            if model.id in rendered_model_ids:
                continue
            next_base_key = None
            if model.base:
                base_version_id = model.metadata_version_id or model.base.metadata_version_id
                next_base_key = (model.base.id, base_version_id)
            if next_base_key != current_base_key:
                if current_base_key is not None:
                    yield from _end_marker("base")
                if model.base:
                    base_version = model.metadata_version or model.base.metadata_version
                    yield from _base_to_tabular(model.base, version=base_version)
                current_base_key = next_base_key
            yield to_row(
                DATASET,
                {
                    "id": meta.uuid,
                    "model": _to_relative_model_name(meta.name, dataset),
                    "level": meta.level_given,
                    "access": _get_access(meta.access),
                    "title": meta.title,
                    "description": meta.description,
                    "uri": meta.uri,
                    "source": meta.source,
                    "status": _get_title(meta.status),
                    "visibility": _get_visibility(meta.visibility),
                    "count": meta.count,
                    "eli": meta.eli,
                    "prepare": meta.prepare,
                    "ref": meta.ref or "",
                },
            )
            yield from _yield_pk_properties(model, meta, model.metadata_version)
        if current_base_key is not None and dataset_index < len(sorted_datasets) - 1:
            yield from _end_marker("base")


def to_row(keys, values) -> Dict:
    return {k: values.get(k) for k in keys}


def _end_marker(name):
    yield to_row(DATASET, {name: "/"})


def _prefixes_to_tabular(obj: models.Model, separator: bool = False, version: Version | None = None) -> Generator:
    ct = ContentType.objects.get_for_model(obj)
    prefix_filter = {"content_type": ct, "object_id": obj.pk}
    metadata_queryset = Metadata.objects.all()

    if version is not None:
        prefix_filter["metadata_version"] = version
        metadata_queryset = metadata_queryset.filter(metadata_version=version)

    prefixes = (
        Prefix.objects.filter(**prefix_filter)
        .prefetch_related(Prefetch("metadata", queryset=metadata_queryset.order_by("order")))
        .order_by("metadata__order")
    )

    first = True
    for prefix in prefixes:
        if meta := prefix.metadata.first():
            yield to_row(
                DATASET,
                {
                    "id": meta.uuid,
                    "type": "prefix" if first else "",
                    "ref": meta.name,
                    "uri": meta.uri,
                    "title": meta.title,
                    "description": meta.description,
                },
            )
            first = False

    if separator and prefixes:
        yield to_row(DATASET, {})


def _dataset_to_tabular(dataset: Dataset, separator: bool = False, version: Version | None = None) -> Generator:
    if lang := get_language():
        dataset.set_current_language(lang)
    meta_query = dataset.metadata.all()
    if version is not None:
        meta_query = meta_query.filter(metadata_version=version)
    if meta := meta_query.first():
        dataset_name = meta.name
        if version is not None and version.status != VersionStatus.DRAFT and version.major is not None:
            dataset_name = f"{meta.name}/{version.major}"
        yield to_row(
            DATASET,
            {
                "id": meta.uuid,
                "dataset": dataset_name,
                "level": meta.level_given,
                "access": _get_access(meta.access),
                "title": dataset.title,
                "description": dataset.description,
            },
        )
    yield from _prefixes_to_tabular(dataset, separator=separator, version=version)
    yield from _enums_to_tabular(dataset, separator=separator, version=version)
    yield from _params_to_tabular(dataset, separator=separator, version=version)
    yield from _dataset_resources_to_tabular(dataset, version=version)
    yield from _models_to_tabular(dataset, separator=separator, version=version)


def _dataset_resources_to_tabular(dataset: Dataset, version: Version | None = None) -> Generator:
    distribution_filter = {"dataset": dataset, "model__isnull": True}
    model_filter = {"dataset": dataset, "distribution__isnull": False}
    metadata_queryset = Metadata.objects.all()
    if version is not None:
        distribution_filter["metadata_version"] = version
        model_filter["metadata__metadata_version"] = version
        metadata_queryset = metadata_queryset.filter(metadata_version=version)
    distributions = (
        DatasetDistribution.objects.filter(**distribution_filter)
        .prefetch_related(Prefetch("metadata", queryset=metadata_queryset.order_by("order")))
        .order_by("metadata__order")
    )
    distributions_with_models = set(Model.objects.filter(**model_filter).values_list("distribution_id", flat=True))
    for distribution in distributions:
        if distribution.pk not in distributions_with_models:
            yield from _resource_to_tabular(distribution, version=version)


def _enums_to_tabular(obj: models.Model, separator: bool = False, version: Version | None = None) -> Generator:
    ct = ContentType.objects.get_for_model(obj)
    enum_filter = {"content_type": ct, "object_id": obj.pk}
    metadata_queryset = Metadata.objects.all()
    enum_item_filter = {}

    if version is not None:
        enum_filter["metadata_version"] = version
        metadata_queryset = metadata_queryset.filter(metadata_version=version)
        enum_item_filter["metadata_version"] = version

    enum_item_queryset = EnumItem.objects.filter(**enum_item_filter).prefetch_related(
        Prefetch("metadata", queryset=metadata_queryset.order_by("order"))
    )
    enums = Enum.objects.filter(**enum_filter).prefetch_related(Prefetch("enumitem_set", queryset=enum_item_queryset))
    for enum in enums:
        first = True
        enum_items = list(enum.enumitem_set.all())
        for item in enum_items:
            if meta := item.metadata.first():
                yield to_row(
                    DATASET,
                    {
                        "id": meta.uuid,
                        "type": "enum" if first else "",
                        "ref": enum.name if (first and not isinstance(obj, Property)) else "",
                        "source": meta.source,
                        "prepare": meta.prepare,
                        "level": meta.level_given,
                        "access": _get_access(meta.access),
                        "title": meta.title,
                        "description": meta.description,
                        "status": _get_title(meta.status),
                        "visibility": _get_visibility(meta.visibility),
                        "eli": meta.eli,
                        "count": meta.count,
                    },
                )
                first = False

    if separator and enums:
        yield to_row(DATASET, {})


def _params_to_tabular(
    obj: models.Model | Dataset | DatasetDistribution, separator: bool = False, version: Version | None = None
) -> Generator:
    ct = ContentType.objects.get_for_model(obj)
    param_filter = {"content_type": ct, "object_id": obj.pk}
    metadata_queryset = Metadata.objects.all()
    param_item_filter = {}

    if version is not None:
        param_filter["metadata_version"] = version
        metadata_queryset = metadata_queryset.filter(metadata_version=version)
        param_item_filter["metadata_version"] = version

    param_item_queryset = ParamItem.objects.filter(**param_item_filter).prefetch_related(
        Prefetch("metadata", queryset=metadata_queryset.order_by("order"))
    )

    params = Param.objects.filter(**param_filter).prefetch_related(
        Prefetch("paramitem_set", queryset=param_item_queryset)
    )

    for param in params:
        first = True
        param_items = list(param.paramitem_set.all())
        for item in param_items:
            if meta := item.metadata.first():
                yield to_row(
                    DATASET,
                    {
                        "id": meta.uuid,
                        "type": "param" if first else "",
                        "ref": param.name if first else "",
                        "source": meta.source,
                        "prepare": meta.prepare,
                        "access": _get_access(meta.access),
                        "title": meta.title,
                        "description": meta.description,
                        "status": _get_title(meta.status),
                        "visibility": _get_visibility(meta.visibility),
                        "eli": meta.eli,
                        "count": meta.count,
                    },
                )
                first = False

    if separator and params:
        yield to_row(DATASET, {})


def _models_to_tabular(dataset: Dataset, separator: bool = False, version: Version | None = None) -> Generator:
    model_filter = {"dataset": dataset}
    model_metadata_filter = {}
    property_list_filter = {}
    metadata_queryset = Metadata.objects.all()
    property_metadata_queryset = Metadata.objects.all()
    distribution_metadata_queryset = Metadata.objects.all()
    base_metadata_queryset = Metadata.objects.all()

    if version is not None:
        model_filter["metadata_version"] = version
        model_metadata_filter["metadata_version"] = version
        property_list_filter["metadata_version"] = version
        metadata_queryset = metadata_queryset.filter(metadata_version=version)
        property_metadata_queryset = property_metadata_queryset.filter(metadata_version=version)
        distribution_metadata_queryset = distribution_metadata_queryset.filter(metadata_version=version)
        base_metadata_queryset = base_metadata_queryset.filter(metadata_version=version)

    property_list_queryset = (
        PropertyList.objects.filter(**property_list_filter)
        .select_related("property")
        .prefetch_related(Prefetch("property__metadata", queryset=property_metadata_queryset))
    )

    dataset_models = (
        Model.objects.filter(**model_filter)
        .select_related("distribution", "base")
        .prefetch_related(
            Prefetch("metadata", queryset=metadata_queryset.order_by("order")),
            Prefetch("property_list", queryset=property_list_queryset),
            Prefetch("distribution__metadata", queryset=distribution_metadata_queryset),
            Prefetch("base__metadata", queryset=base_metadata_queryset),
        )
        .order_by("metadata__order")
    )

    resource = None
    base = None
    for model in dataset_models:
        if model.distribution != resource:
            if resource:
                yield from _end_marker("resource")
            if model.distribution:
                yield from _resource_to_tabular(model.distribution, version=version)
            resource = model.distribution

        if model.base and not base:
            yield from _base_to_tabular(model.base, version=version)
            base = model.base
        elif not model.base and base:
            yield from _end_marker("base")
            base = None

        if meta := model.metadata.first():
            prop_names = set()
            for prop_list_item in model.property_list.all():
                if prop_meta := prop_list_item.property.metadata.first():
                    prop_names.add(prop_meta.name)
            yield to_row(
                DATASET,
                {
                    "id": meta.uuid,
                    "model": _to_relative_model_name(meta.name, dataset),
                    "level": meta.level_given,
                    "access": _get_access(meta.access),
                    "title": meta.title,
                    "description": meta.description,
                    "uri": meta.uri,
                    "source": meta.source,
                    "status": _get_title(meta.status),
                    "visibility": _get_visibility(meta.visibility),
                    "count": meta.count,
                    "eli": meta.eli,
                    "prepare": meta.prepare,
                    "ref": ", ".join(sorted(prop_names)) if prop_names else (meta.ref or ""),
                },
            )

            yield from _comments_to_tabular(model)
            yield from _params_to_tabular(model, version=version)
            yield from _properties_to_tabular(model, version=version)
            if separator:
                yield to_row(DATASET, {})


def _resource_models_to_tabular(
    resource: DatasetDistribution, separator: bool = False, version: Version | None = None
) -> Generator:
    model_filter = {"distribution": resource, "dataset": resource.dataset}
    model_metadata_filter = {}
    property_list_filter = {}
    metadata_queryset = Metadata.objects.all()
    property_metadata_queryset = Metadata.objects.all()
    distribution_metadata_queryset = Metadata.objects.all()
    base_metadata_queryset = Metadata.objects.all()

    if version is not None:
        model_filter["metadata_version"] = version
        model_metadata_filter["metadata_version"] = version
        property_list_filter["metadata_version"] = version
        metadata_queryset = metadata_queryset.filter(metadata_version=version)
        property_metadata_queryset = property_metadata_queryset.filter(metadata_version=version)
        distribution_metadata_queryset = distribution_metadata_queryset.filter(metadata_version=version)
        base_metadata_queryset = base_metadata_queryset.filter(metadata_version=version)

    property_list_queryset = (
        PropertyList.objects.filter(**property_list_filter)
        .select_related("property")
        .prefetch_related(Prefetch("property__metadata", queryset=property_metadata_queryset))
    )

    resource_models = (
        Model.objects.filter(**model_filter)
        .select_related("base")
        .prefetch_related(
            Prefetch("metadata", queryset=metadata_queryset.order_by("order")),
            Prefetch("property_list", queryset=property_list_queryset),
            Prefetch("distribution__metadata", queryset=distribution_metadata_queryset),
            Prefetch("base__metadata", queryset=base_metadata_queryset),
        )
        .order_by("metadata__order")
    )

    base = None
    for model in resource_models:
        if model.base and not base:
            yield from _base_to_tabular(model.base, version=version)
            base = model.base
        elif not model.base and base:
            yield from _end_marker("base")
            base = None

        if meta := model.metadata.first():
            prop_names = set()
            for prop_list_item in model.property_list.all():
                if prop_meta := prop_list_item.property.metadata.first():
                    prop_names.add(prop_meta.name)

            yield to_row(
                DATASET,
                {
                    "id": meta.uuid,
                    "model": _to_relative_model_name(meta.name, resource.dataset),
                    "level": meta.level_given,
                    "access": _get_access(meta.access),
                    "title": meta.title,
                    "description": meta.description,
                    "uri": meta.uri,
                    "source": meta.source,
                    "prepare": meta.prepare,
                    "ref": ", ".join(sorted(prop_names)) if prop_names else (meta.ref or ""),
                },
            )
            yield from _params_to_tabular(model, version=version)
            yield from _properties_to_tabular(model, version=version)
            if separator:
                yield to_row(DATASET, {})


def _resource_to_tabular(resource: DatasetDistribution, version: Version | None = None) -> Generator:
    if lang := get_language():
        resource.set_current_language(lang)
    meta = resource.metadata.first() if version is None else resource.metadata.filter(metadata_version=version).first()
    if meta:
        yield to_row(
            DATASET,
            {
                "id": meta.uuid,
                "resource": meta.name,
                "source": meta.source,
                "prepare": meta.prepare,
                "type": meta.type,
                "ref": meta.ref,
                "level": meta.level_given,
                "access": _get_access(meta.access),
                "title": resource.title,
                "description": resource.description,
            },
        )
        yield from _params_to_tabular(resource)
    yield from _comments_to_tabular(resource)


def _comments_to_tabular(obj: models.Model) -> Generator:
    ct = ContentType.objects.get_for_model(obj)
    comments = Comment.objects.filter(content_type=ct, object_id=obj.pk, type=Comment.STRUCTURE).prefetch_related(
        Prefetch("metadata", queryset=Metadata.objects.all().order_by("order"))
    )
    first = True
    comments_list = list(comments)
    for comment in comments_list:
        if meta := comment.metadata.first():
            yield to_row(
                DATASET,
                {
                    "id": meta.uuid,
                    "type": "comment" if first else "",
                    "ref": meta.ref,
                    "source": meta.source,
                    "prepare": meta.prepare,
                    "level": meta.level_given,
                    "status": _get_title(meta.status),
                    "visibility": _get_visibility(meta.visibility),
                    "access": _get_access(meta.access),
                    "uri": meta.uri,
                    "title": meta.title,
                    "description": meta.description,
                },
            )
            first = False


def _base_to_tabular(base: Base, version: Version | None = None) -> Generator:
    meta_query = base.metadata.all()
    if version is not None:
        meta_query = meta_query.filter(metadata_version=version)
    if meta := meta_query.first():
        yield to_row(
            DATASET,
            {
                "id": meta.uuid,
                "base": _to_relative_model_name(meta.name, meta.dataset),
                "ref": meta.ref,
            },
        )
        yield from _comments_to_tabular(base)


def _properties_to_tabular(model: Model, version: Version | None = None) -> Generator:
    prop_filter = {"model": model, "given": True}
    property_metadata_queryset = Metadata.objects.all()

    if version is not None:
        prop_filter["metadata_version"] = version
        property_metadata_queryset = property_metadata_queryset.filter(metadata_version=version)

    props = (
        Property.objects.filter(**prop_filter)
        .prefetch_related(Prefetch("metadata", queryset=property_metadata_queryset.order_by("order")))
        .order_by("metadata__order", "pk")
    )
    props_list = list(props)
    for prop in props_list:
        if meta := prop.metadata.first():
            yield to_row(
                DATASET,
                {
                    "id": meta.uuid,
                    "property": meta.name,
                    "type": get_type_repr(meta),
                    "level": meta.level_given,
                    "access": _get_access(meta.access),
                    "uri": meta.uri,
                    "title": meta.title,
                    "description": meta.description,
                    "source": meta.source,
                    "prepare": meta.prepare,
                    "ref": _prop_ref_to_tabular(prop, meta),
                    "status": _get_title(meta.status),
                    "visibility": _get_visibility(meta.visibility),
                    "eli": meta.eli,
                    "count": meta.count,
                },
            )

            yield from _comments_to_tabular(prop)
            yield from _enums_to_tabular(prop, version=version)


def _to_relative_model_name(name: str, dataset: Dataset) -> str:
    if dataset.name:
        if name == dataset.name:
            return name
        prefix = dataset.name + "/"
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def _get_access(acess: int) -> str:
    if acess == Metadata.PRIVATE:
        return "private"
    elif acess == Metadata.PROTECTED:
        return "protected"
    elif acess == Metadata.PUBLIC:
        return "public"
    elif acess == Metadata.OPEN:
        return "open"
    return ""


def _get_visibility(visibility: int) -> str:
    if visibility == Metadata.PRIVATE:
        return "private"
    elif visibility == Metadata.PROTECTED:
        return "protected"
    elif visibility == Metadata.PACKAGE:
        return "package"
    elif visibility == Metadata.VISIBILITY_PUBLIC:
        return "public"
    return ""


def _get_title(obj: Status | None) -> str:
    return "" if obj is None else obj.codename


def _prop_ref_to_tabular(prop: Property, meta: Metadata) -> str:
    ref = meta.ref
    if meta.type == "ref":
        ref_model = _to_relative_model_name(meta.ref, meta.dataset)
        ref_props = prop.property_list.values_list("property__metadata__name", flat=True)
        if ref_props:
            ref_props = ", ".join(ref_props)
            ref = f"{ref_model}[{ref_props}]"
        else:
            ref = ref_model
    return ref


def get_srid(type_args):
    srid = None
    if type_args:
        type_args = type_args.split(",")
        type_args = [arg.strip() for arg in type_args]
        if len(type_args) == 1 and type_args[0].isdigit():
            srid = int(type_args[0])
        elif len(type_args) == 2 and type_args[1].isdigit():
            srid = int(type_args[1])
    return srid


def transform_coordinates(point_x, point_y, source_srid, target_srid):
    transformer = Transformer.from_crs(f"EPSG:{source_srid}", f"EPSG:{target_srid}")
    return transformer.transform(point_x, point_y)


def get_allowed_visibilities(
    user: User, dataset: Dataset, model_action: Action, model_class: type[Model | Property | Enum] = Model
) -> set[int]:
    user_role = determine_user_role(user, dataset)
    allowed_visibilities: set[int] = set()

    if model_class == Model:
        acl = MODEL_VISIBILITY_ACL
    elif model_class == Property:
        acl = PROPERTY_VISIBILITY_ACL
    else:
        acl = ENUM_VISIBILITY_ACL

    for (cls, visibility, action), roles in acl.items():
        if cls == model_class and user_role in roles and action == model_action:
            allowed_visibilities.add(visibility)

    return allowed_visibilities


def generate_mermaid_diagram(dataset: Dataset, version: Version) -> str:
    context = create_context("cli")

    stream = _export_dataset_structure_to_stringio(dataset, version)
    manifest_path = ManifestPath(type="tabular", path=None, file=stream)
    manifest = _read_and_return_manifest(
        context,
        [manifest_path],
        external=True,
        format_names=False,
        order_by=None,
        rename_duplicates=False,
        verbose=False,
        check_config=False,
    )
    mermaid = write_mermaid_manifest(context, manifest, dataset.name)
    mermaid_click_links = _generate_mermaid_model_click_links(dataset, version)
    return mermaid + "\n" + mermaid_click_links


def _generate_mermaid_model_click_links(dataset: Dataset, version: Version) -> str:
    model_ids: set[int] = set(
        Model.objects.filter(dataset=dataset, metadata_version=version).values_list("pk", flat=True)
    )
    for dependent_model in dataset.get_dependent_models(version=version):
        child_id = dependent_model.get("child_model_id")
        if child_id is not None:
            model_ids.add(child_id)

    if not model_ids:
        return ""

    models = (
        Model.objects.filter(pk__in=model_ids)
        .select_related("dataset", "metadata_version")
        .prefetch_related("metadata")
    )

    base_url = f"{settings.META_SITE_PROTOCOL}://{settings.META_SITE_DOMAIN}"

    click_lines: list[str] = []
    for model in models:
        full_name = model.full_name
        basename = model.name
        path = reverse(
            "model-structure",
            kwargs={
                "pk": model.dataset_id,
                "version_id": model.metadata_version_id,
                "model": basename,
            },
        )
        click_lines.append(f'click `{full_name}` href "{base_url}{path}"')

    return "\n".join(click_lines)

"""DSA import into a DataService: every dataset of the DataService listed in the file is imported (#2846)."""

import csv
from dataclasses import dataclass, field

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _

import vitrina.datasets.structure as struct
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.datasets.structure import detect_read_errors, read
from vitrina.helpers import get_encoding
from vitrina.structure import VersionStatus
from vitrina.structure.models import (
    Base,
    Enum,
    EnumItem,
    Metadata,
    Model,
    ModelScope,
    Param,
    ParamItem,
    Prefix,
    Property,
    PropertyList,
    Version,
)
from vitrina.structure.services import _create_errors, _link_models, _load_comments, _load_datasets, _load_prefixes


@dataclass
class SkippedDataset:
    name: str
    reason: str


@dataclass
class DataServiceImport:
    # Critical errors: when there are any, nothing was changed.
    errors: list[str] = field(default_factory=list)
    skipped: list[SkippedDataset] = field(default_factory=list)
    new: list[str] = field(default_factory=list)
    # Datasets whose draft with structure would be replaced.
    drafts: list[str] = field(default_factory=list)


@dataclass
class _Target:
    dataset: Dataset
    meta: struct.Dataset
    version: Version | None = None


def import_dataservice_structure(structure: DatasetStructure, replace_drafts: bool = False) -> DataServiceImport:
    """Import the uploaded file into the datasets of `structure.dataset`, a DataService.

    With `replace_drafts`, drafts with structure of the listed datasets are replaced; otherwise they reject the import.
    """
    service = structure.dataset
    result = DataServiceImport()
    state = _read_file(structure, result)
    notes: list[str] = []
    targets = [] if result.errors else _plan(state, service, result, notes)

    if not result.errors and not targets and not result.new:
        result.errors.append(
            _("Faile nėra nė vieno šios duomenų paslaugos „%(name)s“ duomenų rinkinio.") % {"name": service.name}
        )
    if result.new:
        result.errors.append(
            _("Faile yra naujų duomenų rinkinių, kurių sukūrimas turi būti patvirtintas: %(names)s.")
            % {"names": ", ".join(result.new)}
        )
    if result.drafts and not replace_drafts:
        result.errors.append(
            _("Šių duomenų rinkinių juodraščiai būtų pakeisti, todėl importas turi būti patvirtintas: %(names)s.")
            % {"names": ", ".join(result.drafts)}
        )
    if result.errors:
        _create_errors(result.errors, structure)
        return result

    with transaction.atomic():
        _apply(state, structure, targets, replace_drafts)
        _create_errors(notes, structure)
    return result


def _read_file(structure: DatasetStructure, result: DataServiceImport) -> struct.State | None:
    encoding = get_encoding(structure.file.path)
    if errors := detect_read_errors(structure.file.path, encoding):
        result.errors.extend(errors)
        return None
    with open(structure.file.path, encoding=encoding, errors="replace") as f:
        state = read(csv.DictReader(f))
    result.errors.extend(state.errors)
    return state


def _plan(state: struct.State, service: Dataset, result: DataServiceImport, notes: list[str]) -> list[_Target]:
    targets = []
    for name, meta in state.manifest.datasets.items():
        if name == service.name:
            # The DataService has no structure of its own; its own rows never change its models.
            if meta.models:
                notes.append(
                    _(
                        "Duomenų paslaugos „%(name)s“ eilutėje nurodyti modeliai neįkelti: duomenų paslauga neturi "
                        "savo struktūros, todėl modelius importuokite į jos duomenų rinkinį."
                    )
                    % {"name": name}
                )
        elif not _belongs_to(name, service.name):
            result.skipped.append(SkippedDataset(name, _("Duomenų rinkinys nepriklauso šiai duomenų paslaugai.")))
        elif (dataset := _find_dataset(name, service)) is None:
            result.new.append(name)
        elif not dataset.is_descendant_of(service):
            notes.append(
                _("Duomenų rinkinys „%(name)s“ jau yra ne šioje duomenų paslaugoje, todėl neįkeltas.") % {"name": name}
            )
        else:
            targets.append(_Target(dataset, meta))
            if any(_has_structure(draft) for draft in _drafts(dataset)):
                result.drafts.append(name)
    return targets


def _belongs_to(name: str, service_name: str) -> bool:
    # Whole path segments only: "uapi/locations" belongs to "uapi", "uapi2/locations" does not.
    return name.startswith(service_name.rstrip("/") + "/")


def _find_dataset(name: str, service: Dataset) -> Dataset | None:
    ids = Metadata.objects.filter(content_type=ContentType.objects.get_for_model(Dataset), name=name).values_list(
        "object_id", flat=True
    )
    datasets = list(Dataset.objects.filter(pk__in=ids).exclude(deleted=True))
    return next((dataset for dataset in datasets if dataset.is_descendant_of(service)), None) or (
        datasets[0] if datasets else None
    )


def _apply(state: struct.State, structure: DatasetStructure, targets: list[_Target], replace_drafts: bool) -> None:
    replaced: list[Version] = []
    for target in targets:
        drafts = _drafts(target.dataset)
        if replace_drafts and any(_has_structure(draft) for draft in drafts):
            # The old drafts are removed only after their models' references are moved to the new ones.
            replaced.extend(drafts)
            target.version = _new_draft(target.dataset)
        else:
            # An empty draft, as every dataset gets at creation, is reused.
            target.version = drafts[-1] if drafts else _new_draft(target.dataset)
        _reuse_ids(target.dataset, target.meta)

    # First pass: every dataset without its references, so the order of datasets in the file does not matter.
    for target in targets:
        dataset_structure = DatasetStructure.objects.create(
            dataset=target.dataset,
            file=structure.file,
            filename=structure.filename,
            mime_type=structure.mime_type,
            size=structure.size,
        )
        # Update only this column: adding datasets re-sorts the tree, so a full save could write back a stale path.
        Dataset.objects.filter(pk=target.dataset.pk).update(current_structure=dataset_structure)
        target.dataset.current_structure = dataset_structure
        _load_comments(target.dataset, state.manifest.comments, dataset_structure, target.version)
        _load_prefixes(target.dataset, state.manifest.prefixes, dataset_structure, target.version)
        _load_datasets(state, target.dataset, target.version, link=False)

    # Second pass: link references, preferring the models just imported.
    versions = [target.version for target in targets]
    for target in targets:
        _link_models(target.dataset, target.meta, target.version, preferred_versions=versions)
        target.dataset.update_level()

    if replaced:
        _move_references(replaced, versions)
        _delete_drafts(replaced)


def _drafts(dataset: Dataset) -> list[Version]:
    return list(dataset.dataset_version.filter(status=VersionStatus.DRAFT).order_by("version"))


def _has_structure(version: Version) -> bool:
    # A draft holding only the dataset's own row, as created with the dataset, has no structure to lose.
    dataset_ct = ContentType.objects.get_for_model(Dataset)
    return Metadata.objects.filter(metadata_version=version).exclude(content_type=dataset_ct).exists()


def _new_draft(dataset: Dataset) -> Version:
    latest = dataset.latest_version()
    return Version.objects.create(
        dataset=dataset, status=VersionStatus.DRAFT, version=(latest.version if latest else 0) + 1
    )


def _reuse_ids(dataset: Dataset, meta: struct.Dataset) -> None:
    """Give the dataset, models and properties without an id the UUID they have in the latest version."""
    dataset_ct, model_ct = ContentType.objects.get_for_model(Dataset), ContentType.objects.get_for_model(Model)
    property_ct = ContentType.objects.get_for_model(Property)
    rows = (
        Metadata.objects.filter(dataset=dataset, content_type__in=[dataset_ct, model_ct, property_ct])
        .order_by(F("metadata_version__version").desc(nulls_last=True))
        .values_list("content_type_id", "name", "uuid", "object_id")
    )
    ids: dict[tuple, str] = {}
    model_names: dict[int, str] = {}
    properties = []
    for content_type_id, name, uuid, object_id in rows:
        if content_type_id == property_ct.pk:
            properties.append((name, uuid, object_id))
        else:
            ids.setdefault((content_type_id, name), uuid)
            if content_type_id == model_ct.pk:
                model_names[object_id] = name
    property_models = dict(
        Property.objects.filter(pk__in=[object_id for _, _, object_id in properties]).values_list("pk", "model_id")
    )
    for name, uuid, object_id in properties:
        if model_name := model_names.get(property_models.get(object_id)):
            ids.setdefault((property_ct.pk, model_name, name), uuid)

    meta.id = meta.id or ids.get((dataset_ct.pk, meta.name), "")
    for model_meta in meta.models.values():
        model_meta.id = model_meta.id or ids.get((model_ct.pk, model_meta.name), "")
        for prop_meta in model_meta.properties.values():
            prop_meta.id = prop_meta.id or ids.get((property_ct.pk, model_meta.name, prop_meta.name), "")


def _move_references(replaced: list[Version], versions: list[Version]) -> None:
    """Point references from other datasets to the new models with the same name, before the old ones are deleted."""
    model_ct = ContentType.objects.get_for_model(Model)
    old_models = Model.objects.filter(metadata_version__in=replaced)
    old_names = dict(
        Metadata.objects.filter(content_type=model_ct, metadata_version__in=replaced).values_list("object_id", "name")
    )
    new_ids = dict(
        Metadata.objects.filter(content_type=model_ct, metadata_version__in=versions).values_list("name", "object_id")
    )
    for prop in Property.objects.filter(ref_model__in=old_models).exclude(metadata_version__in=replaced):
        prop.ref_model_id = new_ids.get(old_names.get(prop.ref_model_id))
        prop.save(update_fields=["ref_model"])
    for base in Base.objects.filter(model__in=old_models).exclude(metadata_version__in=replaced):
        if new_id := new_ids.get(old_names.get(base.model_id)):
            base.model_id = new_id
            base.save(update_fields=["model"])


def _delete_drafts(replaced: list[Version]) -> None:
    # Deleting a version only cascades to its Metadata; the structure objects would stay without a version.
    for model in (PropertyList, EnumItem, ParamItem, Enum, Param, Property, ModelScope, Model, Base, Prefix):
        model.objects.filter(metadata_version__in=replaced).delete()
    Version.objects.filter(pk__in=[version.pk for version in replaced]).delete()

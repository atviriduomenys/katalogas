"""DSA import into a DataService: every dataset of the DataService listed in the file is imported (#2846)."""

import csv
from dataclasses import dataclass, field

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.translation import gettext_lazy as _

import vitrina.datasets.structure as struct
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.datasets.structure import detect_read_errors, read
from vitrina.helpers import get_encoding
from vitrina.structure import VersionStatus
from vitrina.structure.models import Metadata, Version
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


@dataclass
class _Target:
    dataset: Dataset
    meta: struct.Dataset
    version: Version | None = None


def import_dataservice_structure(structure: DatasetStructure) -> DataServiceImport:
    """Import the uploaded file into the datasets of `structure.dataset`, a DataService."""
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
    if result.errors:
        _create_errors(result.errors, structure)
        return result

    with transaction.atomic():
        _apply(state, structure, targets)
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


def _apply(state: struct.State, structure: DatasetStructure, targets: list[_Target]) -> None:
    # First pass: every dataset without its references, so the order of datasets in the file does not matter.
    for target in targets:
        dataset_structure = DatasetStructure.objects.create(
            dataset=target.dataset,
            file=structure.file,
            filename=structure.filename,
            mime_type=structure.mime_type,
            size=structure.size,
        )
        target.dataset.current_structure = dataset_structure
        target.dataset.save()
        target.version = _draft(target.dataset)
        _load_comments(target.dataset, state.manifest.comments, dataset_structure, target.version)
        _load_prefixes(target.dataset, state.manifest.prefixes, dataset_structure, target.version)
        _load_datasets(state, target.dataset, target.version, link=False)

    # Second pass: link references, preferring the models just imported.
    versions = [target.version for target in targets]
    for target in targets:
        _link_models(target.dataset, target.meta, target.version, preferred_versions=versions)
        target.dataset.update_level()


def _draft(dataset: Dataset) -> Version:
    if draft := dataset.dataset_version.filter(status=VersionStatus.DRAFT).order_by("-version").first():
        return draft
    latest = dataset.latest_version()
    return Version.objects.create(
        dataset=dataset, status=VersionStatus.DRAFT, version=(latest.version if latest else 0) + 1
    )

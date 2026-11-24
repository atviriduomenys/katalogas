"""DSA import into a DataService: every dataset of the DataService listed in the file is imported (#2846)."""

import csv
import uuid
from dataclasses import dataclass, field

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F
from django.http import HttpRequest
from django.utils.translation import get_language, gettext_lazy as _

import vitrina.datasets.structure as struct
from vitrina.datasets.models import Dataset, DatasetStructure, DCATResourceSubclass
from vitrina.datasets.structure import detect_read_errors, read
from vitrina.datasets.view_helpers import (
    create_dataset_representative_and_attribution,
    create_tasks_and_notify_subscribers_about_dataset_creation,
)
from vitrina.helpers import get_encoding
from vitrina.orgs.models import Organization
from vitrina.orgs.services import Action, has_perm
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
from vitrina.users.models import User


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
    # True when the only errors are new datasets or drafts that the user can confirm.
    confirmable: bool = False


@dataclass
class _Target:
    dataset: Dataset
    meta: struct.Dataset
    version: Version | None = None


@dataclass
class _Access:
    """Rights of the website `user` or the UAPI agent's `organization`; without either nothing is checked."""

    service: Dataset
    user: User | None = None
    organization: Organization | None = None

    def can_change(self, dataset: Dataset) -> bool:
        if self.user is not None:
            action = Action.INFORMATION_SYSTEM_UPDATE if dataset.subclass.is_information_system else Action.CREATE
            return has_perm(self.user, action, DatasetStructure, dataset)
        if self.organization is not None:
            return dataset.organization_id == self.organization.pk
        return True

    def can_create(self) -> bool:
        if self.user is not None:
            return has_perm(self.user, Action.CREATE, Dataset, self.service)
        if self.organization is not None:
            return self.service.organization_id == self.organization.pk
        return True


def import_dataservice_structure(
    structure: DatasetStructure,
    *,
    user: User | None = None,
    organization: Organization | None = None,
    request: HttpRequest | None = None,
    create_missing: bool = False,
    replace_drafts: bool = False,
    check_only: bool = False,
) -> DataServiceImport:
    """Import the uploaded file into the datasets of `structure.dataset`, a DataService.

    New datasets are created only with `create_missing`, and drafts with structure are replaced only with
    `replace_drafts`; otherwise they reject the import. With `check_only` nothing is changed.
    """
    service = structure.dataset
    access = _Access(service, user, organization)
    result = DataServiceImport()
    state = _read_file(structure, result)
    notes: list[str] = []
    listed = [] if result.errors else _plan(state, service, result, notes)
    targets = _changeable(listed, access, result)

    if not result.errors and not targets and not result.new:
        if listed:
            result.errors.append(_("Negalite keisti nė vieno faile nurodyto šios duomenų paslaugos duomenų rinkinio."))
        else:
            result.errors.append(
                _("Faile nėra nė vieno šios duomenų paslaugos „%(name)s“ duomenų rinkinio.") % {"name": service.name}
            )
    if result.new and not access.can_create():
        result.errors.append(
            _("Neturite teisių kurti duomenų rinkinių šioje duomenų paslaugoje: %(names)s.")
            % {"names": ", ".join(result.new)}
        )
    blocking = bool(result.errors)
    if result.new and not blocking and not create_missing:
        result.errors.append(
            _("Faile yra naujų duomenų rinkinių, kurių sukūrimas turi būti patvirtintas: %(names)s.")
            % {"names": ", ".join(result.new)}
        )
    if result.drafts and not replace_drafts:
        result.errors.append(
            _("Šių duomenų rinkinių juodraščiai būtų pakeisti, todėl importas turi būti patvirtintas: %(names)s.")
            % {"names": ", ".join(result.drafts)}
        )
    result.confirmable = not blocking and bool(result.errors)
    if result.errors:
        # Waiting for confirmation is not an error of the file, so it is not stored on it.
        if not result.confirmable and not check_only:
            _create_errors(result.errors, structure)
        return result
    if check_only:
        return result

    with transaction.atomic():
        for name in result.new:
            meta = state.manifest.datasets[name]
            targets.append(_Target(_create_dataset(service, meta, request), meta))
        # Adding datasets re-sorts the tree, so the targets are read again.
        for target in targets:
            target.dataset = Dataset.objects.get(pk=target.dataset.pk)
        _apply(state, structure, targets, replace_drafts)
        _create_errors(notes, structure)
        # The DataService points to the file only once it is imported; an update keeps its tree path untouched.
        Dataset.objects.filter(pk=service.pk).update(current_structure=structure)
    return result


def _read_file(structure: DatasetStructure, result: DataServiceImport) -> struct.State | None:
    encoding = get_encoding(structure.file.path)
    if errors := detect_read_errors(structure.file.path, encoding):
        result.errors.extend(errors)
        return None
    with open(structure.file.path, encoding=encoding, errors="replace") as f:
        try:
            state = read(csv.DictReader(f))
        except KeyError as error:
            result.errors.append(_("Faile trūksta stulpelio %(column)s.") % {"column": error})
            return None
        except ValueError as error:
            result.errors.append(_("Failo nepavyko perskaityti: %(error)s") % {"error": error})
            return None
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


def _changeable(targets: list[_Target], access: _Access, result: DataServiceImport) -> list[_Target]:
    allowed = []
    for target in targets:
        if access.can_change(target.dataset):
            allowed.append(target)
            if any(_has_structure(draft) for draft in _drafts(target.dataset)):
                result.drafts.append(target.meta.name)
        else:
            result.skipped.append(SkippedDataset(target.meta.name, _("Neturite teisių keisti šio duomenų rinkinio.")))
    return allowed


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

    if replaced:
        _move_references(replaced, versions)
        _delete_drafts(replaced)
    # The level averages every version, so it is set once the replaced drafts are gone.
    for target in targets:
        target.dataset.update_level()


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
    """Give the dataset, models and properties the UUID they have in the latest version.

    An object is identified by its full name, so an existing UUID wins over the file's id. The file's id is kept
    only for objects that are new.
    """
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
    for content_type_id, name, uid, object_id in rows:
        if content_type_id == property_ct.pk:
            properties.append((name, uid, object_id))
        else:
            ids.setdefault((content_type_id, name), uid)
            if content_type_id == model_ct.pk:
                model_names[object_id] = name
    property_models = dict(
        Property.objects.filter(pk__in=[object_id for _, _, object_id in properties]).values_list("pk", "model_id")
    )
    for name, uid, object_id in properties:
        if model_name := model_names.get(property_models.get(object_id)):
            ids.setdefault((property_ct.pk, model_name, name), uid)

    meta.id = ids.get((dataset_ct.pk, meta.name)) or meta.id
    for model_meta in meta.models.values():
        model_meta.id = ids.get((model_ct.pk, model_meta.name)) or model_meta.id
        for prop_meta in model_meta.properties.values():
            prop_meta.id = ids.get((property_ct.pk, model_meta.name, prop_meta.name)) or prop_meta.id


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

    # Reference keys, such as `id` in `Location[id]`, would be deleted with the old properties.
    old_keys = _property_keys(replaced, old_names)
    new_model_names = {model_id: name for name, model_id in new_ids.items()}
    new_props = {key: prop_id for prop_id, key in _property_keys(versions, new_model_names).items()}
    for item in PropertyList.objects.filter(property_id__in=old_keys).exclude(metadata_version__in=replaced):
        if new_id := new_props.get(old_keys[item.property_id]):
            item.property_id = new_id
            item.save(update_fields=["property"])


def _property_keys(versions: list[Version], model_names: dict[int, str]) -> dict[int, tuple[str, str]]:
    """Map the properties of `versions` to their model's full name and their own name."""
    property_ct = ContentType.objects.get_for_model(Property)
    names = dict(
        Metadata.objects.filter(content_type=property_ct, metadata_version__in=versions).values_list(
            "object_id", "name"
        )
    )
    return {
        prop_id: (model_names[model_id], names[prop_id])
        for prop_id, model_id in Property.objects.filter(pk__in=names).values_list("pk", "model_id")
        if model_id in model_names
    }


def _delete_drafts(replaced: list[Version]) -> None:
    # Deleting a version only cascades to its Metadata; the structure objects would stay without a version.
    for model in (PropertyList, EnumItem, ParamItem, Enum, Param, Property, ModelScope, Model, Base, Prefix):
        model.objects.filter(metadata_version__in=replaced).delete()
    Version.objects.filter(pk__in=[version.pk for version in replaced]).delete()


def _create_dataset(service: Dataset, meta: struct.Dataset, request: HttpRequest | None) -> Dataset:
    """Create a dataset of the DataService as the website does: draft, metadata, representative and notifications."""
    dataset = Dataset(
        organization=service.organization,
        subclass=DCATResourceSubclass.objects.get(name=DCATResourceSubclass.DATASET),
        is_public=False,
    )
    dataset.set_current_language(get_language())
    dataset.title = meta.title or meta.name.rsplit("/", 1)[-1]
    # The dataset form requires a description.
    dataset.description = meta.description or dataset.title
    dataset.access_rights = _access_rights(meta)
    # Treebeard places the child by the parent's in-memory child count, so it must be fresh.
    service.refresh_from_db()
    dataset = service.add_child(instance=dataset)
    version = Version.objects.create(dataset=dataset, version=1, status=VersionStatus.DRAFT)
    Metadata.objects.create(
        uuid=str(uuid.uuid4()),
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=dataset.pk,
        name=meta.name,
        title=dataset.title,
        description=dataset.description,
        prepare_ast={},
        version=1,
        metadata_version=version,
    )
    if request is not None:
        # Sent only if the whole import succeeds, so nobody is told about a dataset that was rolled back.
        transaction.on_commit(lambda: create_tasks_and_notify_subscribers_about_dataset_creation(request, dataset))
    create_dataset_representative_and_attribution(dataset)
    return dataset


# From the most open: the first access found among the properties decides.
_ACCESS_RIGHTS = (
    ("open", Dataset.PUBLIC),
    ("public", Dataset.RESTRICTED),
    ("protected", Dataset.NON_PUBLIC),
    ("private", Dataset.CONFIDENTIAL),
)


def _access_rights(meta: struct.Dataset) -> str:
    """Access rights of a new dataset: its most open property, which inherits access from its model and dataset."""
    accesses = {
        prop.access or model.access or meta.access
        for model in meta.models.values()
        for prop in model.properties.values()
    }
    return next((rights for access, rights in _ACCESS_RIGHTS if access in accesses), Dataset.CONFIDENTIAL)

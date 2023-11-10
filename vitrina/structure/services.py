import csv
import json
import uuid
from io import StringIO
from json import JSONDecodeError
from typing import Union, Tuple, List, Dict

import requests
from django.db.models import Q
from lark import ParseError
from pyproj import Transformer

import vitrina.datasets.structure as struct

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from vitrina import settings
from vitrina.comments.models import Comment
from vitrina.datasets.models import DatasetStructure, Dataset
from vitrina.datasets.structure import detect_read_errors, read
from vitrina.resources.models import DatasetDistribution, Format
from vitrina.structure import spyna
from vitrina.structure.helpers import get_type_repr
from vitrina.structure.models import Metadata, Model, Property, Prefix, Enum, EnumItem, PropertyList, Param, \
    ParamItem, Base
from vitrina.tasks.models import Task
from vitrina.users.models import User


def create_structure_objects(structure: DatasetStructure) -> None:
    sys_user, _ = User.objects.get_or_create(email=settings.SYSTEM_USER_EMAIL)
    ct = ContentType.objects.get_for_model(DatasetStructure)

    if structure.file:
        Comment.objects.filter(
            content_type=ct,
            object_id=structure.pk,
            type=Comment.STRUCTURE_ERROR
        ).delete()

        errors = []
        if detect_read_errors(structure.file.path):
            errors = detect_read_errors(structure.file.path)
        else:
            with open(
                    structure.file.path,
                    encoding='utf-8',
                    errors='replace',
            ) as f:
                reader = csv.DictReader(f)
                state = read(reader)
                if state.errors:
                    errors = state.errors
                else:
                    _load_comments(structure.dataset, state.manifest.comments, structure)
                    _load_prefixes(structure.dataset, state.manifest.prefixes, structure)
                    _load_datasets(state, structure.dataset)
                    _load_models(state, structure.dataset)
                    _link_distributions(state, structure.dataset)
                    _link_models(structure.dataset, state)
                    structure.dataset.update_level()

        for error in errors:
            Comment.objects.create(
                body=error,
                user=sys_user,
                content_type=ct,
                object_id=structure.pk,
                type=Comment.STRUCTURE_ERROR
            )
            Task.objects.create(
                title=f"Rasta klaida duomenyse: {ct}, id: {structure.pk}",
                description=f"Duomenyse {ct}, id: {structure.pk} aptikta klaida.",
                content_type=ct,
                object_id=structure.pk,
                status=Task.CREATED,
                user=sys_user
            )

def _load_datasets(
    state: struct.State,
    dataset: Dataset
):
    ct = ContentType.objects.get_for_model(dataset)
    existing_metadata = Metadata.objects.filter(
        content_type=ct,
        object_id=dataset.pk
    )
    loaded_metadata = []

    for i, meta in enumerate(state.manifest.datasets.values(), 1):
        if metadata := Metadata.objects.filter(
            ~Q(uuid=meta.id),
            content_type=ct,
            name=meta.name,
            dataset=dataset
        ).first():
            meta.errors.append(_(f'Duomenų rinkinys "{meta.name}" jau egzistuoja.'))
            loaded_metadata.append(metadata)
        else:
            dataset, metadata = _create_or_update_metadata(dataset, meta, dataset, i)
            _load_prefixes(dataset, meta.prefixes, dataset)
            _load_enums(dataset, meta.enums, dataset)
            _load_params(dataset, meta.params, dataset)
            _load_comments(dataset, meta.comments, dataset)
            loaded_metadata.append(metadata)

        _create_errors(meta.errors, dataset.current_structure)

    removed_metadata = list(set(existing_metadata) - set(loaded_metadata))
    for meta in removed_metadata:
        meta.delete()


def _load_prefixes(
    dataset: Dataset,
    prefixes: Dict[str, struct.Prefix],
    obj: models.Model,
):
    ct = ContentType.objects.get_for_model(obj)
    prefix_ct = ContentType.objects.get_for_model(Prefix)

    existing_prefixes = Prefix.objects.filter(
        content_type=ct,
        object_id=obj.pk
    )
    loaded_prefixes = []

    for i, meta in enumerate(prefixes.values(), 1):
        if prefix := existing_prefixes.filter(
            ~Q(metadata__uuid=meta.id),
            metadata__content_type=prefix_ct,
            name=meta.name,
            metadata__dataset=dataset,
        ).first():
            meta.errors.append(_(f'Prefiksas "{meta.name}" jau egzistuoja.'))
            loaded_prefixes.append(prefix)
        else:
            prefix = Prefix(
                name=meta.name,
                uri=meta.uri,
                content_type=ct,
                object_id=obj.pk
            )
            prefix, metadata = _create_or_update_metadata(dataset, meta, prefix, i)
            loaded_prefixes.append(prefix)

        _create_errors(meta.errors, prefix)

    removed_prefixes = list(set(existing_prefixes) - set(loaded_prefixes))
    for prefix in removed_prefixes:
        prefix.delete()


def _load_enums(
    dataset: Dataset,
    enums: Dict[str, List[struct.Enum]],
    obj: Union[Dataset, Property]
):
    ct = ContentType.objects.get_for_model(obj)
    enum_ct = ContentType.objects.get_for_model(EnumItem)

    existing_enums = Enum.objects.filter(
        content_type=ct,
        object_id=obj.pk,
    )
    loaded_enums = []

    for name, enum_items in enums.items():
        enum, created = Enum.objects.get_or_create(
            name=name,
            content_type=ct,
            object_id=obj.pk
        )
        existing_enum_items = EnumItem.objects.filter(enum=enum)
        loaded_enum_items = []

        for i, meta in enumerate(enum_items, 1):
            if enum_item := existing_enum_items.filter(
                ~Q(metadata__uuid=meta.id),
                metadata__content_type=enum_ct,
                metadata__name=meta.name,
                metadata__prepare=meta.prepare,
                metadata__dataset=dataset,
            ).first():
                meta.errors.append(_(f'Pasirinkimas "{meta.prepare}" jau egzistuoja.'))
                loaded_enum_items.append(enum_item)
            else:
                enum_item = EnumItem(enum=enum)
                enum_item, metadata = _create_or_update_metadata(dataset, meta, enum_item, i)
                loaded_enum_items.append(enum_item)

            _create_errors(meta.errors, enum_item)

        loaded_enums.append(enum)

        removed_enum_items = list(set(existing_enum_items) - set(loaded_enum_items))
        for enum_item in removed_enum_items:
            enum_item.delete()

    removed_enums = list(set(existing_enums) - set(loaded_enums))
    for enum in removed_enums:
        enum.enumitem_set.all().delete()
        enum.delete()


def _load_params(
    dataset: Dataset,
    params: Dict[str, List[struct.Param]],
    obj: Union[Dataset, Model],
):
    ct = ContentType.objects.get_for_model(obj)
    param_ct = ContentType.objects.get_for_model(ParamItem)

    existing_params = Param.objects.filter(
        content_type=ct,
        object_id=obj.pk,
    )
    loaded_params = []

    for name, param_items in params.items():
        param, created = Param.objects.get_or_create(
            name=name,
            content_type=ct,
            object_id=obj.pk
        )
        existing_param_items = ParamItem.objects.filter(param=param)
        loaded_param_items = []

        for i, meta in enumerate(param_items, 1):
            if param_item := existing_param_items.filter(
                ~Q(metadata__uuid=meta.id),
                metadata__content_type=param_ct,
                metadata__name=meta.name,
                metadata__prepare=meta.prepare,
                metadata__dataset=dataset,
            ).first():
                meta.errors.append(_(f'Parametras "{meta.prepare}" jau egzistuoja.'))
                loaded_param_items.append(param_item)
            else:
                param_item = ParamItem(param=param)
                param_item, metadata = _create_or_update_metadata(dataset, meta, param_item, i)
                loaded_param_items.append(param_item)

            _create_errors(meta.errors, param_item)

        loaded_params.append(param)

        removed_param_items = list(set(existing_param_items) - set(loaded_param_items))
        for param_item in removed_param_items:
            param_item.delete()

    removed_params = list(set(existing_params) - set(loaded_params))
    for param in removed_params:
        param.paramitem_set.all().delete()
        param.delete()


def _load_models(
    state: struct.State,
    dataset: Dataset
):
    ct = ContentType.objects.get_for_model(Model)
    existing_models = Model.objects.filter(dataset=dataset)
    loaded_models = []

    for i, meta in enumerate(state.manifest.models.values(), 1):
        if model := existing_models.filter(
            ~Q(metadata__uuid=meta.id),
            metadata__content_type=ct,
            metadata__name=meta.name,
            metadata__dataset=dataset,
        ).first():
            meta.errors.append(_(f'Modelis "{meta.name}" jau egzistuoja.'))
            loaded_models.append(model)
        else:
            model = Model(dataset=dataset)
            model, metadata = _create_or_update_metadata(dataset, meta, model, i)
            _check_uri(dataset, meta, meta.uri)
            _load_comments(dataset, meta.comments, model)
            _load_params(dataset, meta.params, model)
            _load_properties(dataset, meta, model)
            loaded_models.append(model)

        _create_errors(meta.errors, model)

    removed_models = list(set(existing_models) - set(loaded_models))
    for model in removed_models:
        model.delete()


def _load_properties(
    dataset: Dataset,
    model_meta: struct.Model,
    model: Model,
):
    ct = ContentType.objects.get_for_model(Property)
    existing_props = Property.objects.filter(model=model, given=True)
    loaded_props = []

    for i, meta in enumerate(model_meta.properties.values(), 1):
        if prop := existing_props.filter(
            ~Q(metadata__uuid=meta.id),
            metadata__content_type=ct,
            metadata__name=meta.name,
            metadata__dataset=dataset
        ).first():
            meta.errors.append(_(f'Savybė "{meta.name}" jau egzistuoja.'))
            loaded_props.append(prop)
        else:
            prop = Property(model=model)
            prop, metadata = _create_or_update_metadata(dataset, meta, prop, i)
            _check_uri(dataset, meta, metadata.uri)
            _load_comments(dataset, meta.comments, prop)
            _load_enums(dataset, meta.enums, prop)
            loaded_props.append(prop)

        _create_errors(meta.errors, prop)

    removed_props = list(set(existing_props) - set(loaded_props))
    for prop in removed_props:
        prop.delete()


def _load_comments(
    dataset: Dataset,
    comments: List[struct.Comment],
    obj: models.Model
):
    ct = ContentType.objects.get_for_model(obj)
    sys_user, _ = User.objects.get_or_create(email=settings.SYSTEM_USER_EMAIL)

    existing_comments = Comment.objects.filter(
        content_type=ct,
        object_id=obj.pk,
        type=Comment.STRUCTURE
    )
    loaded_comments = []

    for i, meta in enumerate(comments, 1):
        comment = Comment(
            user=sys_user,
            content_type=ct,
            object_id=obj.pk,
            type=Comment.STRUCTURE,
            body=meta.title
        )
        comment, metadata = _create_or_update_metadata(dataset, meta, comment, i)
        loaded_comments.append(comment)

        _create_errors(meta.errors, comment)

    removed_comments = list(set(existing_comments) - set(loaded_comments))
    for comment in removed_comments:
        comment.delete()


def _create_errors(
    errors: List[str],
    obj: models.Model
):
    ct = ContentType.objects.get_for_model(obj)
    sys_user, _ = User.objects.get_or_create(email=settings.SYSTEM_USER_EMAIL)

    Comment.objects.filter(
        content_type=ct,
        object_id=obj.pk,
        type=Comment.STRUCTURE_ERROR
    ).delete()

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
            user=sys_user
        )


def _parse_prepare(prepare: str, meta: struct.Metadata) -> dict:
    if prepare:
        try:
            return spyna.parse(prepare)
        except ParseError as e:
            if hasattr(meta, 'errors'):
                meta.errors.append(_(f'Klaida skaitant formulę "{prepare}"": {e}'))
    return {}


def _create_or_update_metadata(
    dataset: Dataset,
    obj_meta: struct.Metadata,
    obj: models.Model,
    order: int = None,
    use_existing_meta: bool = False
) -> Tuple[models.Model, struct.Metadata]:
    ct = ContentType.objects.get_for_model(obj)

    if use_existing_meta and obj.pk and Metadata.objects.filter(
        object_id=obj.pk,
        content_type=ct,
        dataset=dataset,
    ).exists():
        metadata = Metadata.objects.filter(
            object_id=obj.pk,
            content_type=ct,
            dataset=dataset,
        ).first()
        return metadata.object, metadata

    if obj_meta.id and Metadata.objects.filter(
        uuid=obj_meta.id,
        content_type=ct,
        dataset=dataset,
    ).exists():
        metadata = Metadata.objects.filter(
            uuid=obj_meta.id,
            content_type=ct,
            dataset=dataset
        ).first()

        type_args = ", ".join(obj_meta.type_args) \
            if hasattr(obj_meta, 'type_args') and obj_meta.type_args else None
        access = _parse_access(obj_meta.access)

        if (
            (
                isinstance(metadata.object, Dataset) and
                metadata.name != obj_meta.name
            ) or (
                isinstance(metadata.object, Model) and
                (
                    metadata.name != obj_meta.name or
                    metadata.ref != obj_meta.ref or
                    metadata.level_given != obj_meta.level_given or
                    (metadata.object.base and obj_meta.base and
                     metadata.object.base.model.full_name != obj_meta.base.name) or
                    (not metadata.object.base and obj_meta.base) or
                    (metadata.object.base and not obj_meta.base)
                )
            ) or (
                isinstance(metadata.object, Property) and
                (
                    metadata.name != obj_meta.name or
                    metadata.type != obj_meta.type or
                    metadata.required != obj_meta.required or
                    metadata.unique != obj_meta.unique or
                    metadata.type_args != type_args or
                    metadata.ref != obj_meta.ref or
                    metadata.level_given != obj_meta.level_given or
                    metadata.access != access
                )
            ) or (
                isinstance(metadata.object, EnumItem) and
                (
                    metadata.prepare != obj_meta.prepare or
                    metadata.source != obj_meta.source
                )
            )
        ):
            metadata.draft = True

        metadata.uuid = obj_meta.id
        metadata.name = obj_meta.name if hasattr(obj_meta, 'name') else ''
        metadata.type = obj_meta.type if hasattr(obj_meta, 'type') else ''
        metadata.ref = obj_meta.ref
        metadata.source = obj_meta.source
        metadata.prepare = obj_meta.prepare
        metadata.prepare_ast = _parse_prepare(obj_meta.prepare, obj_meta)
        metadata.level = obj_meta.level
        metadata.level_given = obj_meta.level_given
        metadata.access = access
        metadata.uri = obj_meta.uri
        metadata.version = metadata.version + 1 if metadata.version else 1
        metadata.title = obj_meta.title
        metadata.description = obj_meta.description
        metadata.order = order
        metadata.required = obj_meta.required if hasattr(obj_meta, 'required') else None
        metadata.unique = obj_meta.unique if hasattr(obj_meta, 'unique') else None
        metadata.type_args = type_args
        metadata.save()

        obj = metadata.object
    else:
        if not obj.pk:
            obj.save()
        if not obj_meta.id:
            obj_meta.id = uuid.uuid4()
        metadata = Metadata.objects.create(
            dataset=dataset,
            uuid=obj_meta.id,
            name=obj_meta.name if hasattr(obj_meta, 'name') else '',
            type=obj_meta.type if hasattr(obj_meta, 'type') else '',
            ref=obj_meta.ref,
            source=obj_meta.source,
            prepare=obj_meta.prepare,
            prepare_ast=_parse_prepare(obj_meta.prepare, obj_meta),
            level=obj_meta.level,
            level_given=obj_meta.level_given,
            access=_parse_access(obj_meta.access),
            uri=obj_meta.uri,
            version=1,
            title=obj_meta.title,
            description=obj_meta.description,
            order=order,
            content_type=ct,
            object_id=obj.pk,
            required=obj_meta.required if hasattr(obj_meta, 'required') else None,
            unique=obj_meta.unique if hasattr(obj_meta, 'unique') else None,
            type_args=", ".join(obj_meta.type_args) if hasattr(obj_meta, 'type_args') and obj_meta.type_args else None,
        )
    return obj, metadata


def _link_distributions(
    state: struct.State,
    dataset: Dataset
):
    for dataset_meta in state.manifest.datasets.values():
        if dataset_meta.resources:
            for i, resource_meta in enumerate(dataset_meta.resources.values()):
                if resource_meta.source:
                    distribution = DatasetDistribution.objects.filter(
                        dataset=dataset,
                        download_url=resource_meta.source,
                    ).first()
                    if not distribution:
                        distribution = DatasetDistribution.objects.create(
                            dataset=dataset,
                            download_url=resource_meta.source,
                            title=resource_meta.name,
                            type='URL',
                        )

                    distribution, metadata = _create_or_update_metadata(
                        dataset,
                        resource_meta,
                        distribution,
                        i,
                        use_existing_meta=True
                    )
                    _load_comments(dataset, resource_meta.comments, distribution)
                    for model_meta in resource_meta.models.values():
                        if model := Model.objects.filter(
                            metadata__uuid=model_meta.id,
                            dataset=dataset
                        ).first():
                            model.distribution = distribution
                            model.save()

                    _create_errors(resource_meta.errors, distribution)
        else:
            title = dataset_meta.name.split('/')[-1]
            url = f"https://get.data.gov.lt/{dataset_meta.name}/:ns"
            resource_meta = struct.Resource(
                name=title,
                source=url
            )
            distribution = DatasetDistribution.objects.filter(
                dataset=dataset,
                download_url=url,
            ).first()
            if not distribution:
                format, created = Format.objects.get_or_create(extension='UAPI')
                if created:
                    format.title = 'Saugyklos API'
                    format.mimetype = "application/vnd.api+json"
                    format.save()
                distribution = DatasetDistribution.objects.create(
                    dataset=dataset,
                    download_url=url,
                    format=format,
                    title=title,
                    type='URL',
                )

            distribution, metadata = _create_or_update_metadata(
                dataset,
                resource_meta,
                distribution,
                1,
                use_existing_meta=True
            )
            _load_comments(dataset, resource_meta.comments, distribution)
            for model_meta in dataset_meta.models.values():
                if model := Model.objects.filter(
                        metadata__uuid=model_meta.id,
                        dataset=dataset
                ).first():
                    model.distribution = distribution
                    model.save()

            _create_errors(resource_meta.errors, distribution)


def _link_models(dataset: Dataset, state: struct.State):
    model_ct = ContentType.objects.get_for_model(Model)
    prop_ct = ContentType.objects.get_for_model(Property)

    for model_meta in state.manifest.models.values():
        if model := Model.objects.filter(
            metadata__content_type=model_ct,
            metadata__uuid=model_meta.id,
            dataset=dataset,
        ).first():
            _link_base(dataset, model_meta.base, model)

            if model_meta.ref and model_meta.ref_props:
                for j, prop in enumerate(model_meta.ref_props, 1):
                    if prop := Property.objects.filter(
                        metadata__name=prop,
                        metadata__content_type=prop_ct,
                        model=model,
                    ).first():
                        PropertyList.objects.get_or_create(
                            content_type=model_ct,
                            object_id=model.pk,
                            order=j,
                            property=prop
                        )

            _link_properties(dataset, model, model_meta)
            model.update_level()


def _link_base(
    dataset: Dataset,
    meta: struct.Base,
    model: Model,
):
    base_ct = ContentType.objects.get_for_model(Base)
    model_ct = ContentType.objects.get_for_model(Model)

    if meta:
        if base_model := Model.objects.filter(
            metadata__content_type=model_ct,
            metadata__name=meta.name,
            dataset=dataset,
        ).first():
            if base := Base.objects.filter(
                ~Q(metadata__uuid=meta.id),
                metadata__content_type=base_ct,
                metadata__name=meta.name,
                model=base_model,
            ).first():
                meta.errors.append(_(f'Bazė "{meta.name}" jau egzistuoja.'))
            else:
                base = Base(model=base_model)
                base, metadata = _create_or_update_metadata(dataset, meta, base)
                _load_comments(dataset, meta.comments, base)

                model.base = base
                model.save()

            _create_errors(meta.errors, base)

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
):
    ct = ContentType.objects.get_for_model(Property)
    model_ct = ContentType.objects.get_for_model(Model)

    for prop_meta in model_meta.properties.values():
        if prop := Property.objects.filter(
            metadata__content_type=ct,
            metadata__uuid=prop_meta.id,
            model=model,
        ).first():
            if '.' in prop_meta.name:
                _link_denorm_props(dataset, prop_meta, model, prop)

            if prop_meta.type in ('ref', 'backref', 'generic') and prop_meta.ref:
                if ref_model := Model.objects.filter(
                    metadata__name=prop_meta.ref,
                    metadata__content_type=model_ct,
                    dataset=dataset
                ).first():
                    prop.ref_model = ref_model
                    prop.save()

                    for i, ref_prop in enumerate(prop_meta.ref_props, 1):
                        if ref_prop := Property.objects.filter(
                            metadata__name=ref_prop,
                            metadata__content_type=ct,
                            model=ref_model,
                        ).first():
                            PropertyList.objects.get_or_create(
                                content_type=ct,
                                object_id=prop.pk,
                                property=ref_prop,
                                order=i,
                            )


def _link_denorm_props(
    dataset: Dataset,
    prop_meta: struct.Property,
    model: Model,
    prop: Property,
) -> Property:
    ct = ContentType.objects.get_for_model(Property)

    parent_prop = prop_meta.name.rsplit('.', 1)[0]
    if parent_prop_meta := Metadata.objects.filter(
        content_type=ct,
        name=parent_prop,
        dataset=dataset
    ).first():
        parent_prop = parent_prop_meta.object
    else:
        meta = struct.Property(
            id=str(uuid.uuid4()),
            name=parent_prop,
        )
        parent_prop = Property.objects.create(model=model, given=False)
        _create_or_update_metadata(dataset, meta, parent_prop)
        if '.' in meta.name:
            parent_prop = _link_denorm_props(dataset, meta, model, parent_prop)

    prop.property = parent_prop
    prop.save()
    return prop


def _check_uri(dataset: Dataset, meta: struct.Metadata, uri: str):
    if (
        uri and
        '://' not in uri and
        ':' not in uri
    ):
        if hasattr(meta, 'errors'):
            meta.errors.append(_(f'Neteisingas uri "{uri}" formatas.'))
    elif ':' in uri and '://' not in uri:
        prefix, name = uri.split(':')
        if not Prefix.objects.filter(
            (
                Q(
                    content_type=ContentType.objects.get_for_model(DatasetStructure),
                    object_id=dataset.current_structure.pk
                ) |
                Q(
                    content_type=ContentType.objects.get_for_model(Dataset),
                    object_id=dataset.pk
                )
            ) & Q(name=prefix)
        ):
            if hasattr(meta, 'errors'):
                meta.errors.append(_(f'Prefiksas "{prefix}" duomenų rinkinyje neegzistuoja.'))


def get_data_from_spinta(model: Union[Model, str], uuid: str = None, query: str = ''):
    if uuid:
        url = f"https://get.data.gov.lt/{model}/{uuid}/?{query}"
    else:
        url = f"https://get.data.gov.lt/{model}/?{query}"
    try:
        res = requests.get(url)
    except requests.exceptions.RequestException:
        return {}

    try:
        data = json.loads(res.content)
        return data
    except JSONDecodeError:
        return {}


def _parse_access(value: str):
    access = None
    if value:
        if value == 'private':
            access = Metadata.PRIVATE
        elif value == 'protected':
            access = Metadata.PROTECTED
        elif value == 'public':
            access = Metadata.PUBLIC
        elif value == 'open':
            access = Metadata.OPEN
    return access


def get_model_name(dataset: Dataset, name: str) -> str:
    if name.startswith('/'):
        return name[1:]
    elif not dataset or not dataset.name:
        return name
    else:
        return '/'.join([
            dataset.name,
            name,
        ])


DATASET = [
    'id',
    'dataset',
    'resource',
    'base',
    'model',
    'property',
    'type',
    'ref',
    'source',
    'prepare',
    'level',
    'access',
    'uri',
    'title',
    'description',
]


class IterableFile:

    def __init__(self):
        self.writes = []

    def __iter__(self):
        yield from self.writes
        self.writes = []

    def write(self, data):
        self.writes.append(data)


def export_dataset_structure(dataset: Dataset) -> StringIO:
    cols = DATASET
    rows = datasets_to_tabular(dataset)
    rows = ({c: row[c] for c in cols} for row in rows)

    stream = IterableFile()
    writer = csv.DictWriter(stream, fieldnames=cols)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
        yield from stream


def datasets_to_tabular(dataset: Dataset):
    yield from _prefixes_to_tabular(dataset.current_structure, separator=True)
    yield from _dataset_to_tabular(dataset, separator=True)


def to_row(keys, values) -> Dict:
    return {k: values.get(k) for k in keys}


def _end_marker(name):
    yield to_row(DATASET, {
        name: "/"
    })


def _prefixes_to_tabular(
    obj: models.Model,
    separator: bool = False
):
    ct = ContentType.objects.get_for_model(obj)
    prefixes = Prefix.objects.filter(content_type=ct, object_id=obj.pk).order_by('metadata__order')

    first = True
    for prefix in prefixes:
        if meta := prefix.metadata.first():
            yield to_row(DATASET, {
                'id': meta.uuid,
                'type': 'prefix' if first else '',
                'ref': meta.name,
                'uri': meta.uri,
                'title': meta.title,
                'description': meta.description,
            })
            first = False

    if separator and prefixes:
        yield to_row(DATASET, {})


def _dataset_to_tabular(
    dataset: Dataset,
    separator: bool = False
):
    if meta := dataset.metadata.first():
        yield to_row(DATASET, {
            'id': meta.uuid,
            'dataset': meta.name,
            'level': meta.level_given,
            'access': _get_access(meta.access),
            'title': meta.title,
            'description': meta.description,
        })
    yield from _prefixes_to_tabular(dataset, separator=separator)
    yield from _enums_to_tabular(dataset, separator=separator)
    yield from _params_to_tabular(dataset, separator=separator)
    yield from _models_to_tabular(dataset, separator=separator)


def _enums_to_tabular(
    obj: models.Model,
    separator: bool = False
):
    ct = ContentType.objects.get_for_model(obj)
    enums = Enum.objects.filter(content_type=ct, object_id=obj.pk)

    for enum in enums:
        first = True
        for item in enum.enumitem_set.all().order_by('metadata__order'):
            if meta := item.metadata.first():
                yield to_row(DATASET, {
                    'id': meta.uuid,
                    'type': 'enum' if first else '',
                    'ref': enum.name if first else '',
                    'source': meta.source,
                    'prepare': meta.prepare,
                    'access': _get_access(meta.access),
                    'title': meta.title,
                    'description': meta.description,
                })
                first = False

    if separator and enums:
        yield to_row(DATASET, {})


def _params_to_tabular(
    obj: models.Model,
    separator: bool = False
):
    ct = ContentType.objects.get_for_model(obj)
    params = Param.objects.filter(content_type=ct, object_id=obj.pk)

    for param in params:
        first = True
        for item in param.paramitem_set.all().order_by('metadata__order'):
            if meta := item.metadata.first():
                yield to_row(DATASET, {
                    'id': meta.uuid,
                    'type': 'param' if first else '',
                    'ref': param.name if first else '',
                    'source': meta.source,
                    'prepare': meta.prepare,
                    'access': _get_access(meta.access),
                    'title': meta.title,
                    'description': meta.description,
                })
                first = False

    if separator and params:
        yield to_row(DATASET, {})


def _models_to_tabular(
    dataset: Dataset,
    separator: bool = False
):
    dataset_models = Model.objects.filter(dataset=dataset).order_by('metadata__order')

    resource = None
    base = None
    for model in dataset_models:
        if model.distribution and not resource:
            yield from _resource_to_tabular(model.distribution)
            resource = model.distribution
        elif not model.distribution and resource:
            yield from _end_marker('resource')
            resource = None

        if model.base and not base:
            yield from _base_to_tabular(model.base)
            base = model.base
        elif not model.base and base:
            yield from _end_marker('base')
            base = None

        if meta := model.metadata.first():
            yield to_row(DATASET, {
                'id': meta.uuid,
                'model': _to_relative_model_name(meta.name, dataset),
                'level': meta.level_given,
                'access': _get_access(meta.access),
                'title': meta.title,
                'description': meta.description,
                'uri': meta.uri,
                'source': meta.source,
                'prepare': meta.prepare,
                'ref': ', '.join([
                    prop.property.name
                    for prop in model.property_list.all()]
                ) if model.property_list.exists() else ''
            })

            yield from _comments_to_tabular(model)
            yield from _params_to_tabular(model)
            yield from _properties_to_tabular(model)
            if separator:
                yield to_row(DATASET, {})


def _resource_to_tabular(
    resource: DatasetDistribution
):
    if meta := resource.metadata.first():
        yield to_row(DATASET, {
            'id': meta.uuid,
            'resource': meta.name,
            'source': meta.source,
            'prepare': meta.prepare,
            'type': meta.type,
            'ref': meta.ref,
            'level': meta.level_given,
            'access': _get_access(meta.access),
            'title': meta.title,
            'description': meta.description,
        })
    yield from _comments_to_tabular(resource)


def _comments_to_tabular(obj: models.Model):
    ct = ContentType.objects.get_for_model(obj)
    comments = Comment.objects.filter(
        content_type=ct,
        object_id=obj.pk,
        type=Comment.STRUCTURE
    ).order_by('metadata__order')

    first = True
    for comment in comments:
        if meta := comment.metadata.first():
            yield to_row(DATASET, {
                'id': meta.uuid,
                'type': 'comment' if first else '',
                'ref': meta.ref,
                'source': meta.source,
                'access': _get_access(meta.access),
                'title': meta.title,
                'description': meta.description,
            })
            first = False


def _base_to_tabular(base: Base):
    if meta := base.metadata.first():
        yield to_row(DATASET, {
            'id': meta.uuid,
            'base': _to_relative_model_name(meta.name, meta.dataset),
            'ref': meta.ref
        })


def _properties_to_tabular(model: Model):
    props = model.get_given_props()

    for prop in props:
        if meta := prop.metadata.first():
            yield to_row(DATASET, {
                'id': meta.uuid,
                'property': meta.name,
                'type': get_type_repr(meta),
                'level': meta.level_given,
                'access': _get_access(meta.access),
                'uri': meta.uri,
                'title': meta.title,
                'description': meta.description,
                'source': meta.source,
                'prepare': meta.prepare,
                'ref': _prop_ref_to_tabular(prop, meta)
            })

            yield from _comments_to_tabular(prop)
            yield from _enums_to_tabular(prop)


def _to_relative_model_name(name: str, dataset: Dataset) -> str:
    if (
        dataset.name and
        name.startswith(dataset.name)
    ):
        prefix = dataset.name
        return name[len(prefix) + 1:]
    else:
        return name


def _get_access(acess: int) -> str:
    if acess == Metadata.PRIVATE:
        return 'private'
    elif acess == Metadata.PROTECTED:
        return 'protected'
    elif acess == Metadata.PUBLIC:
        return 'public'
    elif acess == Metadata.OPEN:
        return 'open'
    return ''


def _prop_ref_to_tabular(prop: Property, meta: Metadata) -> str:
    ref = meta.ref
    if meta.type == 'ref':
        ref_model = _to_relative_model_name(meta.ref, meta.dataset)
        ref_props = prop.property_list.values_list('property__metadata__name', flat=True)
        if ref_props:
            ref_props = ', '.join(ref_props)
            ref = f"{ref_model}[{ref_props}]"
        else:
            ref = ref_model
    return ref


def get_srid(type_args):
    srid = None
    if type_args:
        type_args = type_args.split(',')
        type_args = [arg.strip() for arg in type_args]
        if len(type_args) == 1 and type_args[0].isdigit():
            srid = int(type_args[0])
        elif len(type_args) == 2 and type_args[1].isdigit():
            srid = int(type_args[1])
    return srid


def transform_coordinates(point_x, point_y, source_srid, target_srid):
    transformer = Transformer.from_crs(
        f"EPSG:{source_srid}",
        f"EPSG:{target_srid}"
    )
    return transformer.transform(point_x, point_y)


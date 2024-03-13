from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any, Iterable, NamedTuple, TypedDict, Tuple, List
from django.utils.translation import gettext_lazy as _

DIMS = [
    'dataset',
    'resource',
    'base',
    'model',
    'property',
]

XDIMS = [
    'comment',
    'prefix',
    'enum',
    'param',
    'lang',
]

ATTRS = [
    'id',
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

HEADER = [
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


class Rule(NamedTuple):
    parents: list[str]
    accepts: list[str]


RULES = {
    'manifest': Rule(
        parents=[],
        accepts=[
            'comment',
        ],
    ),
    'dataset': Rule(
        parents=[
            'manifest',
        ],
        accepts=[
            'comment',
            'prefix',
            'enum',
            'lang',
        ],
    ),
    'resource': Rule(
        parents=[
            'dataset',
        ],
        accepts=[
            'comment',
            'param',
            'lang',
        ],
    ),
    'base': Rule(
        parents=[
            'dataset',
            'resource',
        ],
        accepts=[
            'comment',
            'param',
            'lang',
        ],
    ),
    'model': Rule(
        parents=[
            'dataset',
            'resource',
            'base',
        ],
        accepts=[
            'comment',
            'param',
            'lang',
        ],
    ),
    'property': Rule(
        parents=[
            'model',
        ],
        accepts=[
            'comment',
            'param',
            'lang',
            'enum',
        ],
    ),
    'comment': Rule(
        parents=[
            'dataset',
            'resource',
            'base',
            'model',
            'property',
            'enum',
            'prefix',
            'lang',
        ],
        accepts=[],
    ),
    'prefix': Rule(
        parents=[
            'dataset',
        ],
        accepts=[
            'coment',
            'lang',
        ],
    ),
    'enum': Rule(
        parents=[
            'dataset',
            'property',
        ],
        accepts=[
            'coment',
        ],
    ),
    'param': Rule(
        parents=[
            'resource',
            'model',
            'property',
        ],
        accepts=[
            'coment',
        ],
    ),
    'lang': Rule(
        parents=[
            'dataset',
            'resource',
            'base',
            'model',
            'property',
            'enum',
            'prefix',
        ],
        accepts=[
            'coment',
        ],
    ),
}


class Row(TypedDict):
    id: str
    dataset: str
    resource: str
    base: str
    model: str
    property: str
    type: str
    ref: str
    source: str
    prepare: str
    level: str
    access: str
    uri: str
    title: str
    description: str


@dataclass
class Manifest:
    dim: str = field(default='manifest')

    datasets: dict[str, Dataset] = field(default_factory=dict, init=False)
    models: dict[str, Model] = field(default_factory=dict, init=False)
    comments: list[Comment] = field(default_factory=list, init=False)
    prefixes: dict[str, Prefix] = field(default_factory=dict, init=False)
    errors: list[str] = field(default_factory=list, init=False)


@dataclass
class Metadata:
    id: str = ''
    ref: str = ''
    source: str = ''
    prepare: str = ''
    level: int | None = None
    level_given: int | None = None
    access: str = ''
    uri: str = ''
    title: str = ''
    description: str = ''


@dataclass
class Dataset(Metadata):
    dim: str = field(default='dataset')

    name: str = ''
    type: str = ''

    resources: dict[str, Resource] = field(default_factory=dict, init=False)
    models: dict[str, Model] = field(default_factory=dict, init=False)
    comments: list[Comment] = field(default_factory=list, init=False)
    prefixes: dict[str, Prefix] = field(default_factory=dict, init=False)
    enums: dict[str, list[Enum]] = field(default_factory=dict, init=False)
    params: dict[str, list[Param]] = field(default_factory=dict, init=False)
    errors: list[str] = field(default_factory=list, init=False)


@dataclass
class Resource(Metadata):
    dim: str = field(default='resource')

    name: str = ''
    type: str = ''

    dataset: Dataset = field(init=False)
    comments: list[Comment] = field(default_factory=list, init=False)
    models: dict[str, Model] = field(default_factory=dict, init=False)
    errors: list[str] = field(default_factory=list, init=False)


@dataclass
class Base(Metadata):
    dim: str = field(default='base')

    name: str = ''
    type: str = ''

    comments: list[Comment] = field(default_factory=list, init=False)
    errors: list[str] = field(default_factory=list, init=False)


@dataclass
class Model(Metadata):
    dim: str = field(default='model')

    name: str = ''
    type: str = ''

    dataset: Dataset | None = field(default=None, init=False)
    properties: dict[str, Property] = field(default_factory=dict, init=False)
    comments: list[Comment] = field(default_factory=list, init=False)
    base: Base | None = field(default=None, init=False)
    resource: Resource | None = field(default=None, init=False)
    ref_props: list[str] = field(default_factory=list, init=False)
    params: dict[str, list[Param]] = field(default_factory=dict, init=False)
    errors: list[str] = field(default_factory=list, init=False)

    @property
    def absname(self):
        if self.dataset:
            return f'{self.dataset.name}/{self.name}'
        return self.name


@dataclass
class Property(Metadata):
    dim: str = field(default='property')

    name: str = ''
    type: str = ''
    required: bool = False
    unique: bool = False
    type_args: list[str] = None

    model: Model = field(init=False)
    comments: list[Comment] = field(default_factory=list, init=False)
    enums: dict[str, list[Enum]] = field(default_factory=dict, init=False)
    ref_props: list[str] = field(default_factory=list, init=False)
    errors: list[str] = field(default_factory=list, init=False)


@dataclass
class Comment(Metadata):
    dim: str = field(default='comment')

    meta: Metadata = field(init=False)
    errors: list[str] = field(default_factory=list, init=False)


@dataclass
class Prefix(Metadata):
    dim: str = field(default='prefix')

    name: str = ''

    meta: Metadata = field(init=False)
    errors: list[str] = field(default_factory=list, init=False)


@dataclass
class Enum(Metadata):
    dim: str = field(default='enum')

    name: str = ''

    meta: Metadata = field(init=False)
    errors: list[str] = field(default_factory=list, init=False)
    comments: list[Comment] = field(default_factory=list, init=False)


@dataclass
class Param(Metadata):
    dim: str = field(default='param')

    name: str = ''

    meta: Metadata = field(init=False)
    errors: list[str] = field(default_factory=list, init=False)


class State:
    manifest: Manifest | None = None
    dataset: Dataset | None = None
    resource: Resource | None = None
    base: Base | None = None
    model: Model | None = None
    prop: Property | None = None
    enum: Enum | None = None
    comment: Comment | None = None
    prefix: Comment | None = None
    param: Param | None = None

    stack: list[Metadata]
    errors: list[str]

    def __init__(self):
        self.stack = []
        self.errors = []

    def push(self, metadata: Metadata) -> None:
        self.stack.append(metadata)

    def clean(self, dim: str) -> None:
        for meta in list(reversed(self.stack)):
            if precedes(dim, meta.dim):
                self.stack.pop()

    def error(self, message: str) -> None:
        self.errors.append(message)

    @property
    def last(self):
        return self.stack[-1]


def precedes(a: str, b: str) -> bool:
    if a == b:
        return True

    if a in DIMS and b in DIMS:
        return DIMS.index(a) < DIMS.index(b)

    if a in DIMS:
        return True

    if b in DIMS:
        return False

    if a in RULES[b].parents:
        return True

    return False


def detect_read_errors(path: str) -> list[str]:
    path = pathlib.Path(path)
    if not path.exists():
        return ["File does not exist."]

    with path.open('rb') as f:
        sample = f.readline(200).rstrip(b"\r\n")

        if error := _detect_separator_errors(sample):
            return [error]

        sample = sample.decode('utf-8', errors='replace')
        errors = []
        for name in sample.split(','):
            if error := _detect_header_errors(name):
                errors.append(error)
        if errors:
            return errors

    return []


def _detect_separator_errors(sample: bytes) -> str | None:
    if b',' in sample:
        return

    if b';' in sample:
        return (
            "Incorrect value separator. Must be ',', but ';' "
            "is given."
        )

    elif b'\t' in sample:
        return (
            "Incorrect value separator. Must be ',', but 'TAB' "
            "is given."
        )

    else:
        header = ','.join(HEADER)
        return f"Unrecognized CSV file header. Header must be: {header}."


def _detect_header_errors(name: str) -> str | None:
    if name in HEADER:
        return

    elif name.lower() in HEADER:
        return (
            "Header names bus be given in lower case. Expected "
            f"{name.lower()!r}, received {name!r}."
        )

    elif name.strip() in HEADER:
        return (
            "Header names must not have spaces. Expected "
            f"{name.strip()!r}, received {name!r}."
        )

    elif name.strip().lower() in HEADER:
        return (
            "Header names must not have spaces and must be in lower "
            f"case. Expected {name.strip().lower()!r}, received {name!r}."
        )

    else:
        return (
            f"Unrecognized header name {name!r}."
        )


def read(reader: Iterable[Row]) -> State:
    state = State()
    state.manifest = Manifest()
    state.push(state.manifest)

    for row in reader:
        upper, dim, lower = _split_dim(DIMS, row)

        # Main dimension
        if dim:
            name = row[dim]

        # Extra dimension
        else:
            if row['type']:
                dim = row['type']
            elif any(row.values()):
                dim = state.last.dim
            else:
                continue  # empty row

            if row['ref']:
                name = row['ref']
            elif (
                (dim == 'enum' and isinstance(state.last, Enum)) or
                (dim == 'param' and isinstance(state.last, Param))
            ):
                name = state.last.name
            else:
                name = ''

        # Clean stack of lower precedence metadata
        state.clean(dim)

        # Read metadata
        meta = None
        if dim == 'dataset':
            meta = _read_dataset(state, row, name)

        elif dim == 'resource':
            meta = _read_resource(state, row, name)

        elif dim == 'base':
            meta = _read_base(state, row, name)

        elif dim == 'model':
            meta = _read_model(state, row, name)

        elif dim == 'property':
            meta = _read_property(state, row, name)

        elif dim == 'comment':
            meta = _read_comment(state, row, name)

        elif dim == 'prefix':
            meta = _read_prefix(state, row, name)

        elif dim == 'enum':
            meta = _read_enum(state, row, name)

        elif dim == 'param':
            meta = _read_param(state, row, name)

        # Push read metadata to stack
        if meta:
            state.push(meta)

    return state


def _read_dataset(
    state: State,
    row: Row,
    name: str,
) -> Dataset:
    if name == '/':
        dataset = state.dataset = None
    else:
        dataset = state.dataset = Dataset(
            id=row['id'],
            name=name,
            type=row['type'],
            ref=row['ref'],
            source=row['source'],
            prepare=row['prepare'],
            level=_parse_int(row['level']),
            level_given=_parse_int(row['level']),
            access=row['access'],
            uri=row['uri'],
            title=row['title'],
            description=row['description'],
        )
        state.manifest.datasets[name] = dataset
    return dataset


def _read_resource(
    state: State,
    row: Row,
    name: str,
) -> Resource:
    if name == '/':
        resource = state.resource = None
    else:
        resource = state.resource = Resource(
            id=row['id'],
            name=name,
            type=row['type'],
            ref=row['ref'],
            source=row['source'],
            prepare=row['prepare'],
            level=_parse_int(row['level']),
            level_given=_parse_int(row['level']),
            access=row['access'],
            uri=row['uri'],
            title=row['title'],
            description=row['description'],
        )

        _validate_resource_name(name, resource)

        resource.dataset = state.dataset
        resource.dataset.resources[name] = resource

    return resource


def _read_base(
    state: State,
    row: Row,
    name: str,
) -> Base:
    if name == '/':
        base = state.base = None
    else:
        name = get_relative_model_name(state.dataset, name)
        base = state.base = Base(
            id=row['id'],
            name=name,
            type=row['type'],
            ref=row['ref'],
            source=row['source'],
            prepare=row['prepare'],
            level=_parse_int(_get_level(row)),
            level_given=_parse_int(row['level']),
            access=row['access'],
            uri=row['uri'],
            title=row['title'],
            description=row['description'],
        )
    return base


def _read_model(
    state: State,
    row: Row,
    name: str,
) -> Model:
    name = get_relative_model_name(state.dataset, name)
    model = state.model = Model(
        id=row['id'],
        name=name,
        type=row['type'],
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(_get_level(row)),
        level_given=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    _validate_model_name(name, model)

    if model.ref:
        model.ref_props = [x.strip() for x in model.ref.split(',')]

    if state.manifest.models.get(model.name):
        model.errors.append(_(f'Modelis "{model.name}" jau egzistuoja.'))

    if state.dataset:
        model.dataset = state.dataset
        model.dataset.models[name] = model

    if state.base:
        model.base = state.base

    if state.resource:
        model.resource = state.resource
        model.resource.models[name] = model

    state.manifest.models[model.name] = model

    return model


def _parse_property_ref(ref: str) -> Tuple[str, List[str]]:
    if '[' in ref:
        ref = ref.rstrip(']')
        ref_model, ref_props = ref.split('[', 1)
        ref_props = [p.strip() for p in ref_props.split(',')]
    else:
        ref_model = ref
        ref_props = []
    return ref_model, ref_props


def _read_property(
    state: State,
    row: Row,
    name: str,
) -> Property:
    dtype = _parse_dtype_string(row['type'])

    prop = state.prop = Property(
        id=row['id'],
        name=name,
        type=dtype['type'],
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(_get_level(row)),
        level_given=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
        required=dtype['required'],
        unique=dtype['unique'],
        type_args=dtype['type_args'],
    )

    if dtype['error']:
        prop.errors.append(dtype['error'])

    _validate_property_name(name, prop)

    if prop.ref and prop.type in ('ref', 'backref', 'generic'):
        ref_model, ref_props = _parse_property_ref(prop.ref)
        prop.ref = get_relative_model_name(state.dataset, ref_model)
        prop.ref_props = ref_props

    prop.model = state.model

    if prop.model.properties.get(name):
        prop.errors.append(_(f'Savybė "{name}" jau egzistuoja.'))

    prop.model.properties[name] = prop

    return prop


def _read_comment(
    state: State,
    row: Row,
    name: str,
) -> Comment:
    comment = state.comment = Comment(
        id=row['id'],
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
        level_given=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    comment.meta = state.last
    if hasattr(comment.meta, 'comments'):
        comment.meta.comments.append(comment)

    return comment


def _read_prefix(
    state: State,
    row: Row,
    name: str,
) -> Prefix:
    prefix = state.prefix = Prefix(
        id=row['id'],
        name=name,
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
        level_given=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    prefix.meta = state.dataset or state.manifest

    if prefix.meta:
        if prefix.meta.prefixes.get(name):
            prefix.errors.append(_(f'Prefiksas "{name}" jau egzistuoja.'))

        prefix.meta.prefixes[name] = prefix

    return prefix


def _read_enum(
    state: State,
    row: Row,
    name: str,
) -> Enum:
    enum = state.enum = Enum(
        id=row['id'],
        name=name,
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
        level_given=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    last = None
    for node in state.stack:
        if isinstance(node, Dataset) or isinstance(node, Property):
            last = node

    enum.meta = last
    if enum.meta.enums.get(name):
        if enum.prepare in [e.prepare for e in enum.meta.enums[name]]:
            enum.errors.append(_(f'Galima reikšmė "{enum.prepare}" jau egzistuoja.'))

        enum.meta.enums[name].append(enum)
    else:
        enum.meta.enums[name] = [enum]

    return enum


def _read_param(
    state: State,
    row: Row,
    name: str,
) -> Param:
    param = Param(
        id=row['id'],
        name=name,
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
        level_given=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    last = None
    for node in state.stack:
        if isinstance(node, Dataset) or isinstance(node, Model):
            last = node

    _validate_name(name, param)

    param.meta = last
    if param.meta.params.get(name):
        if param.prepare in [e.prepare for e in param.meta.params[name]]:
            param.errors.append(_(f'Parametras "{param.prepare}" jau egzistuoja.'))

        param.meta.params[name].append(param)
    else:
        param.meta.params[name] = [param]

    return param


def _split_dim(
    dims: list[str],
    row: dict[str, Any],
) -> tuple[
    list[str],  # upper
    str,        # found
    list[str],  # lower
]:
    upper = []
    lower = []
    found = None
    for dim in dims:
        if row[dim]:
            found = dim
        elif found:
            lower.append(dim)
        else:
            upper.append(dim)
    return upper, found, lower


def _parse_int(v: str) -> int | None:
    return int(v) if v else None


def get_relative_model_name(dataset: Dataset, name: str) -> str:
    if name.startswith('/'):
        return name[1:]
    elif dataset is None:
        return name
    else:
        return '/'.join([
            dataset.name,
            name,
        ])


def _get_level(row: Row) -> str:
    if row['level']:
        return row['level']

    level = '3'
    if row['ref'] and row['uri']:
        level = '5'
    elif row['ref']:
        level = '4'
    return level


def _parse_dtype_string(dtype: str) -> dict:
    args = []
    error = None
    required = unique = False
    invalid_args = []

    if '(' in dtype:
        dtype, args = dtype.split('(', 1)
        args, additional_args = args.split(')', 1)
        args = args.strip().rstrip(')')
        args = [a.strip() for a in args.split(',')]
    else:
        if len(dtype.split(None, 1)) > 1:
            dtype, additional_args = dtype.split(None, 1)
        else:
            additional_args = ""

    if additional_args:
        for arg in additional_args.split(None):
            if arg == 'required':
                required = True
            elif arg == 'unique':
                unique = True
            else:
                invalid_args.append(arg)
        if invalid_args:
            error = f'Invalid type arguments: {", ".join(invalid_args)}.'

    return {
        'type': dtype,
        'type_args': args,
        'required': required,
        'unique': unique,
        'error': error,
    }


def _validate_name(name: str, meta: Metadata):
    if name:
        if not name.isascii() and hasattr(meta, 'errors'):
            meta.errors.append(_(f'"{name}" kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės.'))


def _validate_model_name(name: str, meta: Model):
    if name:
        name = name.split('/')[-1]
        _validate_name(name, meta)
        if not name[0].isupper():
            meta.errors.append(_(f'Pirmas modelio kodinio pavadinimo simbolis turi būti didžioji raidė: "{name}".'))
        elif any(not c.isalnum() for c in name):
            meta.errors.append(_(f'Modelio kodiniame pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, '
                                 f'jokie kiti simboliai negalimi: "{name}".'))


def _validate_property_name(name: str, meta: Property):
    if name:
        _validate_name(name, meta)
        if not name[0].islower():
            meta.errors.append(_(f'Pirmas kodinio pavadinimo simbolis turi būti mažoji raidė: "{name}".'))
        elif any([ch.isupper() for ch in name]):
            meta.errors.append(_(f'Kodiniame pavadinime negali būti naudojamos didžiosios raidės: "{name}".'))
        elif any((not ch.isalnum() and ch != '_' and ch != '.') for ch in name):
            meta.errors.append(_(f'Pavadinime gali būti mažosios raidės ir skaičiai, ' 
                                 f'žodžiai gali būti atskirti _ simboliu, arba . simboliu, '
                                 f'jei tai denormalizuotas laukas, jokie kiti simboliai negalimi: "{name}".'))


def _validate_resource_name(name: str, meta: Model):
    if name:
        name = name.split('/')[-1]
        _validate_name(name, meta)
        if any([ch.isupper() for ch in name]):
            meta.errors.append(_(f'Kodiniame pavadinime negali būti naudojamos didžiosios raidės: "{name}".'))

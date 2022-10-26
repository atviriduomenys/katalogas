from __future__ import annotations

import pathlib
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Iterable
from typing import NamedTuple
from typing import TypedDict


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


@dataclass
class Metadata:
    id: str = ''
    ref: str = ''
    source: str = ''
    prepare: str = ''
    level: int | None = None
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


@dataclass
class Resource(Metadata):
    dim: str = field(default='resource')

    name: str = ''
    type: str = ''

    dataset: Dataset = field(init=False)
    comments: list[Comment] = field(default_factory=list, init=False)


@dataclass
class Base(Metadata):
    dim: str = field(default='base')

    name: str = ''
    type: str = ''

    comments: list[Comment] = field(default_factory=list, init=False)


@dataclass
class Model(Metadata):
    dim: str = field(default='model')

    name: str = ''
    type: str = ''

    dataset: Dataset | None = field(default=None, init=False)
    properties: dict[str, Property] = field(default_factory=dict, init=False)
    comments: list[Comment] = field(default_factory=list, init=False)

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

    model: Model = field(init=False)
    comments: list[Comment] = field(default_factory=list, init=False)


@dataclass
class Comment(Metadata):
    dim: str = field(default='comment')

    meta: Metadata = field(init=False)


@dataclass
class Prefix(Metadata):
    dim: str = field(default='prefix')

    name: str = ''

    meta: Metadata = field(init=False)


class State:
    dataset: Dataset | None = None
    resource: Resource | None = None
    base: Base | None = None
    model: Model | None = None
    prop: Property | None = None

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
        sample = f.readline(200).rstrip()

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
            else:
                name = ''

        # Clean stack of lower precedence metadata
        state.clean(dim)

        # Read metadata
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

        # Push read metadata to stack
        state.push(meta)

    return state


def _read_dataset(
    state: State,
    row: Row,
    name: str,
) -> None:
    dataset = state.dataset = Dataset(
        id=row['id'],
        name=name,
        type=row['type'],
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
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
) -> None:
    resource = state.resource = Resource(
        id=row['id'],
        name=name,
        type=row['type'],
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    resource.dataset = state.dataset
    resource.dataset.resources[name] = resource

    return resource


def _read_base(
    state: State,
    row: Row,
    name: str,
) -> None:
    base = state.base = Base(
        id=row['id'],
        name=name,
        type=row['type'],
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
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
) -> None:
    model = state.model = Model(
        id=row['id'],
        name=name,
        type=row['type'],
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    if state.dataset:
        model.dataset = state.dataset
        model.dataset.models[name] = model

    state.manifest.models[model.absname] = model

    return model


def _read_property(
    state: State,
    row: Row,
    name: str,
) -> None:
    prop = state.prop = Model(
        id=row['id'],
        name=name,
        type=row['type'],
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    prop.model = state.model
    prop.model.properties[name] = prop

    return prop


def _read_comment(
    state: State,
    row: Row,
    name: str,
) -> None:
    comment = Comment(
        id=row['id'],
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    comment.meta = state.last
    comment.meta.comments.append(comment)

    return comment


def _read_prefix(
    state: State,
    row: Row,
    name: str,
) -> None:
    prefix = Prefix(
        id=row['id'],
        name=name,
        ref=row['ref'],
        source=row['source'],
        prepare=row['prepare'],
        level=_parse_int(row['level']),
        access=row['access'],
        uri=row['uri'],
        title=row['title'],
        description=row['description'],
    )

    prefix.meta = state.last
    prefix.meta.prefixes[name] = prefix

    return prefix




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
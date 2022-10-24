import csv
import io
import pathlib

import pytest

from vitrina.datasets.factories import MANIFEST
from vitrina.datasets.structure import detect_read_errors
from vitrina.datasets.structure import precedes
from vitrina.datasets.structure import read


@pytest.mark.parametrize('content, errors_expected', [
    (b'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description', False),
    (b'id ,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description', True),
    (b'id,DATASET,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description', True),
    (b'id,DATASET ,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description', True),
    (b'id,datast,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description', True),
    (b'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description;;;', True),
    (b'', True),
    (bytes.fromhex('00010203ff'), True),
])
def test_detect_read_errors(
    content: bytes,
    errors_expected: bool,
    tmp_path: pathlib.Path,
):
    path = tmp_path / 'manifest.csv'
    path.write_bytes(content)
    if errors_expected:
        assert detect_read_errors(path) != []
    else:
        assert detect_read_errors(path) == []


@pytest.mark.parametrize('a, b, res', [
    ('manifest', 'manifest', True),
    ('comment', 'manifest', False),
    ('model', 'dataset', False),
    ('dataset', 'comment', True),
    ('property', 'comment', True),
    ('comment', 'enum', False),
    ('enum', 'comment', True),
])
def test_precedence(a: str, b: str, res: bool):
    assert precedes(a, b) is res


def test_read_stcuture_table():
    f = io.StringIO(MANIFEST)
    reader = csv.DictReader(f)
    state = read(reader)
    assert state.errors == []

    manifest = state.manifest
    dataset = 'datasets/gov/ivpk/adk'
    model = f'{dataset}/Dataset'

    assert list(manifest.datasets) == [dataset]
    assert list(manifest.models) == [
        f'{dataset}/Dataset',
        f'{dataset}/Licence',
    ]

    assert list(manifest.datasets[dataset].prefixes) == [
        'dcat',
        'dct',
        'spinta',
    ]

    props = manifest.models[model].properties
    assert list(props) == [
        'id',
        'title',
        'description',
        'licence',
    ]

    assert props['id'].type == 'integer'
    assert len(props['description'].comments) == 1

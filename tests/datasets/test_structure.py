import csv
import io
import pathlib

import pytest

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
    f = io.StringIO('\n'.join([
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description',
        ',datasets/gov/ivpk/adp/catalog,,,,,,,,,,,,,',
        ',,,,,,prefix,dc,,,,,http://purl.org/dc/elements/1.1/,,',
        ',,,,,,,dcat,,,,,http://www.w3.org/ns/dcat#,,',
        ',,,,,,,dct,,,,,http://purl.org/dc/terms/,,',
        ',,,,,,,,,,,,,,',
        ',,,,,,enum,Status,,\'INVENTORED\',,,,Atlikta inventorizacija,',
        ',,,,,,,,,\'PRIORITIZED\',,,,Numatitas prioritetas,',
        ',,,,,,,,,,,,,,',
        ',,,,Category,,,,,,,,,Kategorija,',
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,',
        ',,,,,created,datetime,U,,,5,open,dct:created,Kada sukurta,',
        ',,,,,version,integer,,,,4,open,,Keitimo versija,',
        ',,,,,description,string,,,,2,open,skos:definition,Aprašymas,',
        ',,,,,,comment,type,Mantas,,,open,,2022-04-21 00:00:00,',
    ]))
    reader = csv.DictReader(f)
    state = read(reader)
    assert state.errors == []

    manifest = state.manifest
    dataset = 'datasets/gov/ivpk/adp/catalog'
    model = f'{dataset}/Category'

    assert list(manifest.datasets) == [dataset]
    assert list(manifest.models) == [model]

    assert list(manifest.datasets[dataset].prefixes) == [
        'dc',
        'dcat',
        'dct',
    ]

    props = manifest.models[model].properties
    assert list(props) == [
        'id',
        'created',
        'version',
        'description',
    ]

    assert props['id'].type == 'integer'
    assert len(props['description'].comments) == 1

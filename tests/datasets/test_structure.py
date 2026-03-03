import csv
import io
import pathlib

import pytest

from vitrina.datasets.factories import MANIFEST
from vitrina.datasets.structure import (
    detect_read_errors,
    _update_model_visibility_from_property,
    _update_parent_visibility_from_enum,
    State,
    Property,
    Model,
    Enum,
)
from vitrina.datasets.structure import precedes
from vitrina.datasets.structure import read


@pytest.mark.parametrize(
    "content, errors_expected",
    [
        (b"id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description", False),
        (b"id ,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description", True),
        (b"id,DATASET,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description", True),
        (b"id,DATASET ,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description", True),
        (b"id,datast,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description", True),
        (
            b"id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description;;;",
            True,
        ),
        (b"", True),
        (bytes.fromhex("00010203ff"), True),
    ],
)
def test_detect_read_errors(
    content: bytes,
    errors_expected: bool,
    tmp_path: pathlib.Path,
):
    path = tmp_path / "manifest.csv"
    path.write_bytes(content)
    if errors_expected:
        assert detect_read_errors(path) != []
    else:
        assert detect_read_errors(path) == []


@pytest.mark.parametrize(
    "a, b, res",
    [
        ("manifest", "manifest", True),
        ("comment", "manifest", False),
        ("model", "dataset", False),
        ("dataset", "comment", True),
        ("property", "comment", True),
        ("comment", "enum", False),
        ("enum", "comment", True),
    ],
)
def test_precedence(a: str, b: str, res: bool):
    assert precedes(a, b) is res


def test_read_structure_table():
    f = io.StringIO(MANIFEST)
    reader = csv.DictReader(f)
    state = read(reader)
    assert state.errors == []

    manifest = state.manifest
    dataset = "datasets/gov/ivpk/adk"
    model = f"{dataset}/Dataset"

    assert list(manifest.datasets) == [dataset]
    assert list(manifest.models) == [
        f"{dataset}/Dataset",
        f"{dataset}/Licence",
    ]

    assert list(manifest.datasets[dataset].prefixes) == [
        "dcat",
        "dct",
        "spinta",
    ]

    props = manifest.models[model].properties
    assert list(props) == [
        "id",
        "title",
        "description",
        "licence",
    ]

    assert props["id"].type == "integer"
    assert len(props["description"].comments) == 1


def test_read_structure_table_not_mandatory_columns():
    manifest_without_columns = """\
id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description
,datasets/gov/ivpk/adk,,,,,,,,,,,,Opend Data Portal,
,,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,
,,,,,,,dct,,,,,http://purl.org/dc/terms/,,
,,,,,,,spinta,,,,,https://github.com/atviriduomenys/spinta/issues/,,
,,,,,,,,,,,,,,
,,,,Dataset,,,id,,,5,,dcat:Dataset,Dataset,
,,,,,id,integer,,,,5,open,dct:identifier,,
,,,,,title,string,,,,2,open,dct:title,,
,,,,,,comment,type,,"update(property: ""title@lt"", type: ""text"")",4,open,spinta:204,2022-10-23 11:00,
,,,,,description,string,,,,2,open,dct:description,,
,,,,,,comment,type,,"update(property: ""description@lt"", type: ""text"")",4,open,spinta:204,2022-10-23 11:00,
,,,,,licence,ref,Licence,,,2,open,dct:license,,
,,,,,,,,,,,,,,
,,,,Licence,,,id,,,,,,Licence,
,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,
,,,,,title,string,,,,2,open,dct:title,,
,,,,,,comment,type,,"update(property: ""title@lt"", type: ""text"")",4,open,spinta:204,2022-10-23 11:00,
"""

    f = io.StringIO(manifest_without_columns)
    reader = csv.DictReader(f)
    state = read(reader)
    assert state.errors == []
    manifest = state.manifest
    dataset = "datasets/gov/ivpk/adk"
    model = f"{dataset}/Dataset"

    assert list(manifest.datasets) == [dataset]
    assert list(manifest.models) == [
        f"{dataset}/Dataset",
        f"{dataset}/Licence",
    ]

    assert list(manifest.datasets[dataset].prefixes) == [
        "dcat",
        "dct",
        "spinta",
    ]

    props = manifest.models[model].properties
    assert list(props) == [
        "id",
        "title",
        "description",
        "licence",
    ]

    assert props["id"].type == "integer"
    assert len(props["description"].comments) == 1


@pytest.mark.parametrize(
    "model_visibility, property_visibility, expected",
    [
        ("private", "public", "public"),
        ("private", "protected", "protected"),
        ("private", "package", "package"),
        ("public", "private", "public"),
        ("protected", "protected", "protected"),
    ],
)
def test_update_model_visibility_from_property(model_visibility, property_visibility, expected):
    model = Model(visibility=model_visibility)
    property = Property(visibility=property_visibility)
    property.model = model

    _update_model_visibility_from_property(property)

    assert model.visibility == expected


@pytest.mark.parametrize(
    "model_visibility, property_visibility, enum_visibility, expected_model, expected_property",
    [
        ("private", "private", "public", "public", "public"),
        ("private", "private", "protected", "protected", "protected"),
        ("public", "public", "private", "public", "public"),
        ("public", "private", "protected", "public", "protected"),
        ("private", "public", "protected", "protected", "public"),
    ],
)
def test_update_parent_visibility_from_enum(
    model_visibility, property_visibility, enum_visibility, expected_model_visibility, expected_property_visibility
):
    model = Model(visibility=model_visibility)
    property = Property(visibility=property_visibility)
    property.model = model
    enum = Enum(visibility=enum_visibility)
    enum.meta = property
    state = State()
    state.model = model

    _update_parent_visibility_from_enum(state, enum)

    assert model.visibility == expected_model_visibility
    assert property.visibility == expected_property_visibility

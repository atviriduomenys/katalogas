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
    "model_visibility, property_visibility, enum_visibility, expected_model_visibility, expected_property_visibility",
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


def test_import_property_enum_type_string():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n"
        ",example,,,,,,,,,,,,,\n"
        ",,,,Dataset,,,id,,,,,,,\n"
        ",,,,,id,integer,,,,,,,,\n"
        ",,,,,str_enum,string,,STR_ENUM,,,,,,\n"
        ',,,,,,enum,,one,"""One""",,,,,\n'
        ',,,,,,,,two,"""Two""",,,,,\n'
    )
    reader = csv.DictReader(io.StringIO(manifest))
    model = "example/Dataset"

    state = read(reader)
    assert state.errors == []

    property = state.manifest.models[model].properties["str_enum"]
    assert property.type == "string"
    enum_item_1, enum_item_2 = property.enums[""]
    assert enum_item_1.source == "one"
    assert enum_item_1.prepare == '"One"'
    assert enum_item_2.source == "two"
    assert enum_item_2.prepare == '"Two"'


def test_import_property_enum_type_integer():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n"
        ",example,,,,,,,,,,,,,\n"
        ",,,,Dataset,,,id,,,,,,,\n"
        ",,,,,int_enum,integer,,INT_ENUM,,,,,,\n"
        ",,,,,,enum,,1,1,,,,,\n"
        ",,,,,,,,2,2,,,,,\n"
    )

    reader = csv.DictReader(io.StringIO(manifest))
    model = "example/Dataset"

    state = read(reader)
    assert state.errors == []

    property = state.manifest.models[model].properties["int_enum"]
    assert property.type == "integer"
    enum_item_1, enum_item_2 = property.enums[""]
    assert enum_item_1.source == "1"
    assert enum_item_1.prepare == "1"
    assert enum_item_2.source == "2"
    assert enum_item_2.prepare == "2"


def test_import_property_enum_type_boolean():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
        ",example,,,,,,,,,,,,,,,,\n"
        ",,,,Dataset,,,,,,1,,,,,,,\n"
        ",,,,,boolean_enum,boolean,,BooleanEnum/text(),,,,,4,,,,,,,\n"
        ",,,,,,enum,,True,true,,,,,,,,,,,\n"
        ",,,,,,,,False,false,,,,,,,,,,,\n"
    )
    reader = csv.DictReader(io.StringIO(manifest))
    model = "example/Dataset"

    state = read(reader)

    assert state.errors == []
    property = state.manifest.models[model].properties["boolean_enum"]
    assert property.type == "boolean"
    enum_item_1, enum_item_2 = property.enums[""]
    assert enum_item_1.source == "True"
    assert enum_item_1.prepare == "true"
    assert enum_item_2.source == "False"
    assert enum_item_2.prepare == "false"


def test_import_property_enum_type_number():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
        ",example,,,,,,,,,,,,,,,,\n"
        ",,,,Dataset,,,,,,1,,,,,,,\n"
        ",,,,,type,number required,,TypeID/text(),,,,,4,,,,,,,\n"
        ",,,,,,enum,,1.1,1.2,,,,,,,,,,,\n"
        ",,,,,,,,1.3,1.4,,,,,,,,,,,\n"
    )

    reader = csv.DictReader(io.StringIO(manifest))
    model = "example/Dataset"

    state = read(reader)

    assert state.errors == []
    property = state.manifest.models[model].properties["type"]
    assert property.type == "number"
    enum_item_1, enum_item_2 = property.enums[""]
    assert enum_item_1.source == "1.1"
    assert enum_item_1.prepare == "1.2"
    assert enum_item_2.source == "1.3"
    assert enum_item_2.prepare == "1.4"


def test_import_property_string_enum_without_prepare_uses_source_value():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n"
        ",example,,,,,,,,,,,,,\n"
        ",,,,Dataset,,,id,,,,,,,\n"
        ",,,,,id,integer,,,,,,,,\n"
        ",,,,,str_enum,string,,STR_ENUM,,,,,,\n"
        ",,,,,,enum,,one,,,,,,\n"
        ",,,,,,,,two,,,,,,\n"
    )
    reader = csv.DictReader(io.StringIO(manifest))
    model = "example/Dataset"

    state = read(reader)
    assert state.errors == []

    str_enum_property = state.manifest.models[model].properties["str_enum"]
    assert str_enum_property.type == "string"
    enum_item_1 = str_enum_property.enums[""][0]
    assert enum_item_1.source == "one"
    assert enum_item_1.prepare == '"one"'
    enum_item_2 = str_enum_property.enums[""][1]
    assert enum_item_2.source == "two"
    assert enum_item_2.prepare == '"two"'


def test_import_property_string_enum_without_quoted_prepare_adds_error():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n"
        ",example,,,,,,,,,,,,,\n"
        ",,,,Dataset,,,id,,,,,,,\n"
        ",,,,,id,integer,,,,,,,,\n"
        ",,,,,str_enum,string,,STR_ENUM,,,,,,\n"
        ",,,,,,enum,,one,one,,,,,\n"
    )
    reader = csv.DictReader(io.StringIO(manifest))
    model = "example/Dataset"

    state = read(reader)
    assert state.errors == []

    str_enum_property = state.manifest.models[model].properties["str_enum"]
    assert str_enum_property.type == "string"
    enum_item_1 = str_enum_property.enums[""][0]
    assert enum_item_1.source == "one"
    assert enum_item_1.prepare == "one"
    assert enum_item_1.errors == ['Reikšmė "one" turi būti string tipo.']


def test_import_property_not_string_enum_without_prepare_results_in_error():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n"
        ",example,,,,,,,,,,,,,\n"
        ",,,,Dataset,,,id,,,,,,,\n"
        ",,,,,id,integer,,,,,,,,\n"
        ",,,,,int_enum,integer,,INT_ENUM,,,,,,\n"
        ",,,,,,enum,,1,,,,,,\n"
        ",,,,,,,,2,,,,,,\n"
    )
    reader = csv.DictReader(io.StringIO(manifest))
    model = "example/Dataset"

    state = read(reader)
    assert state.errors == []

    int_enum_property = state.manifest.models[model].properties["int_enum"]
    assert int_enum_property.type == "integer"

    enum_item_1 = int_enum_property.enums[""][0]
    assert enum_item_1.source == "1"
    assert enum_item_1.prepare == ""
    assert enum_item_1.errors == [
        'Duomenų reikšmė (source: "1") privalo turėti nurodytą "prepare" stulpelį.',
        'Reikšmė "" turi būti integer tipo.',
    ]
    enum_item_2 = int_enum_property.enums[""][1]
    assert enum_item_2.source == "2"
    assert enum_item_2.prepare == ""
    assert enum_item_2.errors == [
        'Duomenų reikšmė (source: "2") privalo turėti nurodytą "prepare" stulpelį.',
        'Reikšmė "" turi būti integer tipo.',
    ]


def test_import_enum_checks_uniqueness_based_on_source_and_prepare():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n"
        ",example,,,,,,,,,,,,,\n"
        ",,,,Dataset,,,id,,,,,,,\n"
        ",,,,,id,integer,,,,,,,,\n"
        ",,,,,int_enum,integer,,INT_ENUM,,,,,,\n"
        ",,,,,,enum,,1,1,,,,,\n"
        ",,,,,,,,2,1,,,,,\n"
        ",,,,,,,,1,1,,,,,\n"
    )
    reader = csv.DictReader(io.StringIO(manifest))
    model = "example/Dataset"

    state = read(reader)
    assert state.errors == []

    int_enum_property = state.manifest.models[model].properties["int_enum"]
    assert int_enum_property.type == "integer"

    enum_item_1 = int_enum_property.enums[""][0]
    assert enum_item_1.source == "1"
    assert enum_item_1.prepare == "1"
    assert enum_item_1.errors == []
    enum_item_2 = int_enum_property.enums[""][1]
    assert enum_item_2.source == "2"
    assert enum_item_2.prepare == "1"
    assert enum_item_2.errors == []
    enum_item_3 = int_enum_property.enums[""][2]
    assert enum_item_3.source == "1"
    assert enum_item_3.prepare == "1"
    assert enum_item_3.errors == ['Galima reikšmė (source: "1") "1" jau egzistuoja.']

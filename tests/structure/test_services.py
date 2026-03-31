import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from factory.django import FileField

from vitrina.classifiers.models import Status
from vitrina.cms.factories import FilerFileFactory
from vitrina.comments.factories import CommentFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import ViispRepresentativeFactory, OrganizationFactory, WhitelistedCodeNameFactory
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat
from vitrina.resources.models import DatasetDistribution
from vitrina.structure import VersionStatus
from vitrina.structure.factories import VersionFactory
from vitrina.structure.models import (
    Base,
    Enum,
    EnumItem,
    Metadata,
    Model,
    Param,
    ParamItem,
    Prefix,
    Property,
    PropertyList,
)
from vitrina.structure.services import create_structure_objects
from vitrina.users.factories import UserFactory


@pytest.fixture
def setup_default_status_data():
    defaults = [
        ("Discont", "discont"),
        ("Withdrawn", "withdrawn"),
        ("Completed", "completed"),
        ("Deprecated", "deprecated"),
    ]

    for name, codename in defaults:
        Status.objects.get_or_create(codename=codename, defaults={"name": name})


@pytest.mark.django_db
def test_structure_with_file_error(app: DjangoTestApp):
    manifest = "id,dataset,unknown"
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(structure), object_id=structure.pk)
    assert comments.count() == 1
    assert comments[0].body == "Unrecognized header name 'unknown'."


@pytest.mark.django_db
def test_structure_with_file_error_and_existing_comments(app: DjangoTestApp):
    manifest = "id,dataset,unknown"
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    CommentFactory(
        content_type=ContentType.objects.get_for_model(structure),
        object_id=structure.pk,
        body="Existing error",
        type=Comment.STRUCTURE_ERROR,
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(structure), object_id=structure.pk)
    assert comments.count() == 1
    assert comments[0].body == "Unrecognized header name 'unknown'."


@pytest.mark.django_db
def test_structure_prefixes(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,spinta,,,,,,,https://github.com/atviriduomenys/spinta/issues/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dcat,,,,,,,http://www.w3.org/ns/dcat#,,,,\n"
        ",,,,,,,dct,,,,,,,http://purl.org/dc/terms/,,,,"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    prefixes = Prefix.objects.all()
    assert prefixes.count() == 3
    assert list(
        prefixes.filter(
            content_type=ContentType.objects.get_for_model(structure.dataset), object_id=structure.dataset.pk
        ).values_list("metadata__name", flat=True)
    ) == ["dcat", "dct"]
    assert list(
        prefixes.filter(content_type=ContentType.objects.get_for_model(structure), object_id=structure.pk).values_list(
            "metadata__name", flat=True
        )
    ) == ["spinta"]


@pytest.mark.django_db
def test_structure_prefix_after_enum(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ',,,,,,enum,Size,,"SMALL",,,,,,,,,\n'
        ',,,,,,,,,"MEDIUM",,,,,,,,,\n'
        ',,,,,,,,,"BIG",,,,,,,,,\n'
        ",,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dcat,,,,,,,http://www.w3.org/ns/dcat#,,,,\n"
        ",,,,,,,dct,,,,,,,http://purl.org/dc/terms/,,,,"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    prefixes = Prefix.objects.all()
    assert prefixes.count() == 2
    assert list(
        prefixes.filter(
            content_type=ContentType.objects.get_for_model(structure.dataset), object_id=structure.dataset.pk
        ).values_list("metadata__name", flat=True)
    ) == ["dcat", "dct"]


@pytest.mark.django_db
def test_structure_datasets(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp1,,,,,,,,,,,,,,,,,\n"
        ",datasets/gov/ivpk/adp2,,,,,,,,,,,,,,,,,\n"
        ",datasets/gov/ivpk/adp3,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    metadata_version = create_structure_objects(structure)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset), metadata_version=metadata_version
    )
    assert metadata.count() == 1
    assert sorted(list(metadata.values_list("name", flat=True))) == [
        "datasets/gov/ivpk/adp3",
    ]


@pytest.mark.django_db
def test_structure_models_and_props(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ',,,,Licence,,,id,,"page(id)",,,,,,,Licence,,\n'
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,2,,,open,dct:title,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        ",,,,Catalog,,,id,,,,,,,,,Catalog,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    metadata_version = create_structure_objects(structure)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset), metadata_version=metadata_version
    )
    assert metadata.count() == 1
    assert list(metadata.values_list("name", flat=True)) == ["datasets/gov/ivpk/adp"]

    models = Model.objects.filter(metadata_version=metadata_version)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Model), metadata_version=metadata_version
    ).order_by("order")
    assert models.count() == 2
    assert models[0].dataset == structure.dataset
    assert metadata.count() == 2
    assert list(
        metadata.values_list(
            "name",
            "ref",
            "prepare",
            "prepare_ast",
            "title",
        )
    ) == [
        (
            "datasets/gov/ivpk/adp/Licence",
            "id",
            "page(id)",
            {"name": "page", "args": [{"name": "bind", "args": ["id"]}]},
            "Licence",
        ),
        ("datasets/gov/ivpk/adp/Catalog", "id", "", {}, "Catalog"),
    ]

    props = Property.objects.filter(model=models[0], metadata_version=metadata_version)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id__in=props.values_list("pk", flat=True),
        metadata_version=metadata_version,
    ).order_by("order")
    assert props.count() == 2
    assert metadata.count() == 2
    assert list(
        metadata.values_list(
            "name",
            "type",
            "level",
            "access",
            "uri",
            "title",
        )
    ) == [
        ("id", "integer", 5, Metadata.OPEN, "dct:identifier", "Identifikatorius"),
        ("title", "string", 2, Metadata.OPEN, "dct:title", ""),
    ]

    props = Property.objects.filter(model=models[1], metadata_version=metadata_version)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id__in=props.values_list("pk", flat=True),
        metadata_version=metadata_version,
    )
    assert props.count() == 1
    assert metadata.count() == 1
    assert list(
        metadata.values_list(
            "name",
            "type",
            "level",
            "access",
            "uri",
            "title",
        )
    ) == [
        ("id", "integer", 5, Metadata.OPEN, "dct:identifier", "Identifikatorius"),
    ]


@pytest.mark.django_db
def test_structure_with_base_model(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.w3.org/ns/dcat#,,,,\n"
        ",,,,Base,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        ",,,Base,,,,,,,,,,,,,,,\n"
        ",,,,Catalog,,,,,,,,,,,,,,\n"
        ",,,,,title,string,,,,2,,,open,dct:title,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    models = Model.objects.all()
    assert models.count() == 2
    assert Base.objects.count() == 1
    assert models.filter(base__isnull=False).count() == 1
    assert models.filter(base__isnull=False)[0].base.metadata.first().name == "datasets/gov/ivpk/adp/Base"


@pytest.mark.django_db
def test_structure_with_base_model_two_manifests(app: DjangoTestApp):
    organization = OrganizationFactory(whitelisted_names=["datasets/gov/rc/"])
    manifest_base = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/rc/ar/apskritis,,,,,,,,,,,,,,,,,\n"
        ",,,,Apskritis,,,adm_kodas,,,4,,,,,,,,\n"
        ",,,,,adm_kodas,integer,,,,4,,,open,,,,,,\n"
        ",,,,,tipas,string,,,,3,,,open,,,,,,\n"
        ",,,,,santrumpa,string,,,,3,,,open,,,,,,\n"
        ",,,,,pavadinimas,string,,,,3,,,open,,,,,\n"
        ",,,,,adm_nuo,date,D,,,4,,,open,,,,,,\n"
    )

    base_structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest_base)),
        dataset=DatasetFactory(organization=organization),
    )

    manifest_with_base = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/rc/ar/savivaldybe,,,,,,,,,,,,,,,,,\n"
        ",,,/datasets/gov/rc/ar/apskritis/Apskritis,,,,,,,,,,,,,,,\n"
        ",,,,Savivaldybe,,,sav_kodas,,,4,,,,,,,,\n"
        ",,,,,sav_kodas,integer,,,,4,,,open,,,,,,\n"
        ",,,,,tipas,string,,,,3,,,open,,,,,,\n"
        ",,,,,tipo_santrumpa,string,,,,3,,,open,,,,,,\n"
        ",,,,,pavadinimas,string,,,,3,,,open,,,,,,\n"
        ",,,,,sav_nuo,date,D,,,4,,,open,,,,,,\n"
    )

    structure_with_base = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest_with_base)),
        dataset=DatasetFactory(organization=organization),
    )

    base_structure.dataset.current_structure = base_structure
    base_structure.dataset.save()
    version = create_structure_objects(base_structure)

    structure_with_base.dataset.current_structure = structure_with_base
    structure_with_base.dataset.save()
    create_structure_objects(structure_with_base, version)

    models = Model.objects.all()
    assert models.count() == 2
    assert Base.objects.count() == 1
    assert models.filter(base__isnull=False).count() == 1
    assert models.filter(base__isnull=False)[0].base.metadata.first().name == "datasets/gov/rc/ar/apskritis/Apskritis"


@pytest.mark.django_db
def test_structure_with_property_ref(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "1,,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        ",,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,continent,ref,Continent[id],,,5,,,open,dct:continent,,,,\n"
        "2,,,,Continent,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    country = Model.objects.filter(metadata__uuid="1").first()
    continent = Model.objects.filter(metadata__uuid="2").first()
    props = Property.objects.filter(model=country)
    assert props.count() == 3
    assert props.filter(ref_model__isnull=False).count() == 1
    assert props.filter(ref_model__isnull=False).first().ref_model == continent
    assert list(
        props.filter(ref_model__isnull=False).first().property_list.values_list("property__metadata__name", flat=True)
    ) == ["id"]


@pytest.mark.django_db
def test_structure_with_property_ref_two_manifests(app: DjangoTestApp):
    organization = OrganizationFactory(whitelisted_names=["datasets/gov/rc/"])
    ref_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/rc/ar/apskritis,,,,,,,,,,,,,,,,,\n"
        "1,,,,Apskritis,,,adm_kodas,,,4,,,,,,,,\n"
        ",,,,,adm_kodas,integer,,,,4,,,open,,,,,,\n"
        ",,,,,tipas,string,,,,3,,,open,,,,,,\n"
        ",,,,,santrumpa,string,,,,3,,,open,,,,,,\n"
        ",,,,,pavadinimas,string,,,,3,,,open,,,,,\n"
        ",,,,,adm_nuo,date,D,,,4,,,open,,,,,,\n"
    )

    ref_object_structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=ref_manifest)),
        dataset=DatasetFactory(organization=organization),
    )

    ref_object_structure.dataset.current_structure = ref_object_structure
    ref_object_structure.dataset.save()
    version = create_structure_objects(ref_object_structure)

    manifest_with_ref = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/rc/ar/savivaldybe,,,,,,,,,,,,,,,,,\n"
        "2,,,,Savivaldybe,,,sav_kodas,,,4,,,,,,,,\n"
        ",,,,,sav_kodas,integer,,,,4,,,open,,,,,,\n"
        ",,,,,tipas,string,,,,3,,,open,,,,,,\n"
        ",,,,,tipo_santrumpa,string,,,,3,,,open,,,,,,\n"
        ",,,,,pavadinimas,string,,,,3,,,open,,,,,,\n"
        ",,,,,apskritis,ref,/datasets/gov/rc/ar/apskritis/Apskritis,,,4,,,open,,,,,,\n"
        ",,,,,sav_nuo,date,D,,,4,,,open,,,,,,\n"
    )

    structure_with_ref = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest_with_ref)),
        dataset=DatasetFactory(organization=organization),
    )

    structure_with_ref.dataset.current_structure = structure_with_ref
    structure_with_ref.dataset.save()
    create_structure_objects(structure_with_ref, version)

    county = Model.objects.filter(metadata__uuid="1").first()
    municipality = Model.objects.filter(metadata__uuid="2").first()

    props = Property.objects.filter(model=municipality)
    assert props.count() == 6
    assert props.filter(ref_model__isnull=False).count() == 1
    assert props.filter(ref_model__isnull=False).first().ref_model == county


@pytest.mark.django_db
def test_structure_with_model_ref(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        '1,,,,Country,,,"id,title",,,,,,,,,,,\n'
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        ",,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,continent,ref,Continent,,,5,,,open,dct:continent,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    country = Model.objects.filter(metadata__uuid="1").first()
    assert list(
        PropertyList.objects.filter(
            content_type=ContentType.objects.get_for_model(country), object_id=country.pk
        ).values_list("property__metadata__name", flat=True)
    ) == ["id", "title"]


@pytest.mark.django_db
def test_structure_with_denorm_prop(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "1,,,,Continent,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "2,,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        ",,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,continent,ref,Continent,,,5,,,open,dct:continent,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "3,,,,City,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        ",,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,country,ref,Country,,,5,,,open,,,,,,\n"
        ",,,,,country.id,,,,,5,,,open,,,,,,\n"
        ",,,,,country.continent.id,,,,,5,,,open,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    city = Model.objects.filter(metadata__uuid="3").first()
    props = Property.objects.filter(model=city)
    assert props.count() == 6
    assert props.filter(given=True).count() == 5
    assert props.filter(given=False).first().metadata.first().name == "country.continent"
    assert props.filter(metadata__name="country.continent.id")[0].property.metadata.first().name == "country.continent"
    assert props.filter(metadata__name="country.continent")[0].property.metadata.first().name == "country"
    assert props.filter(metadata__name="country.id")[0].property.metadata.first().name == "country"
    assert props.filter(metadata__name="country")[0].property is None


@pytest.mark.django_db
def test_structure_with_existing_structure(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp1,,,,,,,,,,,,,,,,,\n"
        ",,resource1,,,,,,,,,,,,,,,,\n"
        "2,datasets/gov/ivpk/adp2,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        ",,resource2,,,,,,,,,,,,,,,,\n"
        "3,,,,Country,,,,,,,,,,,,,,\n"
        "4,,,,,id,integer,,,,5,,,open,,,Identifikatorius,,,\n"
        "5,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "6,,,,,deprecated,string,,,,5,,,open,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "7,,,,City,,,,,,,,,,,,,,\n"
        "8,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    metadata_version = create_structure_objects(structure)
    assert Metadata.objects.filter(dataset=structure.dataset, metadata_version=metadata_version).count() == 9

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "2,datasets/gov/ivpk/adp2/updated,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        ",,resource2,,,,,,,,,,,,,,,,\n"
        "3,,,,CountryUpdated,,,,,,,,,,,,,,\n"
        "4,,,,,id,string,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        "5,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "9,,,,,continent,ref,Continent,,,5,,,open,dct:continent,,,,\n"
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    metadata_version = create_structure_objects(structure, metadata_version)
    assert Metadata.objects.filter(dataset=structure.dataset, metadata_version=metadata_version).count() == 7
    assert Metadata.objects.get(uuid="2").name == "datasets/gov/ivpk/adp2/updated"
    assert Metadata.objects.get(uuid="3").name == "datasets/gov/ivpk/adp2/updated/CountryUpdated"
    assert Metadata.objects.get(uuid="4").type == "string"
    assert Metadata.objects.filter(uuid="1").count() == 0
    assert Metadata.objects.filter(uuid="6").count() == 0
    assert Metadata.objects.filter(uuid="7").count() == 0
    assert Metadata.objects.filter(uuid="8").count() == 0
    assert Model.objects.filter(metadata__uuid="7").count() == 0
    assert Property.objects.filter(metadata__uuid="6").count() == 0
    assert Property.objects.filter(metadata__uuid="8").count() == 0


@pytest.mark.django_db
def test_structure_with_comments(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,,,comment,type,,,,,,open,,,Dataset comment,,\n"
        "3,,,,Country,,,,,,,,,,,,,,\n"
        "4,,,,,,comment,type,,,,,,open,,,Model comment,,\n"
        "5,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "6,,,,,,comment,type,,,,,,open,,,Property comment,,\n"
        "7,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    metadata_version = VersionFactory(dataset=structure.dataset)
    DatasetDistributionFactory(
        dataset=structure.dataset,
        type="URL",
        download_url="https://get.data.gov.lt/datasets/gov/ivpk/adp/:ns",
        format=FileFormat(title="Saugykla", extension="UAPI"),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, metadata_version)
    assert Metadata.objects.filter(content_type=ContentType.objects.get_for_model(Comment)).count() == 3
    assert Comment.objects.filter(type=Comment.STRUCTURE).count() == 3
    assert (
        Comment.objects.filter(content_type=ContentType.objects.get_for_model(Dataset)).first().content_object
        == structure.dataset
    )
    assert (
        Comment.objects.filter(content_type=ContentType.objects.get_for_model(Model)).first().content_object
        == Metadata.objects.get(uuid="3").object
    )
    assert (
        Comment.objects.filter(content_type=ContentType.objects.get_for_model(Property)).first().content_object
        == Metadata.objects.get(uuid="5").object
    )


@pytest.mark.django_db
def test_structure_with_resource_and_existing_distribution(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        "1,,resource,,,,,,http://www.example.com,,,,,,,,,,\n"
        "2,,,,City,,,,,,,,,,,,,,\n"
        "3,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "4,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "5,,,,Country,,,,,,,,,,,,,,\n"
        "6,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    metadata_version = VersionFactory(dataset=structure.dataset)
    distribution = DatasetDistributionFactory(
        dataset=structure.dataset, type="URL", download_url="http://www.example.com", metadata_version=metadata_version
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, metadata_version)

    assert Metadata.objects.get(uuid="1").object == distribution
    assert Model.objects.get(metadata__uuid="2").distribution == distribution
    assert Model.objects.get(metadata__uuid="5").distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_with_resource_and_existing_distribution_without_title(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,,,,,\n"
        "1,,resource,,,,,,http://www.example.com,,,,,,,,,,\n"
        "2,,,,City,,,,,,,,,,,,,,\n"
        "3,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "4,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "5,,,,Country,,,,,,,,,,,,,,\n"
        "6,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    metadata_version = VersionFactory(dataset=structure.dataset)
    distribution = DatasetDistributionFactory(
        dataset=structure.dataset,
        type="URL",
        download_url="http://www.example.com",
        title="",
        metadata_version=metadata_version,
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, metadata_version=metadata_version)

    distribution.refresh_from_db()
    distribution.set_current_language("lt")
    assert Metadata.objects.get(uuid="1").object == distribution
    assert Model.objects.get(metadata__uuid="2").distribution == distribution
    assert Model.objects.get(metadata__uuid="5").distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA
    assert distribution.title == "resource"


@pytest.mark.django_db
def test_structure_with_resource_and_without_distribution(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,http://www.purl.org/dc/terms/,,,,,\n"
        "1,,resource,,,,,,http://www.example.com,,,,,,,,,,\n"
        "2,,,,City,,,,,,,,,,,,,,\n"
        "3,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "4,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "5,,,,Country,,,,,,,,,,,,,,\n"
        "6,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    assert DatasetDistribution.objects.count() == 1
    distribution = DatasetDistribution.objects.first()
    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().source == "http://www.example.com"
    assert Model.objects.get(metadata__uuid="2").distribution == distribution
    assert Model.objects.get(metadata__uuid="5").distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_without_resource_and_existing_distribution(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "1,,,,City,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "2,,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    metadata_version = VersionFactory(dataset=structure.dataset)
    DatasetDistributionFactory(
        dataset=structure.dataset,
        type="URL",
        download_url="https://get.data.gov.lt/datasets/gov/ivpk/adp/:ns",
        format=FileFormat(title="Saugykla", extension="UAPI"),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, metadata_version)

    assert DatasetDistribution.objects.count() == 1
    assert Model.objects.get(metadata__uuid="1").distribution is None
    assert Model.objects.get(metadata__uuid="2").distribution is None
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_without_resource_and_existing_distribution_without_title(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "1,,,,City,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "2,,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    metadata_version = VersionFactory(dataset=structure.dataset)
    distribution = DatasetDistributionFactory(
        dataset=structure.dataset,
        type="URL",
        download_url="https://get.data.gov.lt/datasets/gov/ivpk/adp/:ns",
        format=FileFormat(title="Saugykla", extension="UAPI"),
        title="adp",
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, metadata_version)

    distribution.refresh_from_db()
    distribution.set_current_language("lt")
    assert DatasetDistribution.objects.count() == 1
    assert Model.objects.get(metadata__uuid="1").distribution is None
    assert Model.objects.get(metadata__uuid="2").distribution is None
    assert structure.dataset.status == Dataset.HAS_DATA
    assert distribution.title == "adp"


@pytest.mark.django_db
def test_structure_without_resource_and_existing_distribution_without_ns(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "1,,,,City,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "2,,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    metadata_version = VersionFactory(dataset=structure.dataset)
    DatasetDistributionFactory(
        dataset=structure.dataset,
        type="URL",
        download_url="https://get.data.gov.lt/datasets/gov/ivpk/adp/",
        format=FileFormat(title="Saugykla", extension="UAPI"),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, metadata_version)

    assert DatasetDistribution.objects.count() == 1
    assert Model.objects.get(metadata__uuid="1").distribution is None
    assert Model.objects.get(metadata__uuid="2").distribution is None
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_without_resource_and_distribution(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "1,,,,City,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "2,,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    assert DatasetDistribution.objects.count() == 0
    assert Model.objects.count() == 2
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_with_enums(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        '2,,,,,,enum,Size,,"SMALL",,,,,,,,,\n'
        '3,,,,,,,,,"MEDIUM",,,,,,,,,\n'
        '4,,,,,,,,,"BIG",,,,,,,,,\n'
        "5,,,,City,,,,,,,,,,,,,,\n"
        "6,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "7,,,,,size,Size,,,,5,,,open,dct:size,,,,\n"
        "8,,,,,type,string,,,,5,,,open,dct:type,,,,\n"
        '9,,,,,,enum,Type,,"""CREATED""",,,,,,,,,\n'
        '10,,,,,,,,,"""MODIFIED""",,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    dataset = structure.dataset
    dataset_enum = Enum.objects.filter(content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk)
    assert dataset_enum.count() == 1
    assert dataset_enum[0].name == "Size"
    assert list(dataset_enum[0].enumitem_set.values_list("metadata__prepare", flat=True)) == ["SMALL", "MEDIUM", "BIG"]

    prop = Property.objects.get(metadata__uuid="8")
    prop_enum = Enum.objects.filter(content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk)
    assert prop_enum.count() == 1
    assert prop_enum[0].name == "Type"
    assert list(prop_enum[0].enumitem_set.values_list("metadata__prepare", flat=True)) == ['"CREATED"', '"MODIFIED"']


@pytest.mark.django_db
def test_structure_with_enum_and_null_value(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
        "1,,,,,type,string,,,,5,,,open,dct:type,,,,\n"
        ',,,,,,enum,Type,,"""CREATED""",,,,,,,,,\n'
        ',,,,,,,,,"""null""",,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    prop = Property.objects.get(metadata__uuid="1")
    prop_enum = Enum.objects.filter(content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk)
    assert prop_enum.count() == 1
    assert prop_enum[0].name == "Type"
    assert list(prop_enum[0].enumitem_set.values_list("metadata__prepare", flat=True)) == ['"CREATED"', '"null"']


@pytest.mark.django_db
def test_structure_with_two_enums_with_different_source_same_prepare_create_two_different_enum_items(
    app: DjangoTestApp,
):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "5,,,,City,,,,,,,,,,,,,,\n"
        "6,,,,,id,integer,,,,5,,,open,,,,,\n"
        "8,,,,,type,integer,,,,5,,,open,,,,,\n"
        "9,,,,,,enum,,1,1,,,,,,,,,\n"
        "10,,,,,,,,2,1,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    prop = Property.objects.get(metadata__uuid="8")
    prop_enum = Enum.objects.filter(content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk)
    assert prop_enum.count() == 1
    assert prop_enum[0].name == ""
    assert list(prop_enum[0].enumitem_set.values_list("metadata__source", "metadata__prepare")) == [
        ("1", "1"),
        ("2", "1"),
    ]


@pytest.mark.django_db
def test_structure_with_enum_without_prepare_value_adds_comment_about_error(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
        "1,,,,,type,integer,,,,5,,,,,,,,\n"
        ",,,,,,enum,Type,one,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    prop = Property.objects.get(metadata__uuid="1")
    prop_enum = Enum.objects.filter(content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk)
    assert prop_enum.count() == 1
    assert prop_enum[0].name == "Type"
    assert not prop_enum[0].enumitem_set.exists()
    assert list(Comment.objects.filter(type=Comment.STRUCTURE_ERROR).values_list("body", flat=True)) == [
        'Reikšmė "" turi būti integer tipo.',
        'Duomenų reikšmė (source: "one") privalo turėti nurodytą "prepare" stulpelį.',
    ]


@pytest.mark.django_db
def test_structure_with_boolean_enum_with_invalid_value_adds_comment_about_error(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
        "1,,,,,type,boolean,,,,5,,,,,,,,\n"
        ",,,,,,enum,,taip,taip,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    prop = Property.objects.get(metadata__uuid="1")
    prop_enum = Enum.objects.filter(content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk)
    assert prop_enum.count() == 1
    assert prop_enum[0].name == ""
    assert not prop_enum[0].enumitem_set.exists()
    assert list(Comment.objects.filter(type=Comment.STRUCTURE_ERROR).values_list("body", flat=True)) == [
        'Reikšmė "taip" turi būti boolean tipo. Viena iš: true, false',
    ]


@pytest.mark.django_db
def test_structure_with_params(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        '2,,,,,,param,country,,"lt",,,,,,,,,\n'
        '3,,,,,,,,,"lv",,,,,,,,,\n'
        '4,,,,,,,,,"ee",,,,,,,,,\n'
        "5,,,,City,,,,,,,,,,,,,,\n"
        '6,,,,,,param,type,,"created",,,,,,,,,\n'
        '7,,,,,,,,,"modified",,,,,,,,,\n'
        "8,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "9,,,,,type,string,,,,5,,,open,dct:type,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    dataset = structure.dataset
    dataset_params = Param.objects.filter(content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk)
    assert dataset_params.count() == 1
    assert dataset_params[0].name == "country"
    assert list(dataset_params[0].paramitem_set.values_list("metadata__prepare", flat=True)) == ["lt", "lv", "ee"]

    model = Model.objects.get(metadata__uuid="5")
    model_params = Param.objects.filter(content_type=ContentType.objects.get_for_model(model), object_id=model.pk)
    assert model_params.count() == 1
    assert model_params[0].name == "type"
    assert list(model_params[0].paramitem_set.values_list("metadata__prepare", flat=True)) == ["created", "modified"]


@pytest.mark.django_db
def test_structure_with_deleted_enums(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "2,,resource,,,,,,,,,,,,,,,,\n"
        '3,,,,,,enum,Size,,"""SMALL""",,,,,,,,,\n'
        '4,,,,,,,,,"""MEDIUM""",,,,,,,,,\n'
        '5,,,,,,,,,"""BIG""",,,,,,,,,\n'
        '6,,,,,,enum,Deprecated,,"""SMALL""",,,,,,,,,\n'
        '7,,,,,,,,,"""MEDIUM""",,,,,,,,,\n'
        '8,,,,,,,,,"""BIG""",,,,,,,,,\n'
        "9,,,,City,,,,,,,,,,,,,,\n"
        "10,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        "11,,,,,size,Size,,,,5,,,open,dct:size,,,,\n"
        "12,,,,,type,string,,,,5,,,open,dct:type,,,,\n"
        '13,,,,,,enum,Type,,"""CREATED""",,,,,,,,,\n'
        '14,,,,,,,,,"""MODIFIED""",,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    metadata_version = create_structure_objects(structure)
    assert Metadata.objects.filter(dataset=structure.dataset, metadata_version=metadata_version).count() == 15
    assert list(Enum.objects.values_list("name", flat=True)) == ["Size", "Deprecated", "Type"]
    assert list(EnumItem.objects.filter(enum__name="Size").values_list("metadata__prepare", flat=True)) == [
        '"SMALL"',
        '"MEDIUM"',
        '"BIG"',
    ]
    assert list(EnumItem.objects.filter(enum__name="Deprecated").values_list("metadata__prepare", flat=True)) == [
        '"SMALL"',
        '"MEDIUM"',
        '"BIG"',
    ]
    assert list(EnumItem.objects.filter(enum__name="Type").values_list("metadata__prepare", flat=True)) == [
        '"CREATED"',
        '"MODIFIED"',
    ]

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "2,,resource,,,,,,,,,,,,,,,,\n"
        '3,,,,,,enum,Size,,"""SMALL""",,,,,,,,,\n'
        '5,,,,,,,,,"""BIG""",,,,,,,,,\n'
        "9,,,,City,,,,,,,,,,,,,,\n"
        "10,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
        "11,,,,,size,Size,,,,5,,,open,dct:size,,,,\n"
        "12,,,,,type,string,,,,5,,,open,dct:type,,,,\n"
        '13,,,,,,enum,Type,,"""CREATED""",,,,,,,,,\n'
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    metadata_version = create_structure_objects(structure, metadata_version)
    assert Metadata.objects.filter(dataset=structure.dataset, metadata_version=metadata_version).count() == 10
    assert list(Enum.objects.values_list("name", flat=True)) == ["Size", "Type"]
    assert list(EnumItem.objects.filter(enum__name="Size").values_list("metadata__prepare", flat=True)) == [
        '"SMALL"',
        '"BIG"',
    ]
    assert list(EnumItem.objects.filter(enum__name="Type").values_list("metadata__prepare", flat=True)) == ['"CREATED"']


@pytest.mark.django_db
def test_structure_with_deleted_params(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,resource,,,,,,,,,,,,,,,,\n"
        '3,,,,,,param,Size,,"SMALL",,,,,,,,,\n'
        '4,,,,,,,,,"MEDIUM",,,,,,,,,\n'
        '5,,,,,,,,,"BIG",,,,,,,,,\n'
        '6,,,,,,param,Deprecated,,"SMALL",,,,,,,,,\n'
        '7,,,,,,,,,"MEDIUM",,,,,,,,,\n'
        '8,,,,,,,,,"BIG",,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    metadata_version = create_structure_objects(structure)
    assert Metadata.objects.filter(dataset=structure.dataset, metadata_version=metadata_version).count() == 8
    assert list(Param.objects.values_list("name", flat=True)) == ["Size", "Deprecated"]
    assert list(ParamItem.objects.filter(param__name="Size").values_list("metadata__prepare", flat=True)) == [
        "SMALL",
        "MEDIUM",
        "BIG",
    ]
    assert list(ParamItem.objects.filter(param__name="Deprecated").values_list("metadata__prepare", flat=True)) == [
        "SMALL",
        "MEDIUM",
        "BIG",
    ]

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,resource,,,,,,,,,,,,,,,,\n"
        '3,,,,,,param,Size,,"SMALL",,,,,,,,,\n'
        '5,,,,,,,,,"BIG",,,,,,,,,\n'
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    metadata_version = create_structure_objects(structure, metadata_version)
    assert Metadata.objects.filter(dataset=structure.dataset, metadata_version=metadata_version).count() == 4
    assert list(Param.objects.values_list("name", flat=True)) == ["Size"]
    assert list(ParamItem.objects.filter(param__name="Size").values_list("metadata__prepare", flat=True)) == [
        "SMALL",
        "BIG",
    ]


@pytest.mark.django_db
def test_structure_without_ids__prefixes(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dcat,,,,,,,http://www.w3.org/ns/dcat#,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dcat,,,,,,,http://www.w3.org/ns/dcat#,,,,\n"
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


@pytest.mark.django_db
def test_structure_without_ids__enums(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ',,,,,,enum,Size,,"SMALL",,,,,,,,,\n'
        ',,,,,,,,,"BIG",,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ',,,,,,enum,Size,,"SMALL",,,,,,,,,\n'
        ',,,,,,,,,"BIG",,,,,,,,,\n'
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


@pytest.mark.django_db
def test_structure_without_ids__params(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ',,,,,,param,ParamSize,,"SMALL",,,,,,,,,\n'
        ',,,,,,,,,"BIG",,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ',,,,,,param,ParamSize,,"SMALL",,,,,,,,,\n'
        ',,,,,,,,,"BIG",,,,,,,,,\n'
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


@pytest.mark.django_db
def test_structure_without_ids__models(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


@pytest.mark.django_db
def test_structure_without_ids__properties(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "2,,,,City,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://www.purl.org/dc/terms/,,,,\n"
        "2,,,,City,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n"
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


@pytest.mark.django_db
def test_structure_without_ids__base(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,Base,,,,,,,,,,,,,,\n"
        ",,,Base,,,,,,,,,,,,,,,\n"
        "3,,,,City,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,Base,,,,,,,,,,,,,,\n"
        ",,,Base,,,,,,,,,,,,,,,\n"
        "3,,,,City,,,,,,,,,,,,,,\n"
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


@pytest.mark.django_db
def test_structure_with_existing_prefixes(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dcat,,,,,,,http://www.w3.org/ns/dcat#,,,,\n"
        ",,,,,,prefix,dcat,,,,,,,http://www.w3.org/ns/dcat#,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(
        Comment.objects.filter(
            type=Comment.STRUCTURE_ERROR,
            content_type=ContentType.objects.get_for_model(structure),
        ).values_list("body", flat=True)
    ) == ['Prefiksas "dcat" jau egzistuoja.']


@pytest.mark.django_db
def test_structure_with_existing_enums(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ',,,,,,enum,Size,,"SMALL",,,,,,,,,\n'
        ',,,,,,,,,"SMALL",,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(
        Comment.objects.filter(
            type=Comment.STRUCTURE_ERROR,
            content_type=ContentType.objects.get_for_model(structure),
        ).values_list("body", flat=True)
    ) == ['Galima reikšmė (source: "") "SMALL" jau egzistuoja.']


@pytest.mark.django_db
def test_structure_with_existing_params(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ',,,,,,param,ParamSize,,"SMALL",,,,,,,,,\n'
        ',,,,,,,,,"SMALL",,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(
        Comment.objects.filter(
            type=Comment.STRUCTURE_ERROR,
            content_type=ContentType.objects.get_for_model(structure),
        ).values_list("body", flat=True)
    ) == ['Parametras "SMALL" jau egzistuoja.']


@pytest.mark.django_db
def test_structure_with_existing_models(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(
        Comment.objects.filter(
            type=Comment.STRUCTURE_ERROR,
            content_type=ContentType.objects.get_for_model(structure),
        ).values_list("body", flat=True)
    ) == ['Modelis "datasets/gov/ivpk/adp/City" jau egzistuoja.']


@pytest.mark.django_db
def test_structure_with_existing_properties(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,,,Identifikatorius,,\n"
        ",,,,,id,integer,,,,5,,,open,,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(
        Comment.objects.filter(
            type=Comment.STRUCTURE_ERROR,
            content_type=ContentType.objects.get_for_model(Model),
        ).values_list("body", flat=True)
    ) == ['Savybė "id" jau egzistuoja.']


@pytest.mark.django_db
def test_structure_with_existing_dataset(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,resource1,,,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,,,Identifikatorius,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["datasets/gov/ivpk/"])),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0
    assert Metadata.objects.filter(dataset=structure.dataset, metadata_version=version).count() == 4

    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,resource1,,,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,,,Identifikatorius,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(organization=structure.dataset.organization),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, version)
    assert list(
        Comment.objects.filter(
            type=Comment.STRUCTURE_ERROR,
            content_type=ContentType.objects.get_for_model(structure),
        ).values_list("body", flat=True)
    ) == ['Duomenų išteklius "datasets/gov/ivpk/adp" jau egzistuoja.']
    assert Metadata.objects.filter(dataset=structure.dataset, metadata_version=version).count() == 0


@pytest.mark.django_db
def test_structure_with_deleted_base(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,Base,,,,,,,,,,,,,,\n"
        "3,,,Base,,,,,,,,,,,,,,,\n"
        "4,,,,City,,,,,,,,,,,,,,\n"
        "5,,,,Country,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)
    assert Base.objects.count() == 1
    assert Base.objects.get(metadata__uuid="3").model == Model.objects.get(metadata__uuid="2")
    assert Model.objects.get(metadata__uuid="4").base == Base.objects.get(metadata__uuid="3")
    assert Model.objects.get(metadata__uuid="5").base == Base.objects.get(metadata__uuid="3")

    new_manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,Base,,,,,,,,,,,,,,\n"
        "4,,,,City,,,,,,,,,,,,,,\n"
        "5,,,,Country,,,,,,,,,,,,,,\n"
    )
    structure.file = FilerFileFactory(file=FileField(filename="file.csv", data=new_manifest))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, version)

    assert Base.objects.count() == 0
    assert Model.objects.get(metadata__uuid="4").base is None
    assert Model.objects.get(metadata__uuid="5").base is None


@pytest.mark.django_db
def test_average_level(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "1,,,,Base,,,,,,4,,,,,,,,,\n"
        ",,,Base,,,,,,,4,,,,,,,,,\n"
        "2,,,,City,,,,,,5,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,,,,,,,\n"
        ",,,,,title,string,,,,5,,,,,,,,,\n"
        ",,,,,country,ref,Country,,,4,,,,,,,,,\n"
        "3,,,,Country,,,,,,4,,,,,,,,,\n"
        ",,,,,id,integer,,,,3,,,,,,,,,\n"
        ",,,,,title,string,,,,2,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert structure.dataset.metadata.first().average_level == 4
    assert Model.objects.get(metadata__uuid="1").metadata.first().average_level == 4
    assert Model.objects.get(metadata__uuid="2").metadata.first().average_level == 5
    assert Model.objects.get(metadata__uuid="3").metadata.first().average_level == 3


@pytest.mark.django_db
def test_average_level_without_given_level(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        "1,,,,Base,,,,,,,,,,,,,,\n"  # level 3
        ",,,Base,,,,,,,,,,,,,,,\n"  # level 3
        "2,,,,City,,,,,,,,,,,,,,\n"  # level 3
        ",,,,,id,integer,,,,,,,,dcat:id,,,\n"  # level 3
        ",,,,,country1,ref,Country,,,,,,,,,,,\n"  # level 4
        ",,,,,country2,ref,Country,,,,,,,dcat:country,,,,\n"  # level 5
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert structure.dataset.metadata.first().average_level == 3
    assert Model.objects.get(metadata__uuid="1").metadata.first().average_level == 3
    assert Model.objects.get(metadata__uuid="2").metadata.first().average_level == 4


@pytest.mark.django_db
def test_uri_format(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        "2,,,,City,,,,,,,,,,dct:City,,,,\n"
        "3,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "4,,,,Country,,,,,,,,,,https://example.com#Country,,,,\n"
        "5,,,,,id,integer,,,,5,,,open,,https://example.com#id,Identifikatorius,,\n"
        "6,,,,Continent,,,,,,,,,,dct.Continent,,,,\n"
        "7,,,,,id,integer,,,,5,,,open,dct.identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert (
        list(
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Model),
                object_id=Model.objects.get(metadata__uuid=2).pk,
                type=Comment.STRUCTURE_ERROR,
            ).values_list("body", flat=True)
        )
        == []
    )
    assert (
        list(
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Property),
                object_id=Property.objects.get(metadata__uuid=3).pk,
                type=Comment.STRUCTURE_ERROR,
            ).values_list("body", flat=True)
        )
        == []
    )
    assert (
        list(
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Model),
                object_id=Model.objects.get(metadata__uuid=4).pk,
                type=Comment.STRUCTURE_ERROR,
            ).values_list("body", flat=True)
        )
        == []
    )
    assert (
        list(
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Property),
                object_id=Property.objects.get(metadata__uuid=5).pk,
                type=Comment.STRUCTURE_ERROR,
            ).values_list("body", flat=True)
        )
        == []
    )
    assert list(
        Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(Model),
            object_id=Model.objects.get(metadata__uuid=6).pk,
            type=Comment.STRUCTURE_ERROR,
        ).values_list("body", flat=True)
    ) == ['Neteisingas uri "dct.Continent" formatas.']
    assert list(
        Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(Property),
            object_id=Property.objects.get(metadata__uuid=7).pk,
            type=Comment.STRUCTURE_ERROR,
        ).values_list("body", flat=True)
    ) == ['Neteisingas uri "dct.identifier" formatas.']


@pytest.mark.django_db
def test_uri_prefix(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dcat,,,,,,,http://www.w3.org/ns/dcat#,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,City,,,,,,,,,,dcat:City,,,,\n"
        "3,,,,,id,integer,,,,5,,,open,dcat:identifier,,Identifikatorius,,\n"
        "4,,,,Country,,,,,,,,,,dct:Country,,,,\n"
        "5,,,,,id,integer,,,,5,,,open,dct:integer,,Identifikatorius,,\n"
        "6,,,,Continent,,,,,,,,,,spinta:Continent,,,,\n"
        "7,,,,,id,integer,,,,5,,,open,spinta:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert (
        list(
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Model),
                object_id=Model.objects.get(metadata__uuid=2).pk,
                type=Comment.STRUCTURE_ERROR,
            ).values_list("body", flat=True)
        )
        == []
    )
    assert (
        list(
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Property),
                object_id=Property.objects.get(metadata__uuid=3).pk,
                type=Comment.STRUCTURE_ERROR,
            ).values_list("body", flat=True)
        )
        == []
    )
    assert (
        list(
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Model),
                object_id=Model.objects.get(metadata__uuid=4).pk,
                type=Comment.STRUCTURE_ERROR,
            ).values_list("body", flat=True)
        )
        == []
    )
    assert (
        list(
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Property),
                object_id=Property.objects.get(metadata__uuid=5).pk,
                type=Comment.STRUCTURE_ERROR,
            ).values_list("body", flat=True)
        )
        == []
    )
    assert list(
        Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(Model),
            object_id=Model.objects.get(metadata__uuid=6).pk,
            type=Comment.STRUCTURE_ERROR,
        ).values_list("body", flat=True)
    ) == ['Prefiksas "spinta" duomenų ištekliuje neegzistuoja.']
    assert list(
        Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(Property),
            object_id=Property.objects.get(metadata__uuid=7).pk,
            type=Comment.STRUCTURE_ERROR,
        ).values_list("body", flat=True)
    ) == ['Prefiksas "spinta" duomenų ištekliuje neegzistuoja.']


@pytest.mark.django_db
def test_structure_export__dataset_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,,,,,,prefix,spinta,,,,,,,,https://github.com/atviriduomenys/spinta/issues/,,,\n"
        "2,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "3,,,,,,prefix,dcat,,,,,,,,http://www.w3.org/ns/dcat#,,,\n"
        "4,,,,,,,dct,,,,,,,,http://purl.org/dc/terms/,,,"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description"),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = VersionFactory(dataset=structure.dataset, major=3, status=VersionStatus.PRE_RELEASE)
    create_structure_objects(structure, version)
    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, version.pk]))
    assert "datasets/gov/ivpk/adp/3" in resp.text


@pytest.mark.django_db
@pytest.mark.parametrize("use_version", [False, True])
def test_structure_export__prefixes(app: DjangoTestApp, use_version):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,,,,,,prefix,spinta,,,,,,,,https://github.com/atviriduomenys/spinta/issues/,,,\n"
        "2,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "3,,,,,,prefix,dcat,,,,,,,,http://www.w3.org/ns/dcat#,,,\n"
        "4,,,,,,,dct,,,,,,,,http://purl.org/dc/terms/,,,"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description"),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()

    if use_version:
        metadata_version = VersionFactory(dataset=structure.dataset)
        create_structure_objects(structure, metadata_version)
        resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, metadata_version.pk]))
    else:
        create_structure_objects(structure)
        resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))

    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,,,,,,prefix,spinta,,,,,,,,,,https://github.com/atviriduomenys/spinta/issues/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "2,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "3,,,,,,prefix,dcat,,,,,,,,,,http://www.w3.org/ns/dcat#,,,\r\n"
        "4,,,,,,,dct,,,,,,,,,,http://purl.org/dc/terms/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )


@pytest.mark.django_db
def test_structure_export__with_resource_params(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        "2,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "3,,rc_wsdl,,,,wsdl,,https://test-data.data.gov.lt/api/v1/rc/get-data/?wsdl,,,,,,,,,,\n"
        "4,,get_data,,,,soap,,Get.GetPort.GetPort.GetData,wsdl(rc_wsdl),,,,,,,,,\n"
        "5,,,,,,param,action_type,input/ActionType,,,,,,,,,,\n"
        "6,,,,Country,,,,,,,,,,,,,,\n"
        "7,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "8,,,,,title,string,,,,5,,,private,dct:title,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description"),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()

    version = structure.dataset.metadata.first().metadata_version
    create_structure_objects(structure, version)

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, version.pk]))
    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,,,,,,prefix,dct,,,,,,,,,,http://purl.org/dc/terms/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "2,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "3,,rc_wsdl,,,,wsdl,,https://test-data.data.gov.lt/api/v1/rc/get-data/?wsdl,,,,,,,,,,,rc_wsdl,\r\n"
        "4,,get_data,,,,soap,,Get.GetPort.GetPort.GetData,,wsdl(rc_wsdl),,,,,,,,,get_data,\r\n"
        "5,,,,,,param,action_type,input/ActionType,,,,,,develop,,,,,,\r\n"
        "6,,,,Country,,,,,,,,,,develop,,,,,,\r\n"
        "7,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        "8,,,,,title,string,,,,,,,5,develop,,private,dct:title,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )


@pytest.mark.django_db
def test_structure_export__multiple_versions(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    dataset = DatasetFactory(
        title="Multi-Version Dataset",
        description="Dataset with multiple versions",
        organization=OrganizationFactory(whitelisted_names=["datasets/gov/test/"]),
    )

    # Version 1: one model, one property, one prefix, one enum, and one param
    version1 = VersionFactory(dataset=dataset, version=1)
    manifest_v1 = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/test/multi,,,,,,,,,,,,,,,,Multi-Version Dataset,Multi-Version Dataset description\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        '3,,,,,,enum,Status,,"ACTIVE",,,,,,,,,\n'
        '4,,,,,,param,Filter,,"all",,,,,,,,,\n'
        "5,,,,Person,,,id,,,,,,,,,,,Person Model,\n"
        "6,,,,,id,integer,,,,,5,,,open,dct:identifier,,Person ID,"
    )
    structure_v1 = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="v1.csv", data=manifest_v1)), dataset=dataset
    )
    dataset.current_structure = structure_v1
    dataset.save()
    create_structure_objects(structure_v1, version1)

    # Version 2: Add another prefix, enum item, param item, property to Person, and add City model
    version2 = VersionFactory(dataset=dataset, version=2)
    manifest_v2 = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/test/multi,,,,,,,,,,,,,,,,Multi-Version Dataset,Multi-Version Dataset description\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,,,,,prefix,dcat,,,,,,,,http://www.w3.org/ns/dcat#,,,\n"
        '4,,,,,,enum,Status,,"ACTIVE",,,,,,,,,\n'
        '5,,,,,,,,,"INACTIVE",,,,,,,,,\n'
        '6,,,,,,param,Filter,,"all",,,,,,,,,\n'
        '7,,,,,,,,,"recent",,,,,,,,,\n'
        "8,,,,Person,,,id,,,,,,,,,,,Person Model,\n"
        "9,,,,,id,integer,,,,,5,,,open,dct:identifier,,Person ID,\n"
        "10,,,,,name,string,,,,,2,,,open,dct:title,,Person Name,\n"
        "11,,,,City,,,id,,,,,,,,,,,City Model,\n"
        "12,,,,,id,integer,,,,,5,,,open,dct:identifier,,City ID,"
    )
    structure_v2 = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="v2.csv", data=manifest_v2)), dataset=dataset
    )
    dataset.current_structure = structure_v2
    dataset.save()
    create_structure_objects(structure_v2, version2)

    # Version 3: Add another prefix, enum, param, property to City, and add Country model
    version3 = VersionFactory(dataset=dataset, version=3)
    manifest_v3 = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/test/multi,,,,,,,,,,,,,,,,Multi-Version Dataset,Multi-Version Dataset description\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,,,,,prefix,dcat,,,,,,,,http://www.w3.org/ns/dcat#,,,\n"
        "4,,,,,,prefix,foaf,,,,,,,,http://xmlns.com/foaf/0.1/,,,\n"
        '5,,,,,,enum,Status,,"ACTIVE",,,,,,,,,\n'
        '6,,,,,,,,,"INACTIVE",,,,,,,,,\n'
        '7,,,,,,enum,Priority,,"HIGH",,,,,,,,,\n'
        '8,,,,,,param,Filter,,"all",,,,,,,,,\n'
        '9,,,,,,,,,"recent",,,,,,,,,\n'
        '10,,,,,,param,Sort,,"name",,,,,,,,,\n'
        "11,,,,Person,,,id,,,,,,,,,,,Person Model,\n"
        "12,,,,,id,integer,,,,,5,,,open,dct:identifier,,Person ID,\n"
        "13,,,,,name,string,,,,,2,,,open,dct:title,,Person Name,\n"
        "14,,,,City,,,id,,,,,,,,,,,City Model,\n"
        "15,,,,,id,integer,,,,,5,,,open,dct:identifier,,City ID,\n"
        "16,,,,,name,string,,,,,2,,,open,dct:title,,City Name,\n"
        "17,,,,Country,,,id,,,,,,,,,,,Country Model,\n"
        "18,,,,,id,integer,,,,,5,,,open,dct:identifier,,Country ID,"
    )
    structure_v3 = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="v3.csv", data=manifest_v3)), dataset=dataset
    )
    dataset.current_structure = structure_v3
    dataset.save()
    create_structure_objects(structure_v3, version3)

    version_expectations = {
        version1: {
            "present": {
                "models": ["Person"],
                "properties": ["Person ID"],
                "prefixes": ["dct"],
                "enums": ["Status"],
                "enum_values": ["ACTIVE"],
                "params": ["Filter"],
                "param_values": ["all"],
            },
            "absent": {
                "models": ["City", "Country"],
                "properties": ["Person Name", "City ID", "City Name", "Country ID"],
                "prefixes": ["dcat", "foaf"],
                "enums": ["Priority"],
                "enum_values": ["INACTIVE", "HIGH"],
                "params": ["Sort"],
                "param_values": ["recent"],
            },
        },
        version2: {
            "present": {
                "models": ["Person", "City"],
                "properties": ["Person ID", "Person Name", "City ID"],
                "prefixes": ["dct", "dcat"],
                "enums": ["Status"],
                "enum_values": ["ACTIVE", "INACTIVE"],
                "params": ["Filter"],
                "param_values": ["all", "recent"],
            },
            "absent": {
                "models": ["Country"],
                "properties": ["City Name", "Country ID"],
                "prefixes": ["foaf"],
                "enums": ["Priority"],
                "enum_values": ["HIGH"],
                "params": ["Sort"],
            },
        },
        version3: {
            "present": {
                "models": ["Person", "City", "Country"],
                "properties": ["Person ID", "Person Name", "City ID", "City Name", "Country ID"],
                "prefixes": ["dct", "dcat", "foaf"],
                "enums": ["Status", "Priority"],
                "enum_values": ["ACTIVE", "INACTIVE", "HIGH"],
                "params": ["Filter", "Sort"],
                "param_values": ["all", "recent"],
            },
            "absent": {},
        },
    }

    exports = {}
    for version, expectations in version_expectations.items():
        resp = app.get(reverse("dataset-structure-export", args=[dataset.pk, version.pk]))
        exports[version] = resp.text
        text = resp.text

        for category, items in expectations["present"].items():
            for item in items:
                msg = f"Version {version.version}: Expected '{item}' in {category} but not found"
                assert item in text, msg

        for category, items in expectations["absent"].items():
            for item in items:
                msg = f"Version {version.version}: Unexpected '{item}' found in {category}"
                assert item not in text, msg

    assert exports[version1] != exports[version2], "Version 1 and Version 2 exports should be different"
    assert exports[version2] != exports[version3], "Version 2 and Version 3 exports should be different"
    assert exports[version1] != exports[version3], "Version 1 and Version 3 exports should be different"


@pytest.mark.django_db
@pytest.mark.parametrize("use_version", [False, True])
def test_structure_export__models_and_props(app: DjangoTestApp, use_version):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "4,,,,Licence,,,id,,page(id),,,,,,,,Licence,\n"
        "5,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
        "6,,,,,title,string,,,,,2,,,open,dct:title,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "7,,,,Catalog,,,id,,,,,,,,,,Catalog,\n"
        "8,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description", metadata=False),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()

    expected_output = (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "2,,,,,,prefix,dct,,,,,,,,,,http://purl.org/dc/terms/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,,,Title,Description\r\n"
        "4,,,,Licence,,,id,,,page(id),,,,develop,,,,,Licence,\r\n"
        "5,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        "6,,,,,title,string,,,,,,,2,develop,,open,dct:title,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "7,,,,Catalog,,,id,,,,,,,develop,,,,,Catalog,\r\n"
        "8,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )

    if use_version:
        metadata_version = VersionFactory(dataset=structure.dataset)
        create_structure_objects(structure, metadata_version)
        resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, metadata_version.pk]))
    else:
        create_structure_objects(structure)
        resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))

    assert resp.text == expected_output


@pytest.mark.django_db
@pytest.mark.parametrize("use_version", [False, True])
def test_structure_export__base_model(app: DjangoTestApp, use_version):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "4,,,,Base,,,,,,,,,,,,,,\n"
        "5,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "6,,,Base,,,,,,,,,,,,,,,\n"
        "7,,,,Catalog,,,,,,,,,,,,,,\n"
        "8,,,,,title,string,,,,,2,,,open,dct:title,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description", metadata=False),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()

    expected_output = (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "2,,,,,,prefix,dct,,,,,,,,,,http://purl.org/dc/terms/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,,,Title,Description\r\n"
        "4,,,,Base,,,,,,,,,,develop,,,,,,\r\n"
        "5,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "6,,,Base,,,,,,,,,,,,,,,,,\r\n"
        "7,,,,Catalog,,,,,,,,,,develop,,,,,,\r\n"
        "8,,,,,title,string,,,,,,,2,develop,,open,dct:title,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )

    if use_version:
        metadata_version = VersionFactory(dataset=structure.dataset)
        create_structure_objects(structure, metadata_version)
        resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, metadata_version.pk]))
    else:
        create_structure_objects(structure)
        resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))

    assert resp.text == expected_output


@pytest.mark.django_db
@pytest.mark.parametrize("use_version", [False, True])
def test_structure_export__property_ref(app: DjangoTestApp, use_version):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "4,,,,Country,,,,,,,,,,,,,,\n"
        "5,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
        "6,,,,,title,string,,,,,5,,,open,dct:title,,,\n"
        "7,,,,,continent,ref,Continent[id],,,,5,,,open,dct:continent,,,\n"
        "8,,,,Continent,,,,,,,,,,,,,,\n"
        "9,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description", metadata=False),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()

    expected_output = (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "2,,,,,,prefix,dct,,,,,,,,,,http://purl.org/dc/terms/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,,,Title,Description\r\n"
        "4,,,,Country,,,,,,,,,,develop,,,,,,\r\n"
        "5,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        "6,,,,,title,string,,,,,,,5,develop,,open,dct:title,,,\r\n"
        "7,,,,,continent,ref,Continent[id],,,,,,5,develop,,open,dct:continent,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "8,,,,Continent,,,,,,,,,,develop,,,,,,\r\n"
        "9,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )

    if use_version:
        metadata_version = VersionFactory(dataset=structure.dataset)
        create_structure_objects(structure, metadata_version)
        resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, metadata_version.pk]))
    else:
        create_structure_objects(structure)
        resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))

    assert resp.text == expected_output


@pytest.mark.django_db
@pytest.mark.parametrize("use_version", [False, True])
def test_structure_export__model_ref(app: DjangoTestApp, use_version):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        '4,,,,Country,,,"id, title",,,,,,,,,,,\n'
        "5,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
        "6,,,,,title,string,,,,,5,,,open,dct:title,,,\n"
        "7,,,,,continent,ref,Continent,,,,5,,,open,dct:continent,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description", metadata=False),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()

    expected_output = (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "2,,,,,,prefix,dct,,,,,,,,,,http://purl.org/dc/terms/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,,,Title,Description\r\n"
        '4,,,,Country,,,"id, title",,,,,,,develop,,,,,,\r\n'
        "5,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        "6,,,,,title,string,,,,,,,5,develop,,open,dct:title,,,\r\n"
        "7,,,,,continent,ref,Continent,,,,,,5,develop,,open,dct:continent,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )

    if use_version:
        metadata_version = VersionFactory(dataset=structure.dataset)
        create_structure_objects(structure, metadata_version)
        resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, metadata_version.pk]))
    else:
        create_structure_objects(structure)
        resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))

    assert resp.text == expected_output


@pytest.mark.django_db
def test_structure_export__comments(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "4,,,,Country,,,,,,,,,,,,,,\n"
        "5,,,,,,comment,type,,,,,,,open,,,Model comment,\n"
        "6,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
        "7,,,,,,comment,type,,,,,,,open,,,Property comment,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description", metadata=False),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))
    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "2,,,,,,prefix,dct,,,,,,,,,,http://purl.org/dc/terms/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "3,,resource,,,,,,http://www.example.com,,,,,,,,,,,Title,Description\r\n"
        "4,,,,Country,,,,,,,,,,develop,,,,,,\r\n"
        "5,,,,,,comment,type,,,,,,,develop,,open,,,Model comment,\r\n"
        "6,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        "7,,,,,,comment,type,,,,,,,develop,,open,,,Property comment,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("use_version", [False, True])
def test_structure_export__enums(app: DjangoTestApp, use_version):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,,,,,enum,Size,,SMALL,,,,,,,,,,\n"
        "4,,,,,,,,,MEDIUM,,,,,,,,,\n"
        "5,,,,,,,,,BIG,,,,,,,,,\n"
        "6,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "7,,,,City,,,,,,,,,,,,,,\n"
        "8,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
        "9,,,,,size,Size,,,,,5,,,open,dct:size,,,\n"
        "10,,,,,type,string,,,,,5,,,open,dct:type,,,\n"
        "11,,,,,,enum,Type,,'''CREATED''',,,,,,,,,\n"
        "12,,,,,,,,,'''MODIFIED''',,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description", metadata=False),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()

    expected_output = (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "2,,,,,,prefix,dct,,,,,,,,,,http://purl.org/dc/terms/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "3,,,,,,enum,Size,,,SMALL,,,,develop,,,,,,\r\n"
        "4,,,,,,,,,,MEDIUM,,,,develop,,,,,,\r\n"
        "5,,,,,,,,,,BIG,,,,develop,,,,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "6,,resource,,,,,,http://www.example.com,,,,,,,,,,,Title,Description\r\n"
        "7,,,,City,,,,,,,,,,develop,,,,,,\r\n"
        "8,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        "9,,,,,size,Size,,,,,,,5,develop,,open,dct:size,,,\r\n"
        "10,,,,,type,string,,,,,,,5,develop,,open,dct:type,,,\r\n"
        "11,,,,,,enum,Type,,,'''CREATED''',,,,develop,,,,,,\r\n"
        "12,,,,,,,,,,'''MODIFIED''',,,,develop,,,,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )

    if use_version:
        metadata_version = VersionFactory(dataset=structure.dataset)
        create_structure_objects(structure, metadata_version)
        resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, metadata_version.pk]))
    else:
        create_structure_objects(structure)
        resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))

    assert resp.text == expected_output


@pytest.mark.django_db
@pytest.mark.parametrize("use_version", [False, True])
def test_structure_export__params(app: DjangoTestApp, use_version):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n"
        "3,,,,,,param,country,,lt,,,,,,,,,\n"
        "4,,,,,,,,,lv,,,,,,,,,\n"
        "5,,,,,,,,,ee,,,,,,,,,\n"
        "6,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "7,,,,City,,,,,,,,,,,,,,\n"
        "8,,,,,,param,type,,created,,,,,,,,,\n"
        "9,,,,,,,,,modified,,,,,,,,,\n"
        "10,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n"
        "11,,,,,type,string,,,,,5,,,open,dct:type,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description", metadata=False),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()

    expected_output = (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "2,,,,,,prefix,dct,,,,,,,,,,http://purl.org/dc/terms/,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "3,,,,,,param,country,,,lt,,,,develop,,,,,,\r\n"
        "4,,,,,,,,,,lv,,,,develop,,,,,,\r\n"
        "5,,,,,,,,,,ee,,,,develop,,,,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "6,,resource,,,,,,http://www.example.com,,,,,,,,,,,Title,Description\r\n"
        "7,,,,City,,,,,,,,,,develop,,,,,,\r\n"
        "8,,,,,,param,type,,,created,,,,develop,,,,,,\r\n"
        "9,,,,,,,,,,modified,,,,develop,,,,,,\r\n"
        "10,,,,,id,integer,,,,,,,5,develop,,open,dct:identifier,,Identifikatorius,\r\n"
        "11,,,,,type,string,,,,,,,5,develop,,open,dct:type,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )

    if use_version:
        metadata_version = VersionFactory(dataset=structure.dataset)
        create_structure_objects(structure, metadata_version)
        resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, metadata_version.pk]))
    else:
        create_structure_objects(structure)
        resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))

    assert resp.text == expected_output


@pytest.mark.django_db
def test_import_structure_with_wrong_datasets_name(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp/ššš,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.save()
    metadata_version = create_structure_objects(structure)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset),
        metadata_version=metadata_version,
    )
    assert metadata.count() == 0
    comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(structure), object_id=structure.pk)
    assert comments.count() == 1
    assert "kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės." in comments[0].body


@pytest.mark.django_db
def test_structure_resource__resource_title(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        "1,,resource,,,,,,http://www.example.com,,,,,,,,Test resource,,\n"
        "2,,,,City,,,,,,,,,,,,,,\n"
        "3,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "4,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "5,,,,Country,,,,,,,,,,,,,,\n"
        "6,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    distribution = DatasetDistribution.objects.first()
    assert distribution.title == "Test resource"


@pytest.mark.django_db
def test_structure_with_resource__dataset_title(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,Test dataset,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        "1,,resource,,,,,,http://www.example.com,,,,,,,,,,\n"
        "2,,,,City,,,,,,,,,,,,,,\n"
        "3,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "4,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "5,,,,Country,,,,,,,,,,,,,,\n"
        "6,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    distribution = DatasetDistribution.objects.first()
    assert distribution.title == "Test dataset"


@pytest.mark.django_db
def test_structure_with_resource__no_title(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        "1,,resource,,,,,,http://www.example.com,,,,,,,,,,\n"
        "2,,,,City,,,,,,,,,,,,,,\n"
        "3,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "4,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "5,,,,Country,,,,,,,,,,,,,,\n"
        "6,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    distribution = DatasetDistribution.objects.first()
    assert distribution.title == "resource"


@pytest.mark.django_db
def test_structure_without_resource__dataset_title(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,Test dataset,,\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "1,,,,City,,,,,,,,,,,,,,\n"
        "2,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        "3,,,,,title,string,,,,5,,,open,dct:title,,,,\n"
        "4,,,,Country,,,,,,,,,,,,,,\n"
        "5,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    assert DatasetDistribution.objects.count() == 0


@pytest.mark.django_db
def test_structure_export_after_changing_model_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,dataset/org/test/test_dataset,,,,,,,,,,,,,,,,,\n"
        "2,,resource1,,,,,,http://www.example.com,,,,,,,,,Title,Description\n"
        "3,,,,Model,,,id,,,,,,,,,,,\n"
        "4,,,,,id,integer,,,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "5,,,Model,,,,,,,,,,,,,,,\n"
        "6,,,,Country,,,id,,,,,,,,,,,\n"
        "7,,,,,id,int,,,,,,,,,,,,\n"
        "8,,,,,code,string,,,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        ",,,/,,,,,,,,,,,,,,,\n"
        "9,,,,City,,,id,,,,,,,,,,,\n"
        "10,,,,,id,int,,,,,,,,,,,,\n"
        "11,,,,,country,ref,Country,code,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(
            title="Title",
            description="Description",
            metadata=False,
            organization=OrganizationFactory(whitelisted_names=["dataset/org/test/"]),
        ),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    model = Model.objects.get(dataset=structure.dataset, metadata__name="dataset/org/test/test_dataset/Model")
    form = app.get(reverse("model-update", args=[structure.dataset.pk, version.pk, model.name])).forms["model-form"]
    form["name"] = "Modelis"
    resp = form.submit()
    assert resp.url == model.get_absolute_url()
    assert model.metadata.first().name == "dataset/org/test/test_dataset/Modelis"
    assert model.ref_model_base.count() == 1
    assert model.ref_model_base.first().metadata.first().name == "dataset/org/test/test_dataset/Modelis"

    model = Model.objects.get(dataset=structure.dataset, metadata__name="dataset/org/test/test_dataset/Country")
    form = app.get(reverse("model-update", args=[structure.dataset.pk, version.pk, model.name])).forms["model-form"]
    form["name"] = "Salis"
    resp = form.submit()
    assert resp.url == model.get_absolute_url()
    assert model.metadata.first().name == "dataset/org/test/test_dataset/Salis"
    assert model.ref_model_properties.count() == 1
    assert model.ref_model_properties.first().metadata.first().ref == "dataset/org/test/test_dataset/Salis"

    resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))
    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,dataset/org/test/test_dataset,,,,,,,,,,,,,,,,,,Title,Description\r\n"
        "2,,resource1,,,,,,http://www.example.com,,,,,,,,,,,Title,Description\r\n"
        "3,,,,Modelis,,,id,,,,,,,develop,,,,,,\r\n"
        "4,,,,,id,integer,,,,,,,,develop,,,,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        "5,,,Modelis,,,,,,,,,,,,,,,,,\r\n"
        "6,,,,Salis,,,id,,,,,,,develop,,,,,,\r\n"
        "7,,,,,id,int,,,,,,,,develop,,,,,,\r\n"
        "8,,,,,code,string,,,,,,,,develop,,,,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
        ",,,/,,,,,,,,,,,,,,,,,\r\n"
        "9,,,,City,,,id,,,,,,,develop,,,,,,\r\n"
        "10,,,,,id,int,,,,,,,,develop,,,,,,\r\n"
        "11,,,,,country,ref,Salis,code,,,,,,develop,,,,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )


@pytest.mark.django_db
def test_structure_export_after_changing_dataset_title_and_description(app: DjangoTestApp):
    representative = ViispRepresentativeFactory()
    user = representative.user
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,prepare,level,status,visibility,access,uri,eli,title,description\n"
        "1,dataset/org/test/test_dataset,,,,,,,,,,,,,,,,Title,Description\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))

    structure.dataset.current_structure = structure
    structure.dataset.organization = representative.content_object
    structure.dataset.save()
    WhitelistedCodeNameFactory(organization=representative.content_object, code_name="dataset/org/test/")
    version = create_structure_objects(structure, structure.dataset.metadata.first().metadata_version)

    form = app.get(reverse("dataset-change", kwargs={"pk": structure.dataset.pk})).forms["dataset-form"]
    form["title"] = "Edited title"
    form["description"] = "Edited description"
    form["name"] = structure.dataset.organization.name + "edited_dataset"
    resp = form.submit()
    assert resp.url == reverse("dataset-detail", kwargs={"pk": structure.dataset.pk})
    assert structure.dataset.metadata.filter(metadata_version=version).count() == 1
    assert structure.dataset.metadata.first().title == "Edited title"
    assert structure.dataset.metadata.first().description == "Edited description"

    resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))
    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        f"1,{structure.dataset.organization.name + 'edited_dataset'},,,,,,,,,,,,,,,,,,Edited title,Edited description\r\n"
    )


@pytest.mark.django_db
def test_structure_export_after_changing_distribution_title_and_description(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,dataset/gov/test/test_dataset,,,,,,,,,,,,,,,,Dataset,Dataset description\n"
        "2,,test_resource,,,,,,https://example.com,,,,,,,,,Resource,Resource description\n"
        "3,,,,Model,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(
            title="Dataset",
            description="Dataset description",
            metadata=False,
            organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"]),
        ),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)
    dist_format = FileFormat()

    distribution = DatasetDistribution.objects.first()
    form = app.get(
        reverse("resource-change", kwargs={"pk": distribution.pk, "version_id": distribution.metadata_version.pk})
    ).forms["resource-form"]
    form["title"] = "Edited title"
    form["description"] = "Edited description"
    form["format"] = dist_format.pk
    resp = form.submit()
    assert resp.url == reverse(
        "resource-detail", args=[structure.dataset.pk, distribution.metadata_version.pk, distribution.pk]
    )
    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().title == "Edited title"
    assert distribution.metadata.first().description == "Edited description"

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, version.pk]))
    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,dataset/gov/test/test_dataset,,,,,,,,,,,,,,,,,,Dataset,Dataset description\r\n"
        "2,,test_resource,,,,,,https://example.com,,,,,,,,,,,Edited title,Edited description\r\n"
        "3,,,,Model,,,,,,,,,,develop,,,,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )


@pytest.mark.django_db
def test_structure_export_after_changing_distribution_level(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,dataset/gov/test/test_dataset,,,,,,,,,,,,,,,,Dataset,Dataset description\n"
        "2,,test_resource,,,,,,https://example.com,,,,,,,,,Resource,Resource description\n"
        "3,,,,Model,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(
            title="Dataset",
            description="Dataset description",
            metadata=False,
            organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"]),
        ),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)
    dist_format = FileFormat()

    distribution = DatasetDistribution.objects.first()
    form = app.get(
        reverse("resource-change", kwargs={"pk": distribution.pk, "version_id": distribution.metadata_version.pk})
    ).forms["resource-form"]
    form["level"] = 2
    form["format"] = dist_format.pk
    resp = form.submit()
    assert resp.url == reverse(
        "resource-detail", args=[structure.dataset.pk, distribution.metadata_version.pk, distribution.pk]
    )
    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().level_given == 2

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk, version.pk]))
    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,dataset/gov/test/test_dataset,,,,,,,,,,,,,,,,,,Dataset,Dataset description\r\n"
        "2,,test_resource,,,,,,https://example.com,,,,,2,,,,,,Resource,Resource description\r\n"
        "3,,,,Model,,,,,,,,,,develop,,,,,,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )


@pytest.mark.django_db
def test_structure_export__visibility_row(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "3,,,,Pavadinimas,,,id,,,,4,,package,protected,,,Pavadinimas,\n"
        "4,,,,,id,integer,,,,,4,,package,protected,,,ID,\n"
        "5,,,,,class,integer,,,,,4,,package,protected,,,class,\n"
        "6,,,,,,enum,,1,1,,4,,package,protected,,,Class One,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(
            title="Pavadinimas",
            description="Aprašymas",
            organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"]),
        ),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, structure.dataset.metadata.first().metadata_version)

    resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))
    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,,Pavadinimas,Aprašymas\r\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,,resource,\r\n"
        "3,,,,Pavadinimas,,,id,,,,,,4,develop,package,protected,,,Pavadinimas,\r\n"
        "4,,,,,id,integer,,,,,,,4,develop,package,protected,,,ID,\r\n"
        "5,,,,,class,integer,,,,,,,4,develop,package,protected,,,class,\r\n"
        "6,,,,,,enum,,1,,1,,,4,develop,package,protected,,,Class One,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )


@pytest.mark.django_db
def test_structure_export__eli_row(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "3,,,,Pavadinimas,,,id,,,,4,,,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.1,Pavadinimas,\n"
        "4,,,,,id,integer,,,,,4,,,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.2,ID,\n"
        "5,,,,,class,integer,,,,,4,,,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.3,class,\n"
        "6,,,,,,enum,,1,1,,4,,,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.3.1,Class One,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(
            title="Pavadinimas",
            description="Aprašymas",
            organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"]),
        ),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, structure.dataset.metadata.first().metadata_version)

    resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))
    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,,Pavadinimas,Aprašymas\r\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,,resource,\r\n"
        "3,,,,Pavadinimas,,,id,,,,,,4,develop,,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.1,Pavadinimas,\r\n"
        "4,,,,,id,integer,,,,,,,4,develop,,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.2,ID,\r\n"
        "5,,,,,class,integer,,,,,,,4,develop,,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.3,class,\r\n"
        "6,,,,,,enum,,1,,1,,,4,develop,,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.3.1,Class One,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )


@pytest.mark.django_db
def test_structure_export__status_row(app: DjangoTestApp, setup_default_status_data):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "3,,,,Pavadinimas,,,id,,,,4,completed,,protected,,,Pavadinimas,\n"
        "4,,,,,id,integer,,,,,4,withdrawn,,protected,,,ID,\n"
        "5,,,,,class,integer,,,,,4,deprecated,,protected,,,class,\n"
        "6,,,,,,enum,,1,1,,4,discont,,protected,,,Class One,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(
            title="Pavadinimas",
            description="Aprašymas",
            organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"]),
        ),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure, structure.dataset.metadata.first().metadata_version)

    resp = app.get(reverse("dataset-structure-export-no-version", args=[structure.dataset.pk]))
    assert resp.text == (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,count,level,status,visibility,access,uri,eli,title,description\r\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,,Pavadinimas,Aprašymas\r\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,,resource,\r\n"
        "3,,,,Pavadinimas,,,id,,,,,,4,completed,,protected,,,Pavadinimas,\r\n"
        "4,,,,,id,integer,,,,,,,4,withdrawn,,protected,,,ID,\r\n"
        "5,,,,,class,integer,,,,,,,4,deprecated,,protected,,,class,\r\n"
        "6,,,,,,enum,,1,,1,,,4,discont,,protected,,,Class One,\r\n"
        ",,,,,,,,,,,,,,,,,,,,\r\n"
    )


@pytest.mark.django_db
def test_structure_models_props_and_enums_with_visibility_status_eli(app: DjangoTestApp, setup_default_status_data):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "3,,,,Pavadinimas,,,id,,,4,completed,package,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.1,Pavadinimas,,\n"
        "4,,,,,id,integer,,,,4,completed,package,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.2,ID,,\n"
        "5,,,,,class,integer,,,,4,discont,protected,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.3,class,,\n"
        "6,,,,,,enum,,1,1,4,deprecated,protected,protected,,https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.3.1,Class One,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"])),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    models = Model.objects.all()
    metadata = Metadata.objects.filter(content_type=ContentType.objects.get_for_model(Model))
    completed_status_id = Status.objects.filter(codename="completed").values_list("id", flat=True).first()

    assert models.count() == 1
    assert models[0].dataset == structure.dataset
    assert metadata.count() == 1
    assert list(metadata.values_list("visibility", "status", "eli")) == [
        (Metadata.PACKAGE, completed_status_id, "https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.1")
    ]

    props = Property.objects.filter(model=models[0])
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Property), object_id__in=props.values_list("pk", flat=True)
    )
    discont_status_id = Status.objects.filter(codename="discont").values_list("id", flat=True).first()

    assert props.count() == 2
    assert metadata.count() == 2
    assert set(metadata.values_list("visibility", "status", "eli")) == {
        (Metadata.PACKAGE, completed_status_id, "https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.2"),
        (Metadata.PROTECTED, discont_status_id, "https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.3"),
    }

    prop = Property.objects.get(metadata__uuid="5")
    prop_enum = Enum.objects.filter(content_type=ContentType.objects.get_for_model(prop), object_id=prop.pk)
    deprecated_status_id = Status.objects.filter(codename="deprecated").values_list("id", flat=True).first()

    assert prop_enum.count() == 1
    assert list(prop_enum[0].enumitem_set.values_list("metadata__eli", "metadata__visibility", "metadata__status")) == [
        (
            "https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.296815/asr#11.3.1",
            Metadata.PROTECTED,
            deprecated_status_id,
        )
    ]


@pytest.mark.django_db
def test_structure_with_property_level_higher_then_model(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "3,,,,Pavadinimas,,,id,,,4,,package,protected,,,Pavadinimas,,\n"
        "4,,,,,id,integer,,,,4,,public,protected,,,ID,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"])),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    model = Model.objects.get(metadata__uuid="3")
    prop = Property.objects.get(metadata__uuid="4")
    assert prop.visibility == model.visibility


@pytest.mark.django_db
def test_structure_with_enum_level_higher_then_property(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "3,,,,Pavadinimas,,,id,,,4,,package,protected,,,Pavadinimas,,\n"
        "4,,,,,id,integer,,,,4,,package,protected,,,ID,,\n"
        "5,,,,,class,integer,,,,4,,package,protected,,,class,,\n"
        "6,,,,,,enum,,1,1,4,,public,protected,,,Class One,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"])),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    model = Model.objects.get(metadata__uuid="3")
    property = Property.objects.get(metadata__uuid="5")
    property_enum = Enum.objects.get(content_type=ContentType.objects.get_for_model(Property), object_id=property.pk)

    enum_item_visibility = property_enum.enumitem_set.values_list("metadata__visibility", flat=True).first()

    assert enum_item_visibility == property.visibility
    assert enum_item_visibility == model.visibility


@pytest.mark.django_db
def test_structure_with_enum_level_higher_then_model(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,dataset/gov/test/example,,,,,,,,,,,,,,,,,\n"
        "2,,resource,,,,xml,,resource.xml,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "3,,,,Pavadinimas,,,id,,,4,,package,protected,,,Pavadinimas,,\n"
        "4,,,,,id,integer,,,,4,,package,protected,,,ID,,\n"
        "5,,,,,class,integer,,,,4,,,protected,,,class,,\n"
        "6,,,,,,enum,,1,1,4,,public,protected,,,Class One,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"])),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    model = Model.objects.get(metadata__uuid="3")
    property = Property.objects.get(metadata__uuid="5")
    property_enum = Enum.objects.get(content_type=ContentType.objects.get_for_model(Property), object_id=property.pk)

    enum_item_visibility = property_enum.enumitem_set.values_list("metadata__visibility", flat=True).first()
    assert enum_item_visibility == model.visibility


@pytest.mark.django_db
def test_structure_with_origin_source_type_headers(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,source.type,prepare,origin,level,status,visibility,access,uri,eli,title,description,count\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,,,\n"
        ",,,,City,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()
    metadata_version = create_structure_objects(structure)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset),
        metadata_version=metadata_version,
    )
    assert metadata.count() == 1
    assert sorted(list(metadata.values_list("name", flat=True))) == [
        "datasets/gov/ivpk/adp",
    ]
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


class TestStructureBaseModels:
    @pytest.mark.django_db
    def test_structure_base_and_model_defined_in_file(self, app: DjangoTestApp):
        """Model for Base is defined in the same file."""
        manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            ",dataset/gov/test/example,,,,,,,,,,,,,,,,\n"
            ",,,,Animal,,,,,,0,completed,public,,,,,\n"
            ",,,,,id,string,,source_animal_id,,4,completed,package,protected,,,,\n"
            ",,,Animal,,,,,,,1,completed,public,,,,,\n"
            ",,,,Dog,,,,,,0,completed,public,,,,,\n"
            ",,,,,action,string,,source_dog_action,,4,completed,package,protected,,,,\n"
            ",,,/,,,,,,,,,,,,,,\n"
        )

        structure = DatasetStructureFactory(
            file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
            dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"])),
        )
        structure.dataset.current_structure = structure
        structure.dataset.save()
        create_structure_objects(structure)

        assert Base.objects.count() == 1
        base_object = Base.objects.get(metadata__name="dataset/gov/test/example/Animal")
        assert Base.objects.first().model.name == "Animal"
        assert Model.objects.count() == 2
        assert Model.objects.get(metadata__name="dataset/gov/test/example/Animal")
        assert Model.objects.get(metadata__name="dataset/gov/test/example/Dog").base == base_object

    @pytest.mark.django_db
    def test_structure_two_imports_first_model_secondly_reference_the_model_as_base(self, app: DjangoTestApp):
        """Two imports: First one imports a manifest with a model. Second, uses the model as a base.

        In this case, the model that was imported with the first file must have a Version status of STABLE.
        """
        manifest_with_model_definition = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            ",dataset/gov/test/example,,,,,,,,,,,,,,,,\n"
            ",,,,Animal,,,,,,0,completed,public,,,,,\n"
            ",,,,,id,string,,source_animal_id,,4,completed,package,protected,,,,\n"
        )
        structure_model = DatasetStructureFactory(
            file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest_with_model_definition)),
            dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"])),
        )
        structure_model.dataset.current_structure = structure_model
        structure_model.dataset.save()
        version = create_structure_objects(structure_model)
        version.status = VersionStatus.STABLE
        version.save()

        manifest_with_base_reference = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            ",dataset/org/test/example2,,,,,,,,,,,,,,,,\n"
            ",,,dataset/gov/test/example/Animal,,,,,,,1,completed,public,,,,,\n"
            ",,,,Dog,,,,,,0,completed,public,,,,,\n"
            ",,,,,action,string,,source_dog_action,,4,completed,package,protected,,,,\n"
            ",,,/,,,,,,,,,,,,,,\n"
        )
        structure_base = DatasetStructureFactory(
            file=FilerFileFactory(file=FileField(filename="file2.csv", data=manifest_with_base_reference)),
            dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/org/test/"])),
        )
        structure_base.dataset.current_structure = structure_base
        structure_base.dataset.save()
        create_structure_objects(structure_base)

        assert Model.objects.count() == 2
        animal_model = Model.objects.get(metadata__name="dataset/gov/test/example/Animal")
        dog_model = Model.objects.get(metadata__name="dataset/org/test/example2/Dog")

        assert Base.objects.count() == 1
        base_object = Base.objects.get(metadata__name="dataset/gov/test/example/Animal")

        assert base_object.model == animal_model
        assert dog_model.base == base_object

    @pytest.mark.django_db
    def test_structure_two_imports_first_model_secondly_reference_the_model_as_base_model_not_released(
        self, app: DjangoTestApp
    ):
        manifest_with_model_definition = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            ",dataset/gov/test/example,,,,,,,,,,,,,,,,\n"
            ",,,,Animal,,,,,,0,completed,public,,,,,\n"
            ",,,,,id,string,,source_animal_id,,4,completed,package,protected,,,,\n"
        )
        structure_model = DatasetStructureFactory(
            file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest_with_model_definition)),
            dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"])),
        )
        structure_model.dataset.current_structure = structure_model
        structure_model.dataset.save()
        version = create_structure_objects(structure_model)
        version.status = VersionStatus.DRAFT
        version.save()

        manifest_with_base_reference = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            ",dataset/org/test/example2,,,,,,,,,,,,,,,,\n"
            ",,,dataset/gov/test/example/Animal,,,,,,,1,completed,public,,,,,\n"
            ",,,,Dog,,,,,,0,completed,public,,,,,\n"
            ",,,,,action,string,,source_dog_action,,4,completed,package,protected,,,,\n"
            ",,,/,,,,,,,,,,,,,,\n"
        )
        structure_base = DatasetStructureFactory(
            file=FilerFileFactory(file=FileField(filename="file2.csv", data=manifest_with_base_reference)),
            dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/org/test/"])),
        )
        structure_base.dataset.current_structure = structure_base
        structure_base.dataset.save()
        create_structure_objects(structure_base)

        assert Base.objects.count() == 0
        assert Model.objects.count() == 2
        assert Model.objects.get(metadata__name="dataset/org/test/example2/Dog").base is None

        error_comment = Comment.objects.get(content_type=ContentType.objects.get_for_model(Model))
        assert error_comment.type == Comment.STRUCTURE_ERROR
        assert error_comment.body == (
            "Nepavyko susieti bazinio modelio „dataset/gov/test/example/Animal“. "
            "Įsitikinkite, kad jis egzistuoja ir turi patvirtintą (stabilią) versiją."
        )

    @pytest.mark.django_db
    def test_structure_base_defined_but_model_does_not_exist(self, app: DjangoTestApp):
        """No model exists for the defined Base"""
        manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            ",dataset/gov/test/example,,,,,,,,,,,,,,,,\n"
            ",,,Animal,,,,,,,1,completed,public,,,,,\n"
            ",,,,Dog,,,,,,0,completed,public,,,,,\n"
            ",,,,,action,string,,source_dog_action,,4,completed,package,protected,,,,\n"
            ",,,/,,,,,,,,,,,,,,\n"
        )

        structure = DatasetStructureFactory(
            file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
            dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"])),
        )
        structure.dataset.current_structure = structure
        structure.dataset.save()
        create_structure_objects(structure)

        assert Base.objects.count() == 0  # No model to link with - no base is created.
        assert Model.objects.count() == 1
        assert Model.objects.get(metadata__name="dataset/gov/test/example/Dog").base is None

        error_comment = Comment.objects.get(content_type=ContentType.objects.get_for_model(Model))
        assert error_comment.type == Comment.STRUCTURE_ERROR
        assert error_comment.body == (
            "Nepavyko susieti bazinio modelio „dataset/gov/test/example/Animal“. "
            "Įsitikinkite, kad jis egzistuoja ir turi patvirtintą (stabilią) versiją."
        )


class TestStructureComments:
    @pytest.mark.django_db
    def test_structure_comments_are_created(self, app: DjangoTestApp):
        manifest = (
            "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
            ",dataset/gov/test/dataset,,,,,,,,,,,,,,,,\n"
            ",,,,Animal,,,,source_animal_model,,,,,,,,,\n"
            ',,,,,,comment,model,,"update(model: ""Animal/:part"")",2,completed,protected,open,https://github.com/example/issues/1,,,\n'
            ",,,,,id,string,,source_animal_id,,4,,,,,,,\n"
            ",,,Animal,,,,,,,,,,,,,,\n"
            ',,,,,,comment,model,,"update(model: ""Animal"")",2,completed,protected,open,https://github.com/example/issues/2,,,\n'
            ",,,,Dog,,,,,,,,,,,,,\n"
            ",,,,,action,string,,source_dog_action,,4,,,,,,,\n"
        )

        structure = DatasetStructureFactory(
            file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
            dataset=DatasetFactory(organization=OrganizationFactory(whitelisted_names=["dataset/gov/test/"])),
        )
        structure.dataset.current_structure = structure
        structure.dataset.save()

        create_structure_objects(structure)

        # Comments created for model.
        comment_model = Comment.objects.get(content_type=ContentType.objects.get_for_model(Model))
        assert comment_model.prepare == 'update(model: "Animal/:part")'
        assert comment_model.uri == "https://github.com/example/issues/1"

        # Comments created for base.
        comment_base = Comment.objects.get(content_type=ContentType.objects.get_for_model(Base))
        assert comment_base.prepare == 'update(model: "Animal")'
        assert comment_base.uri == "https://github.com/example/issues/2"


def test_structure_boolean_enums(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
        "1,dataset,,,,,,,,,,,,,,,,\n"
        "2,,,,Approver,,,,,,1,,,,,,,\n"
        "3,,,,,is_active,boolean,,IsActive/text(),,,,,4,,,,,,,\n"
        "4,,,,,,enum,,True,true,,,,,,,,,,,\n"
        "5,,,,,,,,False,false,,,,,,,,,,,\n"
    )

    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()

    create_structure_objects(structure)

    assert Comment.objects.filter(content_type=ContentType.objects.get_for_model(Property)).count() == 0

    assert Enum.objects.count() == 1
    enum = Enum.objects.first()
    enum_items = enum.enumitem_set.all()
    assert enum_items.count() == 2
    assert list(enum_items.values_list("metadata__prepare", flat=True)) == ["true", "false"]


def test_structure_boolean_enums_invalid_source(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
        "1,dataset,,,,,,,,,,,,,,,,\n"
        "2,,,,Approver,,,,,,1,,,,,,,\n"
        "3,,,,,is_active,boolean,,IsActive/text(),,,,,4,,,,,,,\n"
        "4,,,,,,enum,,True,True,,,,,,,,,,,\n"
        "5,,,,,,,,False,False,,,,,,,,,,,\n"
    )

    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()

    create_structure_objects(structure)

    comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Property))
    assert comments.count() == 2
    assert comments.first().body == 'Reikšmė "False" turi būti boolean tipo. Viena iš: true, false'
    assert comments.last().body == 'Reikšmė "True" turi būti boolean tipo. Viena iš: true, false'

    assert Enum.objects.count() == 1
    assert Enum.objects.first().enumitem_set.count() == 0  # No enum-items created due to errors.


def test_structure_number_enums(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description\n"
        ",example,,,,,,,,,,,,,,,,\n"
        ",,,,Dataset,,,,,,1,,,,,,,\n"
        ",,,,,type,number required,,TypeID/text(),,,,,4,,,,,,,\n"
        ",,,,,,enum,,1.1,1.2,,,,,,,,,,,\n"
        ",,,,,,,,1.3,1.4,,,,,,,,,,,\n"
    )

    structure = DatasetStructureFactory(file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)))
    structure.dataset.current_structure = structure
    structure.dataset.save()

    create_structure_objects(structure)

    assert Comment.objects.filter(content_type=ContentType.objects.get_for_model(Property)).count() == 0
    assert Enum.objects.count() == 1
    enum = Enum.objects.first()
    enum_items = enum.enumitem_set.all()
    assert enum_items.count() == 2
    assert list(enum_items.values_list("metadata__prepare", flat=True)) == ["1.2", "1.4"]

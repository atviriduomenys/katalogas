import pytest
from django.contrib.contenttypes.models import ContentType
from django_webtest import DjangoTestApp
from factory.django import FileField

from vitrina.cms.factories import FilerFileFactory
from vitrina.comments.factories import CommentFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.models import Metadata, Prefix, Model, Property, PropertyList, Enum, Param, EnumItem, \
    ParamItem, Base
from vitrina.structure.services import create_structure_objects


@pytest.mark.django_db
def test_structure_with_file_error(app: DjangoTestApp):
    manifest = 'id,dataset,unknown'
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    comments = Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(structure),
        object_id=structure.pk
    )
    assert comments.count() == 1
    assert comments[0].body == "Unrecognized header name 'unknown'."


@pytest.mark.django_db
def test_structure_with_file_error_and_existing_comments(app: DjangoTestApp):
    manifest = 'id,dataset,unknown'
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    CommentFactory(
        content_type=ContentType.objects.get_for_model(structure),
        object_id=structure.pk,
        body='Existing error',
        type=Comment.STRUCTURE_ERROR
    )

    create_structure_objects(structure)
    comments = Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(structure),
        object_id=structure.pk
    )
    assert comments.count() == 1
    assert comments[0].body == "Unrecognized header name 'unknown'."


@pytest.mark.django_db
def test_structure_prefixes(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',,,,,,prefix,spinta,,,,,https://github.com/atviriduomenys/spinta/issues/,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,\n'
        ',,,,,,,dct,,,,,http://purl.org/dc/terms/,,'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    create_structure_objects(structure)
    prefixes = Prefix.objects.all()
    assert prefixes.count() == 3
    assert list(prefixes.filter(
        content_type=ContentType.objects.get_for_model(structure.dataset),
        object_id=structure.dataset.pk
    ).values_list('metadata__name', flat=True)) == ['dcat', 'dct']
    assert list(prefixes.filter(
        content_type=ContentType.objects.get_for_model(structure),
        object_id=structure.pk
    ).values_list('metadata__name', flat=True)) == ['spinta']


@pytest.mark.django_db
def test_structure_datasets(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp1,,,,,,,,,,,,,\n'
        ',datasets/gov/ivpk/adp2,,,,,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    create_structure_objects(structure)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset)
    )
    assert metadata.count() == 2
    assert list(metadata.values_list('name', flat=True)) == [
        'datasets/gov/ivpk/adp1',
        'datasets/gov/ivpk/adp2',
    ]


@pytest.mark.django_db
def test_structure_models_and_props(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,Licence,,,id,,"page(id)",,,,Licence,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,2,open,dct:title,,\n'
        ',,,,,,,,,,,,,,\n'
        ',,,,Catalog,,,id,,,,,,Catalog,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    create_structure_objects(structure)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset)
    )
    assert metadata.count() == 1
    assert list(metadata.values_list('name', flat=True)) == ['datasets/gov/ivpk/adp']

    models = Model.objects.all()
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Model)
    )
    assert models.count() == 2
    assert models[0].dataset == structure.dataset
    assert metadata.count() == 2
    assert list(metadata.values_list(
        'name',
        'ref',
        'prepare',
        'prepare_ast',
        'title',
    )) == [
        ('datasets/gov/ivpk/adp/Licence', 'id', 'page(id)', {
            'name': 'page',
            'args': [{
                'name': 'bind',
                'args': ['id']
            }]
        }, 'Licence'),
        ('datasets/gov/ivpk/adp/Catalog', 'id', '', {}, 'Catalog'),
    ]

    props = Property.objects.filter(model=models[0])
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id__in=props.values_list('pk', flat=True)
    )
    assert props.count() == 2
    assert metadata.count() == 2
    assert list(metadata.values_list(
        'name',
        'type',
        'level',
        'access',
        'uri',
        'title',
    )) == [
        ('id', 'integer', 5, 'open', 'dct:identifier', 'Identifikatorius'),
        ('title', 'string', 2, 'open', 'dct:title', ''),
    ]

    props = Property.objects.filter(model=models[1])
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id__in=props.values_list('pk', flat=True)
    )
    assert props.count() == 1
    assert metadata.count() == 1
    assert list(metadata.values_list(
        'name',
        'type',
        'level',
        'access',
        'uri',
        'title',
    )) == [
        ('id', 'integer', 5, 'open', 'dct:identifier', 'Identifikatorius'),
    ]


@pytest.mark.django_db
def test_structure_with_base_model(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,Base,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,,,,,,,,,,\n'
        ',,,Base,,,,,,,,,,,\n'
        ',,,,Catalog,,,,,,,,,,\n'
        ',,,,,title,string,,,,2,open,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    create_structure_objects(structure)
    models = Model.objects.all()
    assert models.count() == 2
    assert Base.objects.count() == 1
    assert models.filter(base__isnull=False).count() == 1
    assert models.filter(base__isnull=False)[0].base.metadata.first().name == 'datasets/gov/ivpk/adp/Base'


@pytest.mark.django_db
def test_structure_with_property_ref(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '1,,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
        ',,,,,continent,ref,Continent[id],,,5,open,dct:continent,,\n'
        '2,,,,Continent,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    create_structure_objects(structure)
    country = Model.objects.filter(metadata__uuid='1').first()
    continent = Model.objects.filter(metadata__uuid='2').first()
    props = Property.objects.filter(model=country)
    assert props.count() == 3
    assert props.filter(ref_model__isnull=False).count() == 1
    assert props.filter(ref_model__isnull=False).first().ref_model == continent
    assert list(props.filter(ref_model__isnull=False).first().property_list.values_list(
        'property__metadata__name', flat=True
    )) == ['id']


@pytest.mark.django_db
def test_structure_with_model_ref(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '1,,,,Country,,,"id,title",,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
        ',,,,,continent,ref,Continent,,,5,open,dct:continent,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    create_structure_objects(structure)
    country = Model.objects.filter(metadata__uuid='1').first()
    assert list(PropertyList.objects.filter(
        content_type=ContentType.objects.get_for_model(country),
        object_id=country.pk
    ).values_list(
        'property__metadata__name', flat=True
    )) == ['id', 'title']


@pytest.mark.django_db
def test_structure_with_denorm_prop(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '1,,,,Continent,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,,,,,,,,,,\n'
        '2,,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
        ',,,,,continent,ref,Continent,,,5,open,dct:continent,,\n'
        ',,,,,,,,,,,,,,\n'
        '3,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
        ',,,,,country,ref,Country,,,5,open,,,\n'
        ',,,,,country.id,,,,,5,open,,,\n'
        ',,,,,country.continent.id,,,,,5,open,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    create_structure_objects(structure)
    city = Model.objects.filter(metadata__uuid='3').first()
    props = Property.objects.filter(model=city)
    assert props.count() == 6
    assert props.filter(given=True).count() == 5
    assert props.filter(given=False).first().metadata.first().name == 'country.continent'
    assert props.filter(metadata__name='country.continent.id')[0].property.metadata.first().name == 'country.continent'
    assert props.filter(metadata__name='country.continent')[0].property.metadata.first().name == 'country'
    assert props.filter(metadata__name='country.id')[0].property.metadata.first().name == 'country'
    assert props.filter(metadata__name='country')[0].property is None


@pytest.mark.django_db
def test_structure_with_existing_structure(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp1,,,,,,,,,,,,,\n'
        ',,resource1,,,,,,,,,,,,\n'
        '2,datasets/gov/ivpk/adp2,,,,,,,,,,,,,\n'
        ',,resource2,,,,,,,,,,,,\n'
        '3,,,,Country,,,,,,,,,,\n'
        '4,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '5,,,,,title,string,,,,5,open,dct:title,,\n'
        '6,,,,,deprecated,string,,,,5,open,,,\n'
        ',,,,,,,,,,,,,,\n'
        '7,,,,City,,,,,,,,,,\n'
        '8,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Metadata.objects.count() == 8

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '2,datasets/gov/ivpk/adp2/updated,,,,,,,,,,,,,\n'
        ',,resource2,,,,,,,,,,,,\n'
        '3,,,,CountryUpdated,,,,,,,,,,\n'
        '4,,,,,id,string,,,,5,open,dct:identifier,Identifikatorius,\n'
        '5,,,,,title,string,,,,5,open,dct:title,,\n'
        '9,,,,,continent,ref,Continent,,,5,open,dct:continent,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert Metadata.objects.count() == 5
    assert Metadata.objects.get(uuid='2').name == 'datasets/gov/ivpk/adp2/updated'
    assert Metadata.objects.get(uuid='3').name == 'datasets/gov/ivpk/adp2/updated/CountryUpdated'
    assert Metadata.objects.get(uuid='4').type == 'string'
    assert Metadata.objects.filter(uuid='1').count() == 0
    assert Metadata.objects.filter(uuid='6').count() == 0
    assert Metadata.objects.filter(uuid='7').count() == 0
    assert Metadata.objects.filter(uuid='8').count() == 0
    assert Model.objects.filter(metadata__uuid='7').count() == 0
    assert Property.objects.filter(metadata__uuid='6').count() == 0
    assert Property.objects.filter(metadata__uuid='8').count() == 0


@pytest.mark.django_db
def test_structure_with_comments(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,comment,type,,,,open,,Dataset comment,\n'
        '3,,,,Country,,,,,,,,,,\n'
        '4,,,,,,comment,type,,,,open,,Model comment,\n'
        '5,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '6,,,,,,comment,type,,,,open,,Property comment,\n'
        '7,,,,,title,string,,,,5,open,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Comment)
    ).count() == 3
    assert Comment.objects.count() == 3
    assert Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset)
    ).first().content_object == structure.dataset
    assert Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Model)
    ).first().content_object == Metadata.objects.get(uuid='3').object
    assert Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Property)
    ).first().content_object == Metadata.objects.get(uuid='5').object


@pytest.mark.django_db
def test_structure_with_resource_and_existing_distribution(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '1,,resource,,,,,,http://www.example.com,,,,,,\n'
        '2,,,,City,,,,,,,,,,\n'
        '3,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '4,,,,,title,string,,,,5,open,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    distribution = DatasetDistributionFactory(
        dataset=structure.dataset,
        type='URL',
        download_url='http://www.example.com',
    )

    create_structure_objects(structure)

    assert Metadata.objects.get(uuid='1').object == distribution
    assert Model.objects.get(metadata__uuid='2').distribution == distribution


@pytest.mark.django_db
def test_structure_with_resource_and_without_distribution(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '1,,resource,,,,,,http://www.example.com,,,,,,\n'
        '2,,,,City,,,,,,,,,,\n'
        '3,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '4,,,,,title,string,,,,5,open,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    create_structure_objects(structure)

    assert DatasetDistribution.objects.count() == 1
    distribution = DatasetDistribution.objects.first()
    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().source == 'http://www.example.com'
    assert Model.objects.get(metadata__uuid='2').distribution == distribution


@pytest.mark.django_db
def test_structure_without_resource_and_existing_distribution(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '1,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    distribution = DatasetDistributionFactory(
        dataset=structure.dataset,
        type='URL',
        download_url='https://get.data.gov.lt/datasets/gov/ivpk/adp/City/:ns',
        format=FileFormat(title="Saugykla", extension='API'),
    )

    create_structure_objects(structure)

    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().source == 'https://get.data.gov.lt/datasets/gov/ivpk/adp/City/:ns'
    assert Model.objects.get(metadata__uuid='1').distribution == distribution


@pytest.mark.django_db
def test_structure_without_resource_and_distribution(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '1,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    create_structure_objects(structure)

    assert DatasetDistribution.objects.count() == 1
    distribution = DatasetDistribution.objects.first()
    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().source == 'https://get.data.gov.lt/datasets/gov/ivpk/adp/City/:ns'
    assert Model.objects.get(metadata__uuid='1').distribution == distribution


@pytest.mark.django_db
def test_structure_with_enums(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,enum,Size,,"SMALL",,,,,\n'
        '3,,,,,,,,,"MEDIUM",,,,,\n'
        '4,,,,,,,,,"BIG",,,,,\n'
        '5,,,,City,,,,,,,,,,\n'
        '6,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '7,,,,,size,Size,,,,5,open,dct:size,,\n'
        '8,,,,,type,string,,,,5,open,dct:type,,\n'
        '9,,,,,,enum,Type,,"CREATED",,,,,\n'
        '10,,,,,,,,,"MODIFIED",,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)

    dataset = structure.dataset
    dataset_enum = Enum.objects.filter(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk
    )
    assert dataset_enum.count() == 1
    assert dataset_enum[0].name == 'Size'
    assert list(dataset_enum[0].enumitem_set.values_list('metadata__prepare', flat=True)) == ['SMALL', 'MEDIUM', 'BIG']

    prop = Property.objects.get(metadata__uuid='8')
    prop_enum = Enum.objects.filter(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk
    )
    assert prop_enum.count() == 1
    assert prop_enum[0].name == 'Type'
    assert list(prop_enum[0].enumitem_set.values_list('metadata__prepare', flat=True)) == ['CREATED', 'MODIFIED']


@pytest.mark.django_db
def test_structure_with_params(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,param,country,,"lt",,,,,\n'
        '3,,,,,,,,,"lv",,,,,\n'
        '4,,,,,,,,,"ee",,,,,\n'
        '5,,,,City,,,,,,,,,,\n'
        '6,,,,,,param,type,,"created",,,,,\n'
        '7,,,,,,,,,"modified",,,,,\n'
        '8,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '9,,,,,type,string,,,,5,open,dct:type,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)

    dataset = structure.dataset
    dataset_params = Param.objects.filter(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk
    )
    assert dataset_params.count() == 1
    assert dataset_params[0].name == 'country'
    assert list(dataset_params[0].paramitem_set.values_list('metadata__prepare', flat=True)) == ['lt', 'lv', 'ee']

    model = Model.objects.get(metadata__uuid='5')
    model_params = Param.objects.filter(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk
    )
    assert model_params.count() == 1
    assert model_params[0].name == 'type'
    assert list(model_params[0].paramitem_set.values_list('metadata__prepare', flat=True)) == ['created', 'modified']


@pytest.mark.django_db
def test_structure_with_deleted_enums(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,resource,,,,,,,,,,,,\n'
        '3,,,,,,enum,Size,,"SMALL",,,,,\n'
        '4,,,,,,,,,"MEDIUM",,,,,\n'
        '5,,,,,,,,,"BIG",,,,,\n'
        '6,,,,,,enum,Deprecated,,"SMALL",,,,,\n'
        '7,,,,,,,,,"MEDIUM",,,,,\n'
        '8,,,,,,,,,"BIG",,,,,\n'
        '9,,,,City,,,,,,,,,,\n'
        '10,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '11,,,,,size,Size,,,,5,open,dct:size,,\n'
        '12,,,,,type,string,,,,5,open,dct:type,,\n'
        '13,,,,,,enum,Type,,"CREATED",,,,,\n'
        '14,,,,,,,,,"MODIFIED",,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Metadata.objects.count() == 13
    assert list(Enum.objects.values_list('name', flat=True)) == ['Size', 'Deprecated', 'Type']
    assert list(EnumItem.objects.filter(enum__name='Size').values_list(
        'metadata__prepare', flat=True
    )) == ['SMALL', 'MEDIUM', 'BIG']
    assert list(EnumItem.objects.filter(enum__name='Deprecated').values_list(
        'metadata__prepare', flat=True
    )) == ['SMALL', 'MEDIUM', 'BIG']
    assert list(EnumItem.objects.filter(enum__name='Type').values_list(
        'metadata__prepare', flat=True
    )) == ['CREATED', 'MODIFIED']

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,resource,,,,,,,,,,,,\n'
        '3,,,,,,enum,Size,,"SMALL",,,,,\n'
        '5,,,,,,,,,"BIG",,,,,\n'
        '9,,,,City,,,,,,,,,,\n'
        '10,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '11,,,,,size,Size,,,,5,open,dct:size,,\n'
        '12,,,,,type,string,,,,5,open,dct:type,,\n'
        '13,,,,,,enum,Type,,"CREATED",,,,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert Metadata.objects.count() == 8
    assert list(Enum.objects.values_list('name', flat=True)) == ['Size', 'Type']
    assert list(EnumItem.objects.filter(enum__name='Size').values_list(
        'metadata__prepare', flat=True
    )) == ['SMALL', 'BIG']
    assert list(EnumItem.objects.filter(enum__name='Type').values_list(
        'metadata__prepare', flat=True
    )) == ['CREATED']


@pytest.mark.django_db
def test_structure_with_deleted_params(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,resource,,,,,,,,,,,,\n'
        '3,,,,,,param,Size,,"SMALL",,,,,\n'
        '4,,,,,,,,,"MEDIUM",,,,,\n'
        '5,,,,,,,,,"BIG",,,,,\n'
        '6,,,,,,param,Deprecated,,"SMALL",,,,,\n'
        '7,,,,,,,,,"MEDIUM",,,,,\n'
        '8,,,,,,,,,"BIG",,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Metadata.objects.count() == 7
    assert list(Param.objects.values_list('name', flat=True)) == ['Size', 'Deprecated']
    assert list(ParamItem.objects.filter(param__name='Size').values_list(
        'metadata__prepare', flat=True
    )) == ['SMALL', 'MEDIUM', 'BIG']
    assert list(ParamItem.objects.filter(param__name='Deprecated').values_list(
        'metadata__prepare', flat=True
    )) == ['SMALL', 'MEDIUM', 'BIG']

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,resource,,,,,,,,,,,,\n'
        '3,,,,,,param,Size,,"SMALL",,,,,\n'
        '5,,,,,,,,,"BIG",,,,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert Metadata.objects.count() == 3
    assert list(Param.objects.values_list('name', flat=True)) == ['Size']
    assert list(ParamItem.objects.filter(param__name='Size').values_list(
        'metadata__prepare', flat=True
    )) == ['SMALL', 'BIG']


@pytest.mark.django_db
def test_structure_without_ids__datasets(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(structure.dataset),
        object_id=structure.dataset.pk
    ).values_list('body', flat=True)) == [
        'Dataset "datasets/gov/ivpk/adp" already exists.'
    ]


@pytest.mark.django_db
def test_structure_without__prefixes(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(Prefix),
    ).values_list('body', flat=True)) == [
        'Prefix "dcat" already exists.'
    ]


@pytest.mark.django_db
def test_structure_without_ids__enums(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,enum,Size,,"SMALL",,,,,\n'
        ',,,,,,,,,"BIG",,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,enum,Size,,"SMALL",,,,,\n'
        ',,,,,,,,,"BIG",,,,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(EnumItem),
    ).order_by('body').values_list('body', flat=True)) == [
        'Enum item "BIG" already exists.',
        'Enum item "SMALL" already exists.',
    ]


@pytest.mark.django_db
def test_structure_without_ids__params(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,param,ParamSize,,"SMALL",,,,,\n'
        ',,,,,,,,,"BIG",,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,param,ParamSize,,"SMALL",,,,,\n'
        ',,,,,,,,,"BIG",,,,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(ParamItem),
    ).order_by('body').values_list('body', flat=True)) == [
        'Param item "BIG" already exists.',
        'Param item "SMALL" already exists.',
    ]


@pytest.mark.django_db
def test_structure_without_ids__models(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,City,,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,City,,,,,,,,,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(Model),
    ).values_list('body', flat=True)) == [
        'Model "datasets/gov/ivpk/adp/City" already exists.'
    ]


@pytest.mark.django_db
def test_structure_without_ids__properties(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(Property),
    ).values_list('body', flat=True)) == [
        'Property "id" already exists.'
    ]


@pytest.mark.django_db
def test_structure_without_ids__base(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,Base,,,,,,,,,,\n'
        ',,,Base,,,,,,,,,,,\n'
        '3,,,,City,,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,Base,,,,,,,,,,\n'
        ',,,Base,,,,,,,,,,,\n'
        '3,,,,City,,,,,,,,,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(Base),
    ).values_list('body', flat=True)) == [
        'Base "datasets/gov/ivpk/adp/Base" already exists.'
    ]


@pytest.mark.django_db
def test_structure_with_deleted_base(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,Base,,,,,,,,,,\n'
        '3,,,Base,,,,,,,,,,,\n'
        '4,,,,City,,,,,,,,,,\n'
        '5,,,,Country,,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert Base.objects.count() == 1
    assert Base.objects.get(metadata__uuid='3').model == Model.objects.get(metadata__uuid='2')
    assert Model.objects.get(metadata__uuid='4').base == Base.objects.get(metadata__uuid='3')
    assert Model.objects.get(metadata__uuid='5').base == Base.objects.get(metadata__uuid='3')

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,Base,,,,,,,,,,\n'
        '4,,,,City,,,,,,,,,,\n'
        '5,,,,Country,,,,,,,,,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    create_structure_objects(structure)

    assert Base.objects.count() == 0
    assert Model.objects.get(metadata__uuid='4').base is None
    assert Model.objects.get(metadata__uuid='5').base is None


@pytest.mark.django_db
def test_average_level(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '1,,,,Base,,,,,,4,,,,\n'
        ',,,Base,,,,,,,4,,,,\n'
        '2,,,,City,,,,,,5,,,,\n'
        ',,,,,id,integer,,,,5,,,,\n'
        ',,,,,title,string,,,,5,,,,\n'
        ',,,,,country,ref,Country,,,4,,,,\n'
        '3,,,,Country,,,,,,4,,,,\n'
        ',,,,,id,integer,,,,3,,,,\n'
        ',,,,,title,string,,,,2,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert structure.dataset.metadata.first().average_level == 4
    assert Model.objects.get(metadata__uuid="1").metadata.first().average_level == 4
    assert Model.objects.get(metadata__uuid="2").metadata.first().average_level == 4.6
    assert Model.objects.get(metadata__uuid="3").metadata.first().average_level == 3.25


@pytest.mark.django_db
def test_average_level_without_given_level(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '1,,,,Base,,,,,,,,,,\n'                             # level 3
        ',,,Base,,,,,,,,,,,\n'                              # level 3
        '2,,,,City,,,,,,,,,,\n'                             # level 3
        ',,,,,id,integer,,,,,,dcat:id,,\n'                  # level 3            
        ',,,,,country1,ref,Country,,,,,,,\n'                # level 4
        ',,,,,country2,ref,Country,,,,,dcat:country,,\n'    # level 5
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    create_structure_objects(structure)
    assert structure.dataset.metadata.first().average_level == 3.5
    assert Model.objects.get(metadata__uuid="1").metadata.first().average_level == 3
    assert Model.objects.get(metadata__uuid="2").metadata.first().average_level == 3.6

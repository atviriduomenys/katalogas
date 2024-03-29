import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
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
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_structure_with_file_error(app: DjangoTestApp):
    manifest = 'id,dataset,unknown'
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
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

    structure.dataset.current_structure = structure
    structure.dataset.save()
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

    structure.dataset.current_structure = structure
    structure.dataset.save()
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
def test_structure_prefix_after_enum(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,enum,Size,,"SMALL",,,,,\n'
        ',,,,,,,,,"MEDIUM",,,,,\n'
        ',,,,,,,,,"BIG",,,,,\n'
        ',,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,\n'
        ',,,,,,,dct,,,,,http://purl.org/dc/terms/,,'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    prefixes = Prefix.objects.all()
    assert prefixes.count() == 2
    assert list(prefixes.filter(
        content_type=ContentType.objects.get_for_model(structure.dataset),
        object_id=structure.dataset.pk
    ).values_list('metadata__name', flat=True)) == ['dcat', 'dct']


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

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset)
    )
    assert metadata.count() == 2
    assert sorted(list(metadata.values_list('name', flat=True))) == [
        'datasets/gov/ivpk/adp1',
        'datasets/gov/ivpk/adp2',
    ]


@pytest.mark.django_db
def test_structure_models_and_props(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset)
    )
    assert metadata.count() == 1
    assert list(metadata.values_list('name', flat=True)) == ['datasets/gov/ivpk/adp']

    models = Model.objects.all()
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Model)
    ).order_by('order')
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
    ).order_by('order')
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
        ('id', 'integer', 5, Metadata.OPEN, 'dct:identifier', 'Identifikatorius'),
        ('title', 'string', 2, Metadata.OPEN, 'dct:title', ''),
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
        ('id', 'integer', 5, Metadata.OPEN, 'dct:identifier', 'Identifikatorius'),
    ]


@pytest.mark.django_db
def test_structure_with_base_model(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    models = Model.objects.all()
    assert models.count() == 2
    assert Base.objects.count() == 1
    assert models.filter(base__isnull=False).count() == 1
    assert models.filter(base__isnull=False)[0].base.metadata.first().name == 'datasets/gov/ivpk/adp/Base'


@pytest.mark.django_db
def test_structure_with_base_model_two_manifests(app: DjangoTestApp):
    manifest_base = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/rc/ar/apskritis,,,,,,,,,,,,,\n'
        ',,,,Apskritis,,,adm_kodas,,,4,,,,\n'
        ',,,,,adm_kodas,integer,,,,4,open,,,\n'
        ',,,,,tipas,string,,,,3,open,,,\n'
        ',,,,,santrumpa,string,,,,3,open,,,\n'
        ',,,,,pavadinimas,string,,,,3,open,,,\n'
        ',,,,,adm_nuo,date,D,,,4,open,,,\n'
    )

    base_structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest_base)
        )
    )

    manifest_with_base = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/rc/ar/savivaldybe,,,,,,,,,,,,,\n'
        ',,,/datasets/gov/rc/ar/apskritis/Apskritis,,,,,,,,,,,\n'
        ',,,,Savivaldybe,,,sav_kodas,,,4,,,,\n'
        ',,,,,sav_kodas,integer,,,,4,open,,,\n'
        ',,,,,tipas,string,,,,3,open,,,\n'
        ',,,,,tipo_santrumpa,string,,,,3,open,,,\n'
        ',,,,,pavadinimas,string,,,,3,open,,,\n'
        ',,,,,sav_nuo,date,D,,,4,open,,,\n'
    )

    structure_with_base = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest_with_base)
        )
    )

    base_structure.dataset.current_structure = base_structure
    base_structure.dataset.save()
    create_structure_objects(base_structure)

    structure_with_base.dataset.current_structure = structure_with_base
    structure_with_base.dataset.save()
    create_structure_objects(structure_with_base)

    models = Model.objects.all()
    assert models.count() == 2
    assert Base.objects.count() == 1
    assert models.filter(base__isnull=False).count() == 1
    assert models.filter(base__isnull=False)[0].base.metadata.first().name == 'datasets/gov/rc/ar/apskritis/Apskritis'


@pytest.mark.django_db
def test_structure_with_property_ref(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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

    structure.dataset.current_structure = structure
    structure.dataset.save()
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
def test_structure_with_property_ref_two_manifests(app: DjangoTestApp):
    ref_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/rc/ar/apskritis,,,,,,,,,,,,,\n'
        '1,,,,Apskritis,,,adm_kodas,,,4,,,,\n'
        ',,,,,adm_kodas,integer,,,,4,open,,,\n'
        ',,,,,tipas,string,,,,3,open,,,\n'
        ',,,,,santrumpa,string,,,,3,open,,,\n'
        ',,,,,pavadinimas,string,,,,3,open,,,\n'
        ',,,,,adm_nuo,date,D,,,4,open,,,\n'
    )

    ref_object_structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=ref_manifest)
        )
    )

    ref_object_structure.dataset.current_structure = ref_object_structure
    ref_object_structure.dataset.save()
    create_structure_objects(ref_object_structure)

    manifest_with_ref = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/rc/ar/savivaldybe,,,,,,,,,,,,,\n'
        '2,,,,Savivaldybe,,,sav_kodas,,,4,,,,\n'
        ',,,,,sav_kodas,integer,,,,4,open,,,\n'
        ',,,,,tipas,string,,,,3,open,,,\n'
        ',,,,,tipo_santrumpa,string,,,,3,open,,,\n'
        ',,,,,pavadinimas,string,,,,3,open,,,\n'
        ',,,,,apskritis,ref,/datasets/gov/rc/ar/apskritis/Apskritis,,,4,open,,,\n'
        ',,,,,sav_nuo,date,D,,,4,open,,,\n'
    )

    structure_with_ref = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest_with_ref)
        )
    )

    structure_with_ref.dataset.current_structure = structure_with_ref
    structure_with_ref.dataset.save()
    create_structure_objects(structure_with_ref)

    county = Model.objects.filter(metadata__uuid='1').first()
    municipality = Model.objects.filter(metadata__uuid='2').first()

    props = Property.objects.filter(model=municipality)
    assert props.count() == 6
    assert props.filter(ref_model__isnull=False).count() == 1
    assert props.filter(ref_model__isnull=False).first().ref_model == county


@pytest.mark.django_db
def test_structure_with_model_ref(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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

    structure.dataset.current_structure = structure
    structure.dataset.save()
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
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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

    structure.dataset.current_structure = structure
    structure.dataset.save()
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
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        ',,resource2,,,,,,,,,,,,\n'
        '3,,,,Country,,,,,,,,,,\n'
        '4,,,,,id,integer,,,,5,open,,Identifikatorius,\n'
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Metadata.objects.count() == 9

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '2,datasets/gov/ivpk/adp2/updated,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        ',,resource2,,,,,,,,,,,,\n'
        '3,,,,CountryUpdated,,,,,,,,,,\n'
        '4,,,,,id,string,,,,5,open,dct:identifier,Identifikatorius,\n'
        '5,,,,,title,string,,,,5,open,dct:title,,\n'
        '9,,,,,continent,ref,Continent,,,5,open,dct:continent,,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Metadata.objects.count() == 6
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
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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
    DatasetDistributionFactory(
        dataset=structure.dataset,
        type='URL',
        download_url='https://get.data.gov.lt/datasets/gov/ivpk/adp/:ns',
        format=FileFormat(title="Saugykla", extension='UAPI'),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '1,,resource,,,,,,http://www.example.com,,,,,,\n'
        '2,,,,City,,,,,,,,,,\n'
        '3,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '4,,,,,title,string,,,,5,open,dct:title,,\n'
        '5,,,,Country,,,,,,,,,,\n'
        '6,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
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

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    assert Metadata.objects.get(uuid='1').object == distribution
    assert Model.objects.get(metadata__uuid='2').distribution == distribution
    assert Model.objects.get(metadata__uuid='5').distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_with_resource_and_existing_distribution_without_title(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '1,,resource,,,,,,http://www.example.com,,,,,,\n'
        '2,,,,City,,,,,,,,,,\n'
        '3,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '4,,,,,title,string,,,,5,open,dct:title,,\n'
        '5,,,,Country,,,,,,,,,,\n'
        '6,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
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
        title=""
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    distribution.refresh_from_db()
    assert Metadata.objects.get(uuid='1').object == distribution
    assert Model.objects.get(metadata__uuid='2').distribution == distribution
    assert Model.objects.get(metadata__uuid='5').distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA
    assert distribution.title == 'resource'


@pytest.mark.django_db
def test_structure_with_resource_and_without_distribution(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '1,,resource,,,,,,http://www.example.com,,,,,,\n'
        '2,,,,City,,,,,,,,,,\n'
        '3,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '4,,,,,title,string,,,,5,open,dct:title,,\n'
        '5,,,,Country,,,,,,,,,,\n'
        '6,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    assert DatasetDistribution.objects.count() == 1
    distribution = DatasetDistribution.objects.first()
    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().source == 'http://www.example.com'
    assert Model.objects.get(metadata__uuid='2').distribution == distribution
    assert Model.objects.get(metadata__uuid='5').distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_without_resource_and_existing_distribution(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '1,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
        '2,,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    distribution = DatasetDistributionFactory(
        dataset=structure.dataset,
        type='URL',
        download_url='https://get.data.gov.lt/datasets/gov/ivpk/adp/:ns',
        format=FileFormat(title="Saugykla", extension='UAPI'),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().source == 'https://get.data.gov.lt/datasets/gov/ivpk/adp/:ns'
    assert Model.objects.get(metadata__uuid='1').distribution == distribution
    assert Model.objects.get(metadata__uuid='2').distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_without_resource_and_existing_distribution_without_title(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '1,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
        '2,,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    distribution = DatasetDistributionFactory(
        dataset=structure.dataset,
        type='URL',
        download_url='https://get.data.gov.lt/datasets/gov/ivpk/adp/:ns',
        format=FileFormat(title="Saugykla", extension='UAPI'),
        title="",
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    distribution.refresh_from_db()
    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().source == 'https://get.data.gov.lt/datasets/gov/ivpk/adp/:ns'
    assert Model.objects.get(metadata__uuid='1').distribution == distribution
    assert Model.objects.get(metadata__uuid='2').distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA
    assert distribution.title == "adp"


@pytest.mark.django_db
def test_structure_without_resource_and_existing_distribution_without_ns(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '1,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
        '2,,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    distribution = DatasetDistributionFactory(
        dataset=structure.dataset,
        type='URL',
        download_url='https://get.data.gov.lt/datasets/gov/ivpk/adp/',
        format=FileFormat(title="Saugykla", extension='UAPI'),
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().source == 'https://get.data.gov.lt/datasets/gov/ivpk/adp/'
    assert Model.objects.get(metadata__uuid='1').distribution == distribution
    assert Model.objects.get(metadata__uuid='2').distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_without_resource_and_distribution(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '1,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,open,dct:title,,\n'
        '2,,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    assert DatasetDistribution.objects.count() == 1
    distribution = DatasetDistribution.objects.first()
    assert distribution.metadata.count() == 1
    assert distribution.metadata.first().source == 'https://get.data.gov.lt/datasets/gov/ivpk/adp/:ns'
    assert Model.objects.get(metadata__uuid='1').distribution == distribution
    assert Model.objects.get(metadata__uuid='2').distribution == distribution
    assert structure.dataset.status == Dataset.HAS_DATA


@pytest.mark.django_db
def test_structure_with_enums(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
def test_structure_with_enum_and_null_value(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        ',,,,City,,,,,,,,,,\n'
        '1,,,,,type,string,,,,5,open,dct:type,,\n'
        ',,,,,,enum,Type,,"CREATED",,,,,\n'
        ',,,,,,,,,null,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    prop = Property.objects.get(metadata__uuid='1')
    prop_enum = Enum.objects.filter(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk
    )
    assert prop_enum.count() == 1
    assert prop_enum[0].name == 'Type'
    assert list(prop_enum[0].enumitem_set.values_list('metadata__prepare', flat=True)) == ['CREATED', 'null']


@pytest.mark.django_db
def test_structure_with_params(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Metadata.objects.count() == 14
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
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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
    assert Metadata.objects.count() == 9
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Metadata.objects.count() == 3
    assert list(Param.objects.values_list('name', flat=True)) == ['Size']
    assert list(ParamItem.objects.filter(param__name='Size').values_list(
        'metadata__prepare', flat=True
    )) == ['SMALL', 'BIG']


@pytest.mark.django_db
def test_structure_without_ids__prefixes(app: DjangoTestApp):
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


@pytest.mark.django_db
def test_structure_without_ids__properties(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '2,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0

    new_manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '2,,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure.file = FilerFileFactory(
        file=FileField(filename='file.csv', data=new_manifest)
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0


@pytest.mark.django_db
def test_structure_with_existing_prefixes(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,\n'
        ',,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(structure),
    ).values_list('body', flat=True)) == [
       'Prefiksas "dcat" jau egzistuoja.'
    ]


@pytest.mark.django_db
def test_structure_with_existing_enums(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,enum,Size,,"SMALL",,,,,\n'
        ',,,,,,,,,"SMALL",,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(structure),
    ).values_list('body', flat=True)) == [
       'Galima reikšmė "SMALL" jau egzistuoja.'
    ]


@pytest.mark.django_db
def test_structure_with_existing_params(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,param,ParamSize,,"SMALL",,,,,\n'
        ',,,,,,,,,"SMALL",,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(structure),
    ).values_list('body', flat=True)) == [
       'Parametras "SMALL" jau egzistuoja.'
    ]


@pytest.mark.django_db
def test_structure_with_existing_models(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,City,,,,,,,,,,\n'
        ',,,,City,,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(structure),
    ).values_list('body', flat=True)) == [
       'Modelis "datasets/gov/ivpk/adp/City" jau egzistuoja.'
    ]


@pytest.mark.django_db
def test_structure_with_existing_properties(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,,Identifikatorius,\n'
        ',,,,,id,integer,,,,5,open,,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(Model),
    ).values_list('body', flat=True)) == [
       'Savybė "id" jau egzistuoja.'
    ]


@pytest.mark.django_db
def test_structure_with_existing_dataset(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,resource1,,,,,,,,,,,,\n'
        ',,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert Comment.objects.filter(type=Comment.STRUCTURE_ERROR).count() == 0
    assert Metadata.objects.filter(dataset=structure.dataset).count() == 3

    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,resource1,,,,,,,,,,,,\n'
        ',,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    assert list(Comment.objects.filter(
        type=Comment.STRUCTURE_ERROR,
        content_type=ContentType.objects.get_for_model(structure),
    ).values_list('body', flat=True)) == [
       'Duomenų rinkinys "datasets/gov/ivpk/adp" jau egzistuoja.'
    ]
    assert Metadata.objects.filter(dataset=structure.dataset).count() == 0


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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
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
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
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
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert structure.dataset.metadata.first().average_level == 3.5
    assert Model.objects.get(metadata__uuid="1").metadata.first().average_level == 3
    assert Model.objects.get(metadata__uuid="2").metadata.first().average_level == 3.6


@pytest.mark.django_db
def test_uri_format(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '2,,,,City,,,,,,,,dct:City,,\n'
        '3,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '4,,,,Country,,,,,,,,https://example.com#Country,,\n'
        '5,,,,,id,integer,,,,5,open,https://example.com#id,Identifikatorius,\n'
        '6,,,,Continent,,,,,,,,dct.Continent,,\n'
        '7,,,,,id,integer,,,,5,open,dct.identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Model),
        object_id=Model.objects.get(metadata__uuid=2).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == []
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id=Property.objects.get(metadata__uuid=3).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == []
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Model),
        object_id=Model.objects.get(metadata__uuid=4).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == []
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id=Property.objects.get(metadata__uuid=5).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == []
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Model),
        object_id=Model.objects.get(metadata__uuid=6).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == ['Neteisingas uri "dct.Continent" formatas.']
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id=Property.objects.get(metadata__uuid=7).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == ['Neteisingas uri "dct.identifier" formatas.']


@pytest.mark.django_db
def test_uri_prefix(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,City,,,,,,,,dcat:City,,\n'
        '3,,,,,id,integer,,,,5,open,dcat:identifier,Identifikatorius,\n'
        '4,,,,Country,,,,,,,,dct:Country,,\n'
        '5,,,,,id,integer,,,,5,open,dct:integer,Identifikatorius,\n'
        '6,,,,Continent,,,,,,,,spinta:Continent,,\n'
        '7,,,,,id,integer,,,,5,open,spinta:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Model),
        object_id=Model.objects.get(metadata__uuid=2).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == []
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id=Property.objects.get(metadata__uuid=3).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == []
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Model),
        object_id=Model.objects.get(metadata__uuid=4).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == []
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id=Property.objects.get(metadata__uuid=5).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == []
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Model),
        object_id=Model.objects.get(metadata__uuid=6).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == ['Prefiksas "spinta" duomenų rinkinyje neegzistuoja.']
    assert list(Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(Property),
        object_id=Property.objects.get(metadata__uuid=7).pk,
        type=Comment.STRUCTURE_ERROR
    ).values_list('body', flat=True)) == ['Prefiksas "spinta" duomenų rinkinyje neegzistuoja.']


@pytest.mark.django_db
def test_structure_export__prefixes(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,,,,,,prefix,spinta,,,,,https://github.com/atviriduomenys/spinta/issues/,,\n'
        '2,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '3,,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,\n'
        '4,,,,,,,dct,,,,,http://purl.org/dc/terms/,,'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk]))
    assert resp.text == (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\r\n'
        '1,,,,,,prefix,spinta,,,,,https://github.com/atviriduomenys/spinta/issues/,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '2,datasets/gov/ivpk/adp,,,,,,,,,,,,,\r\n'
        '3,,,,,,prefix,dcat,,,,,http://www.w3.org/ns/dcat#,,\r\n'
        '4,,,,,,,dct,,,,,http://purl.org/dc/terms/,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
    )


@pytest.mark.django_db
def test_structure_export__models_and_props(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\n'
        '4,,,,Licence,,,id,,page(id),,,,Licence,\n'
        '5,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '6,,,,,title,string,,,,2,open,dct:title,,\n'
        ',,,,,,,,,,,,,,\n'
        '7,,,,Catalog,,,id,,,,,,Catalog,\n'
        '8,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk]))
    assert resp.text == (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\r\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\r\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\r\n'
        '4,,,,Licence,,,id,,page(id),,,,Licence,\r\n'
        '5,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\r\n'
        '6,,,,,title,string,,,,2,open,dct:title,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '7,,,,Catalog,,,id,,,,,,Catalog,\r\n'
        '8,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\r\n'
        ',,,,,,,,,,,,,,\r\n'
    )


@pytest.mark.django_db
def test_structure_export__base_model(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\n'
        '4,,,,Base,,,,,,,,,,\n'
        '5,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,,,,,,,,,,\n'
        '6,,,Base,,,,,,,,,,,\n'
        '7,,,,Catalog,,,,,,,,,,\n'
        '8,,,,,title,string,,,,2,open,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk]))
    assert resp.text == (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\r\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\r\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\r\n'
        '4,,,,Base,,,,,,,,,,\r\n'
        '5,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '6,,,Base,,,,,,,,,,,\r\n'
        '7,,,,Catalog,,,,,,,,,,\r\n'
        '8,,,,,title,string,,,,2,open,dct:title,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
    )


@pytest.mark.django_db
def test_structure_export__property_ref(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\n'
        '4,,,,Country,,,,,,,,,,\n'
        '5,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '6,,,,,title,string,,,,5,open,dct:title,,\n'
        '7,,,,,continent,ref,Continent[id],,,5,open,dct:continent,,\n'
        '8,,,,Continent,,,,,,,,,,\n'
        '9,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk]))
    assert resp.text == (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\r\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\r\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\r\n'
        '4,,,,Country,,,,,,,,,,\r\n'
        '5,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\r\n'
        '6,,,,,title,string,,,,5,open,dct:title,,\r\n'
        '7,,,,,continent,ref,Continent[id],,,5,open,dct:continent,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '8,,,,Continent,,,,,,,,,,\r\n'
        '9,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\r\n'
        ',,,,,,,,,,,,,,\r\n'
    )


@pytest.mark.django_db
def test_structure_export__model_ref(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\n'
        '4,,,,Country,,,"id, title",,,,,,,\n'
        '5,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '6,,,,,title,string,,,,5,open,dct:title,,\n'
        '7,,,,,continent,ref,Continent,,,5,open,dct:continent,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk]))
    assert resp.text == (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\r\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\r\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\r\n'
        '4,,,,Country,,,"id, title",,,,,,,\r\n'
        '5,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\r\n'
        '6,,,,,title,string,,,,5,open,dct:title,,\r\n'
        '7,,,,,continent,ref,Continent,,,5,open,dct:continent,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
    )


@pytest.mark.django_db
def test_structure_export__comments(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\n'
        '4,,,,Country,,,,,,,,,,\n'
        '5,,,,,,comment,type,,,,open,,Model comment,\n'
        '6,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '7,,,,,,comment,type,,,,open,,Property comment,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk]))
    assert resp.text == (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\r\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\r\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '3,,resource,,,,,,http://www.example.com,,,,,,\r\n'
        '4,,,,Country,,,,,,,,,,\r\n'
        '5,,,,,,comment,type,,,,open,,Model comment,\r\n'
        '6,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\r\n'
        '7,,,,,,comment,type,,,,open,,Property comment,\r\n'
        ',,,,,,,,,,,,,,\r\n'
    )


@pytest.mark.django_db
def test_structure_export__enums(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '3,,,,,,enum,Size,,SMALL,,,,,\n'
        '4,,,,,,,,,MEDIUM,,,,,\n'
        '5,,,,,,,,,BIG,,,,,\n'
        '6,,resource,,,,,,http://www.example.com,,,,,,\n'
        '7,,,,City,,,,,,,,,,\n'
        '8,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '9,,,,,size,Size,,,,5,open,dct:size,,\n'
        '10,,,,,type,string,,,,5,open,dct:type,,\n'
        '11,,,,,,enum,Type,,CREATED,,,,,\n'
        '12,,,,,,,,,MODIFIED,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk]))
    assert resp.text == (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\r\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\r\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '3,,,,,,enum,Size,,SMALL,,,,,\r\n'
        '4,,,,,,,,,MEDIUM,,,,,\r\n'
        '5,,,,,,,,,BIG,,,,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '6,,resource,,,,,,http://www.example.com,,,,,,\r\n'
        '7,,,,City,,,,,,,,,,\r\n'
        '8,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\r\n'
        '9,,,,,size,Size,,,,5,open,dct:size,,\r\n'
        '10,,,,,type,string,,,,5,open,dct:type,,\r\n'
        '11,,,,,,enum,Type,,CREATED,,,,,\r\n'
        '12,,,,,,,,,MODIFIED,,,,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
    )


@pytest.mark.django_db
def test_structure_export__params(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        '3,,,,,,param,country,,lt,,,,,\n'
        '4,,,,,,,,,lv,,,,,\n'
        '5,,,,,,,,,ee,,,,,\n'
        '6,,resource,,,,,,http://www.example.com,,,,,,\n'
        '7,,,,City,,,,,,,,,,\n'
        '8,,,,,,param,type,,created,,,,,\n'
        '9,,,,,,,,,modified,,,,,\n'
        '10,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        '11,,,,,type,string,,,,5,open,dct:type,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure-export", args=[structure.dataset.pk]))
    assert resp.text == (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\r\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,\r\n'
        '2,,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '3,,,,,,param,country,,lt,,,,,\r\n'
        '4,,,,,,,,,lv,,,,,\r\n'
        '5,,,,,,,,,ee,,,,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
        '6,,resource,,,,,,http://www.example.com,,,,,,\r\n'
        '7,,,,City,,,,,,,,,,\r\n'
        '8,,,,,,param,type,,created,,,,,\r\n'
        '9,,,,,,,,,modified,,,,,\r\n'
        '10,,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\r\n'
        '11,,,,,type,string,,,,5,open,dct:type,,\r\n'
        ',,,,,,,,,,,,,,\r\n'
    )


@pytest.mark.django_db
def test_import_structure_with_wrong_datasets_name(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',datasets/gov/ivpk/adp/ššš,,,,,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )

    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    metadata = Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset)
    )
    assert metadata.count() == 0
    comments = Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(structure),
        object_id=structure.pk
    )
    assert comments.count() == 1
    assert 'kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės.' in comments[0].body

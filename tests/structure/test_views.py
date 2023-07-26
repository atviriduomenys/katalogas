import json
import uuid

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from unittest.mock import Mock, patch

from factory.django import FileField
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer
from pygments.lexers.special import TextLexer
from pygments.styles import get_style_by_name
from reversion.models import Version

from vitrina.cms.factories import FilerFileFactory
from vitrina.datasets.factories import DatasetStructureFactory, DatasetFactory
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.structure.factories import ModelFactory, MetadataFactory, PropertyFactory, EnumFactory, EnumItemFactory, \
    PrefixFactory, ParamItemFactory, ParamFactory
from vitrina.structure.models import Metadata, Enum, EnumItem, Param
from vitrina.structure.services import create_structure_objects
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_model_data(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_data': [
                {
                    '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
                    'prop_1': "test 1",
                    'prop_2': 1
                },
                {
                    '_id': '5bfd5a54-0ded-4803-9363-349f6e1b4523',
                    'prop_1': "test 2",
                    'prop_2': 2
                }
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse('model-data', args=[dataset.pk, model.name]))
        assert resp.context['headers'] == ['_id', 'prop_1', 'prop_2']
        assert resp.context['properties'] == {
            'prop_1': prop_1,
            'prop_2': prop_2
        }
        assert resp.context['tags'] == []
        assert resp.context['select'] == 'select(*)'
        assert resp.context['selected_cols'] == ['_id', 'prop_1', 'prop_2']


@pytest.mark.django_db
def test_model_data_select(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_data': [
                {'prop_1': 'test 1'},
                {'prop_1': 'test 2'}
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse('model-data', args=[dataset.pk, model.name]) + "?select(prop_1)")
        assert resp.context['headers'] == ['prop_1']
        assert resp.context['tags'] == []
        assert resp.context['select'] == 'select(prop_1)'
        assert resp.context['selected_cols'] == ['prop_1']


@pytest.mark.django_db
def test_model_data_sort(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_data': [
                {'prop_1': 'test 2'},
                {'prop_1': 'test 1'},
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse('model-data', args=[dataset.pk, model.name]) + "?select(prop_1)&sort(-prop_1)")
        assert resp.context['headers'] == ['prop_1']
        assert resp.context['tags'] == ['sort(-prop_1)']
        assert resp.context['select'] == 'select(prop_1)'
        assert resp.context['selected_cols'] == ['prop_1']


@pytest.mark.django_db
@pytest.mark.parametrize("operator", ['=', '<' '>' '<=', '>='])
def test_model_data_with_compare_operators(app: DjangoTestApp, operator: str):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_data': [
                {'prop_2': 2},
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse('model-data', args=[dataset.pk, model.name]) + f"?select(prop_2)&prop_2{operator}2")
        assert resp.context['headers'] == ['prop_2']
        assert resp.context['tags'] == [f'prop_2{operator}2']
        assert resp.context['select'] == 'select(prop_2)'
        assert resp.context['selected_cols'] == ['prop_2']


@pytest.mark.django_db
@pytest.mark.parametrize("operator", ['contains', 'startswith', 'endswith'])
def test_model_data_with_string_operators(app: DjangoTestApp, operator: str):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_data': [
                {'prop_1': 'test 1'},
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse('model-data', args=[dataset.pk, model.name]) + f"?select(prop_1)&{operator}('test')")
        assert resp.context['headers'] == ['prop_1']
        assert resp.context['tags'] == [f"{operator}('test')"]
        assert resp.context['select'] == 'select(prop_1)'
        assert resp.context['selected_cols'] == ['prop_1']


@pytest.mark.django_db
def test_object_data(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
            'prop_1': "test 1",
            'prop_2': 1
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse('object-data', args=[
            dataset.pk,
            model.name,
            'c7d66fa2-a880-443d-8ab5-2ab7f9c79886'
        ]))
        assert resp.context['headers'] == ['_id', 'prop_1', 'prop_2']
        assert resp.context['properties'] == {
            'prop_1': prop_1,
            'prop_2': prop_2
        }


@pytest.mark.django_db
def test_structure_tab_from_dataset_detail(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(dataset.get_absolute_url())
    resp = resp.click(linkid='structure_tab')
    assert resp.request.path == reverse('dataset-structure', args=[dataset.pk])


@pytest.mark.django_db
def test_structure_tab_from_model_structure(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(model.get_absolute_url())
    resp = resp.click(linkid='structure_tab')
    assert resp.request.path == reverse('dataset-structure', args=[dataset.pk])


@pytest.mark.django_db
def test_structure_tab_from_property_structure(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(prop.get_absolute_url())
    resp = resp.click(linkid='structure_tab')
    assert resp.request.path == reverse('dataset-structure', args=[dataset.pk])


@pytest.mark.django_db
def test_structure_tab_from_model_data(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(model.get_data_url())
    resp = resp.click(linkid='structure_tab')
    assert resp.request.path == model.get_absolute_url()


@pytest.mark.django_db
def test_data_tab_from_dataset_detail(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(dataset.get_absolute_url())
    resp = resp.click(linkid='data_tab')
    assert resp.request.path == model.get_data_url()


@pytest.mark.django_db
def test_data_tab_from_dataset_structure(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(reverse('dataset-structure', args=[dataset.pk]))
    resp = resp.click(linkid='data_tab')
    assert resp.request.path == model.get_data_url()


@pytest.mark.django_db
def test_data_tab_from_model_structure(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(model.get_absolute_url())
    resp = resp.click(linkid='data_tab')
    assert resp.request.path == model.get_data_url()


@pytest.mark.django_db
def test_data_tab_from_property_structure(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(prop.get_absolute_url())
    resp = resp.click(linkid='data_tab')
    assert resp.request.path == model.get_data_url()


@pytest.mark.django_db
def test_data_tab_from_object_data(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(reverse('object-data', args=[dataset.pk, model.name, str(uuid.uuid4())]))
    resp = resp.click(linkid='data_tab')
    assert resp.request.path == model.get_data_url()


@pytest.mark.django_db
def test_private_model(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,private,dct:title,,\n'
        ',,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,private,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,private,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse('dataset-structure', args=[structure.dataset.pk]))
    assert list(resp.context['models'].values_list('metadata__name', flat=True)) == [
        'datasets/gov/ivpk/adp/Country'
    ]

    resp = app.get(reverse('model-structure', args=[structure.dataset.pk, 'City']), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_private_model_with_access(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,private,dct:title,,\n'
        ',,,,City,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,private,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,private,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.pk,
    )
    app.set_user(representative.user)

    resp = app.get(reverse('dataset-structure', args=[structure.dataset.pk]))
    assert list(resp.context['models'].values_list('metadata__name', flat=True)) == [
        'datasets/gov/ivpk/adp/City',
        'datasets/gov/ivpk/adp/Country'
    ]

    resp = app.get(reverse('model-structure', args=[structure.dataset.pk, 'City']))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_private_property(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,private,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse('model-structure', args=[structure.dataset.pk, 'Country']))
    assert list(resp.context['props'].values_list('metadata__name', flat=True)) == ['id']

    resp = app.get(reverse('property-structure', args=[
        structure.dataset.pk,
        'Country',
        'title'
    ]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_private_property_with_access(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,open,dct:identifier,Identifikatorius,\n'
        ',,,,,title,string,,,,5,private,dct:title,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.pk,
    )
    app.set_user(representative.user)

    resp = app.get(reverse('model-structure', args=[structure.dataset.pk, 'Country']))
    assert list(resp.context['props'].values_list('metadata__name', flat=True)) == ['id', 'title']

    resp = app.get(reverse('property-structure', args=[
        structure.dataset.pk,
        'Country',
        'title'
    ]), expect_errors=True)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_private_comment(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,\n'
        ',,,,,,comment,type,,,,public,,Public comment,\n'
        ',,,,,,comment,type,,,,private,,Private comment,\n'
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

    resp = app.get(reverse('model-structure', args=[structure.dataset.pk, 'Country']))
    assert sorted([comment.body for comment, _ in resp.context['comments']]) == [
        'Public comment'
    ]


@pytest.mark.django_db
def test_private_comment_with_access(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,access,uri,title,description\n'
        ',,,,,,prefix,dct,,,,,http://purl.org/dc/terms/,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,\n'
        ',,,,,,comment,type,,,,public,,Public comment,\n'
        ',,,,,,comment,type,,,,private,,Private comment,\n'
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

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.pk,
    )
    app.set_user(representative.user)

    resp = app.get(reverse('model-structure', args=[structure.dataset.pk, 'Country']))
    assert sorted([comment.body for comment, _ in resp.context['comments']]) == [
        'Private comment',
        'Public comment',
    ]


@pytest.mark.django_db
def test_getall(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_data': [
                {
                    '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
                    'prop_1': "test 1",
                    'prop_2': 1
                },
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse('getall-api', args=[dataset.pk, model.name]))
        assert resp.context['tabs'] == {
            'http': {
                'name': 'HTTP',
                'query': highlight(
                    "https://get.data.gov.lt/test/dataset/TestModel",
                    TextLexer(), HtmlFormatter()
                )
            },
            'httpie': {
                'name': 'HTTPie',
                'query': highlight(
                    'http GET "https://get.data.gov.lt/test/dataset/TestModel"',
                    TextLexer(), HtmlFormatter()
                )
            },
            'curl': {
                'name': 'curl',
                'query': highlight(
                    'curl "https://get.data.gov.lt/test/dataset/TestModel"',
                    TextLexer(), HtmlFormatter()
                )
            }
        }
        assert resp.context['response'] == highlight(
            json.dumps({
                '_data': [
                    {
                        '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
                        'prop_1': "test 1",
                        'prop_2': 1
                    },
                ]
            }, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name('friendly'), noclasses=True)
        )


@pytest.mark.django_db
def test_getall_with_query(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_data': [
                {
                    '_id': '5bfd5a54-0ded-4803-9363-349f6e1b4523',
                    'prop_2': 2
                },
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get("%s%s" % (
            reverse('getall-api', args=[dataset.pk, model.name]),
            "?select(_id,prop_2)&sort(-prop2)"
        ))
        assert resp.context['tabs'] == {
            'http': {
                'name': 'HTTP',
                'query': highlight(
                    "https://get.data.gov.lt/test/dataset/TestModel?select(_id,prop_2)&sort(-prop2)",
                    TextLexer(), HtmlFormatter()
                )
            },
            'httpie': {
                'name': 'HTTPie',
                'query': highlight(
                    'http GET "https://get.data.gov.lt/test/dataset/TestModel?select(_id,prop_2)&sort(-prop2)"',
                    TextLexer(), HtmlFormatter()
                )
            },
            'curl': {
                'name': 'curl',
                'query': highlight(
                    'curl "https://get.data.gov.lt/test/dataset/TestModel?select(_id,prop_2)&sort(-prop2)"',
                    TextLexer(), HtmlFormatter()
                )
            }
        }
        assert resp.context['response'] == highlight(
            json.dumps({
                '_data': [
                    {
                        '_id': '5bfd5a54-0ded-4803-9363-349f6e1b4523',
                        'prop_2': 2
                    },
                ]
            }, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name('friendly'), noclasses=True)
        )


@pytest.mark.django_db
def test_getone(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
            'prop_1': "test 1",
            'prop_2': 1
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse('getone-api', args=[dataset.pk, model.name, "c7d66fa2-a880-443d-8ab5-2ab7f9c79886"]))
        assert resp.context['tabs'] == {
            'http': {
                'name': 'HTTP',
                'query': highlight(
                    "https://get.data.gov.lt/test/dataset/TestModel/c7d66fa2-a880-443d-8ab5-2ab7f9c79886",
                    TextLexer(), HtmlFormatter()
                )
            },
            'httpie': {
                'name': 'HTTPie',
                'query': highlight(
                    'http GET "https://get.data.gov.lt/test/dataset/TestModel/c7d66fa2-a880-443d-8ab5-2ab7f9c79886"',
                    TextLexer(), HtmlFormatter()
                )
            },
            'curl': {
                'name': 'curl',
                'query': highlight(
                    'curl "https://get.data.gov.lt/test/dataset/TestModel/c7d66fa2-a880-443d-8ab5-2ab7f9c79886"',
                    TextLexer(), HtmlFormatter()
                )
            }
        }
        assert resp.context['response'] == highlight(
            json.dumps({
                '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
                'prop_1': "test 1",
                'prop_2': 1
            }, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name('friendly'), noclasses=True)
        )


@pytest.mark.django_db
def test_changes(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name='prop_1',
        type='string',
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name='prop_2',
        type='integer'
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_data': [
                {
                    '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
                    '_op': 'insert',
                    'prop_1': "test 1",
                    'prop_2': 1
                }
            ]
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        resp = app.get(reverse('changes-api', args=[dataset.pk, model.name]))
        assert resp.context['tabs'] == {
            'http': {
                'name': 'HTTP',
                'query': highlight(
                    "https://get.data.gov.lt/test/dataset/TestModel/:changes",
                    TextLexer(), HtmlFormatter()
                )
            },
            'httpie': {
                'name': 'HTTPie',
                'query': highlight(
                    'http GET "https://get.data.gov.lt/test/dataset/TestModel/:changes"',
                    TextLexer(), HtmlFormatter()
                )
            },
            'curl': {
                'name': 'curl',
                'query': highlight(
                    'curl "https://get.data.gov.lt/test/dataset/TestModel/:changes"',
                    TextLexer(), HtmlFormatter()
                )
            }
        }
        assert resp.context['response'] == highlight(
            json.dumps({
                '_data': [
                    {
                        '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
                        '_op': 'insert',
                        'prop_1': "test 1",
                        'prop_2': 1
                    },
                ]
            }, indent=2, ensure_ascii=False),
            JsonLexer(),
            HtmlFormatter(style=get_style_by_name('friendly'), noclasses=True)
        )


@pytest.mark.django_db
def test_api_tab_from_model_data(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(reverse('model-data', args=[dataset.pk, model.name]))
    resp = resp.click(linkid='api_tab')
    assert resp.request.path == model.get_api_url()


@pytest.mark.django_db
def test_api_tab_from_model_data_with_query(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get("%s%s" % (
        reverse('model-data', args=[dataset.pk, model.name]),
        "?select(prop)"
    ))
    resp = resp.click(linkid='api_tab')
    assert resp.request.path_qs == "%s%s" % (
        model.get_api_url(),
        "?select(prop)"
    )


@pytest.mark.django_db
def test_api_tab_from_object_data(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    _id = str(uuid.uuid4())
    resp = app.get(reverse('object-data', args=[dataset.pk, model.name, _id]))
    resp = resp.click(linkid='api_tab')
    assert resp.request.path == reverse('getone-api', args=[dataset.pk, model.name, _id])


@pytest.mark.django_db
def test_data_tab_from_getone(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    _id = str(uuid.uuid4())
    resp = app.get(reverse('getone-api', args=[dataset.pk, model.name, _id]))
    resp = resp.click(linkid='data_tab')
    assert resp.request.path == reverse('object-data', args=[dataset.pk, model.name, _id])


@pytest.mark.django_db
def test_data_tab_from_getall(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get(reverse('getall-api', args=[dataset.pk, model.name]))
    resp = resp.click(linkid='data_tab')
    assert resp.request.path == reverse('model-data', args=[dataset.pk, model.name])


@pytest.mark.django_db
def test_data_tab_from_getall_with_query(app: DjangoTestApp):
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.get("%s%s" % (
        reverse('getall-api', args=[dataset.pk, model.name]),
        "?select(prop)"
    ))
    resp = resp.click(linkid='data_tab')
    assert resp.request.path_qs == "%s%s" % (
        model.get_data_url(),
        "?select(prop)"
    )


@pytest.mark.django_db
def test_property_enum_item_create__string(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('enum-create', args=[dataset.pk, model.name, prop.name])).forms['enum-form']
    form['value'] = "test"
    form['source'] = "TEST"
    form['access'] = Metadata.OPEN
    form['title'] = 'Test value'
    form['description'] = 'For testing'
    resp = form.submit()

    assert resp.url == prop.get_absolute_url()
    assert Enum.objects.filter(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk
    ).count() == 1
    assert list(EnumItem.objects.filter(
        enum__content_type=ContentType.objects.get_for_model(prop),
        enum__object_id=prop.pk
    ).values(
        'metadata__prepare',
        'metadata__source',
        'metadata__access',
        'metadata__title',
        'metadata__description'
    )) == [
        {
            'metadata__prepare': '"test"',
            'metadata__source': "TEST",
            'metadata__access': Metadata.OPEN,
            'metadata__title': "Test value",
            'metadata__description': "For testing"
        }
    ]


@pytest.mark.django_db
def test_property_enum_item_create__integer(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='integer',
    )

    form = app.get(reverse('enum-create', args=[dataset.pk, model.name, prop.name])).forms['enum-form']
    form['value'] = 1
    form['source'] = "TEST"
    form['access'] = Metadata.OPEN
    form['title'] = 'Test value'
    form['description'] = 'For testing'
    resp = form.submit()

    assert resp.url == prop.get_absolute_url()
    assert Enum.objects.filter(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk
    ).count() == 1
    assert list(EnumItem.objects.filter(
        enum__content_type=ContentType.objects.get_for_model(prop),
        enum__object_id=prop.pk
    ).values(
        'metadata__prepare',
        'metadata__source',
        'metadata__access',
        'metadata__title',
        'metadata__description'
    )) == [
        {
            'metadata__prepare': '1',
            'metadata__source': "TEST",
            'metadata__access': Metadata.OPEN,
            'metadata__title': "Test value",
            'metadata__description': "For testing"
        }
    ]
    assert Version.objects.get_for_object(prop).count() == 1
    assert Version.objects.get_for_object(prop).first().revision.user == user


@pytest.mark.django_db
def test_property_enum_item_create__integer_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='integer',
    )

    form = app.get(reverse('enum-create', args=[dataset.pk, model.name, prop.name])).forms['enum-form']
    form['value'] = "invalid"
    form['source'] = "TEST"
    form['access'] = Metadata.OPEN
    form['title'] = 'Test value'
    form['description'] = 'For testing'
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [["Reikšmė turi būti integer tipo."]]


@pytest.mark.django_db
def test_property_enum_item_update(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='integer',
    )

    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk
    )
    enum_item = EnumItemFactory(enum=enum)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title='Test value',
        description='For testing',
        prepare='1',
        access=Metadata.OPEN,
        source="TEST",
    )

    form = app.get(reverse('enum-update', args=[
        dataset.pk,
        model.name,
        prop.name,
        enum_item.pk
    ])).forms['enum-form']
    form['access'] = Metadata.PUBLIC
    form['title'] = 'Test value (updated)'
    resp = form.submit()

    assert resp.url == prop.get_absolute_url()
    assert Enum.objects.filter(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk
    ).count() == 1
    assert list(EnumItem.objects.filter(
        enum__content_type=ContentType.objects.get_for_model(prop),
        enum__object_id=prop.pk
    ).values(
        'metadata__prepare',
        'metadata__source',
        'metadata__access',
        'metadata__title',
        'metadata__description'
    )) == [
        {
            'metadata__prepare': '1',
            'metadata__source': "TEST",
            'metadata__access': Metadata.PUBLIC,
            'metadata__title': "Test value (updated)",
            'metadata__description': "For testing"
        }
    ]
    assert Version.objects.get_for_object(prop).count() == 1
    assert Version.objects.get_for_object(prop).first().revision.user == user


@pytest.mark.django_db
def test_property_enum_item_delete(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='integer',
    )

    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk
    )
    enum_item = EnumItemFactory(enum=enum)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title='Test value',
        description='For testing',
        prepare='1',
        access=Metadata.OPEN,
        source="TEST",
    )

    resp = app.get(reverse('enum-delete', args=[
        dataset.pk,
        model.name,
        prop.name,
        enum_item.pk
    ]))

    assert resp.url == prop.get_absolute_url()
    assert EnumItem.objects.filter(pk=enum_item.pk).count() == 0
    assert Metadata.objects.filter(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk
    ).count() == 0
    assert Version.objects.get_for_object(prop).count() == 1
    assert Version.objects.get_for_object(prop).first().revision.user == user


@pytest.mark.django_db
def test_model_create_with_lowercase_first_name_letter(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse('model-create', args=[dataset.pk])).forms['model-form']
    form['name'] = "invalidName"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        "Pirmas kodinio pavadinimo simbolis turi būti didžioji raidė."
    ]]


@pytest.mark.django_db
def test_model_create_with_number_as_first_name_letter(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse('model-create', args=[dataset.pk])).forms['model-form']
    form['name'] = "1nvalidName"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        "Pirmas kodinio pavadinimo simbolis turi būti didžioji raidė."
    ]]


@pytest.mark.django_db
def test_model_create_with_special_symbol_in_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse('model-create', args=[dataset.pk])).forms['model-form']
    form['name'] = "Invalid_name1"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        "Pavadinime gali būti didžiosos/mažosios raidės ir skaičiai, jokie kiti simboliai negalimi."
    ]]


@pytest.mark.django_db
def test_model_create_with_invalid_prepare(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse('model-create', args=[dataset.pk])).forms['model-form']
    form['name'] = "Model"
    form['prepare'] = 'sort(id)'
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        'Duomenų filtre nurodytas modelyje neegzistuojantis laukas: "id".'
    ]]


@pytest.mark.django_db
def test_model_create_with_invalid_uri(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse('model-create', args=[dataset.pk])).forms['model-form']
    form['name'] = "Model"
    form['uri'] = 'dcat:invalid:format'
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        'Nevalidus uri "dcat:invalid:format" formatas.'
    ]]


@pytest.mark.django_db
def test_model_create_with_invalid_uri_prefix(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse('model-create', args=[dataset.pk])).forms['model-form']
    form['name'] = "Model"
    form['uri'] = 'dcat:invalid'
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        'Neatpažintas "dcat" prefiksas.'
    ]]


@pytest.mark.django_db
def test_model_create(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    PrefixFactory(name="dcat")
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        uri="dcat:TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='integer',
    )

    form = app.get(reverse('model-create', args=[dataset.pk])).forms['model-form']
    form['name'] = "Model"
    form['uri'] = 'dcat:model'
    form['source'] = "MODEL"
    form['level'] = 3
    form['title'] = 'Test model'
    form['description'] = 'Model for testing'
    form['base'].force_value([model.pk])
    form['base_level'] = 4
    form['base_ref'].force_value([prop.pk])
    form['comment'] = 'Added Model'
    resp = form.submit()
    new_model = dataset.model_set.exclude(pk=model.pk).first()
    assert resp.url == new_model.get_absolute_url()
    assert new_model.metadata.count() == 1
    assert new_model.metadata.first().name == 'test/dataset/Model'
    assert new_model.metadata.first().uri == 'dcat:model'
    assert new_model.metadata.first().source == 'MODEL'
    assert new_model.metadata.first().level == 5
    assert new_model.metadata.first().level_given == 3
    assert new_model.metadata.first().title == 'Test model'
    assert new_model.metadata.first().description == 'Model for testing'

    assert new_model.base.model == model
    assert new_model.base.property_list.count() == 1
    assert new_model.base.property_list.first().property == prop
    assert new_model.base.metadata.first().level == 5
    assert new_model.base.metadata.first().level_given == 4
    assert new_model.base.metadata.first().name == 'test/dataset/TestModel'
    assert new_model.base.metadata.first().ref == 'prop'

    assert Version.objects.get_for_object(new_model).count() == 1
    assert Version.objects.get_for_object(new_model).first().revision.comment == 'Sukurtas "Model" modelis. Added Model'
    assert Version.objects.get_for_object(new_model).first().revision.user == user


@pytest.mark.django_db
def test_model_update(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    PrefixFactory(name="dcat")
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        uri="dcat:TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop1 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop1),
        object_id=prop1.pk,
        dataset=dataset,
        name='prop1',
        type='integer',
    )
    prop2 = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop2),
        object_id=prop2.pk,
        dataset=dataset,
        name='prop2',
        type='integer',
    )

    base_model = ModelFactory(dataset=dataset)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(base_model),
        object_id=base_model.pk,
        dataset=dataset,
        name="test/dataset/BaseModel"
    )

    form = app.get(reverse('model-update', args=[dataset.pk, model.name])).forms['model-form']
    form['name'] = "UpdatedModel"
    form['prepare'] = "sort(prop1)"
    form['ref'].force_value([prop2.pk, prop1.pk])
    form['base'].force_value([base_model.pk])
    form['comment'] = 'Updated Model'
    resp = form.submit()
    model.refresh_from_db()
    assert resp.url == model.get_absolute_url()
    assert model.metadata.count() == 1
    assert model.metadata.first().name == 'test/dataset/UpdatedModel'
    assert model.metadata.first().prepare == 'sort(prop1)'
    assert model.metadata.first().prepare_ast == {'args': [{'args': ['prop1'], 'name': 'bind'}], 'name': 'sort'}

    assert model.base.model == base_model
    assert model.base.metadata.first().name == 'test/dataset/BaseModel'
    assert model.base.metadata.first().ref == ''

    assert Version.objects.get_for_object(model).count() == 1
    assert Version.objects.get_for_object(model).first().revision.comment == \
           'Redaguotas "UpdatedModel" modelis. Updated Model'
    assert Version.objects.get_for_object(model).first().revision.user == user


@pytest.mark.django_db
def test_param_create_for_resource(app: DjangoTestApp):
    distribution = DatasetDistributionFactory(is_parameterized=True)
    dataset = distribution.dataset
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
    )
    app.set_user(representative.user)

    ct = ContentType.objects.get_for_model(distribution)
    form = app.get(reverse('param-create', args=[dataset.pk, ct.pk, distribution.pk])).forms['param-form']
    form['name'] = 'test'
    form['prepare'] = 'param'
    form['title'] = 'Test param'
    form['source'] = 'src'
    form['description'] = 'Param for testing'
    resp = form.submit()

    assert resp.url == distribution.get_absolute_url()
    assert list(distribution.params.values_list('name', flat=True)) == ['test']
    assert distribution.params.first().paramitem_set.count() == 1
    assert distribution.params.first().paramitem_set.first().metadata.first().name == 'test'
    assert distribution.params.first().paramitem_set.first().metadata.first().prepare == 'param'
    assert distribution.params.first().paramitem_set.first().metadata.first().title == 'Test param'
    assert distribution.params.first().paramitem_set.first().metadata.first().source == 'src'
    assert distribution.params.first().paramitem_set.first().metadata.first().description == 'Param for testing'


@pytest.mark.django_db
def test_param_create_for_model(app: DjangoTestApp):
    model = ModelFactory(is_parameterized=True)
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
    )
    app.set_user(representative.user)

    ct = ContentType.objects.get_for_model(model)
    form = app.get(reverse('param-create', args=[dataset.pk, ct.pk, model.pk])).forms['param-form']
    form['name'] = 'test'
    form['prepare'] = 'param'
    form['title'] = 'Test param'
    form['source'] = 'src'
    form['description'] = 'Param for testing'
    resp = form.submit()

    assert resp.url == model.get_absolute_url()
    assert list(model.params.values_list('name', flat=True)) == ['test']
    assert model.params.first().paramitem_set.count() == 1
    assert model.params.first().paramitem_set.first().metadata.first().name == 'test'
    assert model.params.first().paramitem_set.first().metadata.first().prepare == 'param'
    assert model.params.first().paramitem_set.first().metadata.first().title == 'Test param'
    assert model.params.first().paramitem_set.first().metadata.first().source == 'src'
    assert model.params.first().paramitem_set.first().metadata.first().description == 'Param for testing'
    assert Version.objects.get_for_object(model).count() == 1
    assert Version.objects.get_for_object(model).first().revision.user == representative.user


@pytest.mark.django_db
def test_param_update(app: DjangoTestApp):
    distribution = DatasetDistributionFactory(is_parameterized=True)
    dataset = distribution.dataset
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
    )
    app.set_user(representative.user)
    ct = ContentType.objects.get_for_model(distribution)
    param = ParamFactory(
        content_type=ct,
        object_id=distribution.pk
    )
    param_item = ParamItemFactory(param=param)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(param_item),
        object_id=param_item.pk,
        dataset=dataset,
        name="test",
        title='Test param',
        prepare='param'
    )

    form = app.get(reverse('param-update', args=[dataset.pk, param_item.pk])).forms['param-form']
    form['title'] = 'Updated test param'
    resp = form.submit()

    assert resp.url == distribution.get_absolute_url()
    assert distribution.params.first().paramitem_set.count() == 1
    assert distribution.params.first().paramitem_set.first().metadata.first().title == 'Updated test param'


@pytest.mark.django_db
def test_param_delete(app: DjangoTestApp):
    distribution = DatasetDistributionFactory(is_parameterized=True)
    dataset = distribution.dataset
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
    )
    app.set_user(representative.user)
    ct = ContentType.objects.get_for_model(distribution)
    param = ParamFactory(
        content_type=ct,
        object_id=distribution.pk
    )
    param_item = ParamItemFactory(param=param)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(param_item),
        object_id=param_item.pk,
        dataset=dataset,
        name="test",
        title='Test param',
        prepare='param'
    )

    resp = app.get(reverse('param-delete', args=[dataset.pk, param_item.pk]))
    assert resp.url == distribution.get_absolute_url()
    assert distribution.params.first().paramitem_set.count() == 0

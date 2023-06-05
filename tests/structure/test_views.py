import json
import uuid

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from unittest.mock import Mock, patch

from factory.django import FileField

from vitrina.cms.factories import FilerFileFactory
from vitrina.datasets.factories import DatasetStructureFactory
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.structure.factories import ModelFactory, MetadataFactory, PropertyFactory
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

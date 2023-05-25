import json

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from unittest.mock import Mock, patch

from vitrina.structure.factories import ModelFactory, MetadataFactory, PropertyFactory


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

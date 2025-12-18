import datetime
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

from vitrina.classifiers.models import Status
from vitrina.cms.factories import FilerFileFactory
from vitrina.datasets.factories import DatasetStructureFactory, DatasetFactory
from vitrina.orgs.factories import RepresentativeFactory, OrganizationFactory
from vitrina.orgs.models import Representative, Organization
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure.factories import ModelFactory, MetadataFactory, PropertyFactory, EnumFactory, EnumItemFactory, \
    PrefixFactory, ParamItemFactory, ParamFactory, BaseFactory, VersionFactory
from vitrina.structure.models import Metadata, Enum, EnumItem, Param, VersionType
from vitrina.structure.services import create_structure_objects
from vitrina.users.factories import UserFactory
from vitrina.structure.models import Version as _Version
from vitrina.utils import RevisionComment, RevisionSource


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
    resp = app.post(reverse('model-data-table', args=[dataset.pk, model.name]), {
        'data': json.dumps(data)
    })
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

    data = {
        '_data': [
            {'prop_1': 'test 1'},
            {'prop_1': 'test 2'}
        ]
    }
    resp = app.post(reverse(
        'model-data-table', args=[dataset.pk, model.name]), {
        'data': json.dumps(data),
        'query': "?select(prop_1)",
    })
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

    data = {
        '_data': [
            {'prop_1': 'test 2'},
            {'prop_1': 'test 1'},
        ]
    }
    resp = app.post(reverse(
        'model-data-table', args=[dataset.pk, model.name]), {
        'data': json.dumps(data),
        'query': "?select(prop_1)&sort(-prop_1)",
    })
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

    data = {
        '_data': [
            {'prop_2': 2},
        ]
    }
    resp = app.post(reverse(
        'model-data-table', args=[dataset.pk, model.name]), {
        'data': json.dumps(data),
        'query': f"?select(prop_2)&prop_2{operator}2",
    })
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

    data = {
        '_data': [
            {'prop_1': 'test 1'},
        ]
    }
    resp = app.post(reverse(
        'model-data-table', args=[dataset.pk, model.name]), {
        'data': json.dumps(data),
        'query': f"?select(prop_1)&{operator}('test')",
    })
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

    data = {
        '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
        'prop_1': "test 1",
        'prop_2': 1
    }
    resp = app.post(reverse(
        'object-data-table', args=[
            dataset.pk,
            model.name,
            'c7d66fa2-a880-443d-8ab5-2ab7f9c79886'
        ]), {
        'data': json.dumps(data),
    })
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
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        ',,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n'
        ',,,,,title,string,,,,5,,,private,,dct:title,,,\n'
        ',,,,City,,,,,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,,,private,dct:identifier,,Identifikatorius,,\n'
        ',,,,,title,string,,,,5,,,private,dct:title,,,,\n'
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
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        ',,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n'
        ',,,,,title,string,,,,5,,,private,dct:title,,,,\n'
        ',,,,City,,,,,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,,,private,dct:identifier,,Identifikatorius,,\n'
        ',,,,,title,string,,,,5,,,private,dct:title,,,,\n'
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
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        ',,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n'
        ',,,,,title,string,,,,5,,,private,dct:title,,,,\n'
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
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        ',,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n'
        ',,,,,title,string,,,,5,,,private,dct:title,,,,\n'
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
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        ',,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,,,,,\n'
        ',,,,,,comment,type,,,,,,public,,,Public comment,,\n'
        ',,,,,,comment,type,,,,,,private,,,Private comment,,\n'
        ',,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n'
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
    assert sorted([comment.body for comment, _, _ in resp.context['comments']]) == [
        'Public comment'
    ]


@pytest.mark.django_db
def test_private_comment_with_access(app: DjangoTestApp):
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        ',,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,,\n'
        ',,,,,,comment,type,,,,public,,,,,Public comment,,\n'
        ',,,,,,comment,type,,,,private,,,,,Private comment,,\n'
        ',,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n'
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
    assert sorted([comment.body for comment, _, _ in resp.context['comments']]) == [
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
                    f"{SPINTA_SERVER_URL}/test/dataset/TestModel",
                    TextLexer(), HtmlFormatter()
                )
            },
            'httpie': {
                'name': 'HTTPie',
                'query': highlight(
                    f'http GET "{SPINTA_SERVER_URL}/test/dataset/TestModel"',
                    TextLexer(), HtmlFormatter()
                )
            },
            'curl': {
                'name': 'curl',
                'query': highlight(
                    f'curl "{SPINTA_SERVER_URL}/test/dataset/TestModel"',
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
            HtmlFormatter(style=get_style_by_name('borland'), noclasses=True)
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
                    f"{SPINTA_SERVER_URL}/test/dataset/TestModel?select(_id,prop_2)&sort(-prop2)",
                    TextLexer(), HtmlFormatter()
                )
            },
            'httpie': {
                'name': 'HTTPie',
                'query': highlight(
                    f'http GET "{SPINTA_SERVER_URL}/test/dataset/TestModel?select(_id,prop_2)&sort(-prop2)"',
                    TextLexer(), HtmlFormatter()
                )
            },
            'curl': {
                'name': 'curl',
                'query': highlight(
                    f'curl "{SPINTA_SERVER_URL}/test/dataset/TestModel?select(_id,prop_2)&sort(-prop2)"',
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
            HtmlFormatter(style=get_style_by_name('borland'), noclasses=True)
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
                    f"{SPINTA_SERVER_URL}/test/dataset/TestModel/c7d66fa2-a880-443d-8ab5-2ab7f9c79886",
                    TextLexer(), HtmlFormatter()
                )
            },
            'httpie': {
                'name': 'HTTPie',
                'query': highlight(
                    f'http GET "{SPINTA_SERVER_URL}/test/dataset/TestModel/c7d66fa2-a880-443d-8ab5-2ab7f9c79886"',
                    TextLexer(), HtmlFormatter()
                )
            },
            'curl': {
                'name': 'curl',
                'query': highlight(
                    f'curl "{SPINTA_SERVER_URL}/test/dataset/TestModel/c7d66fa2-a880-443d-8ab5-2ab7f9c79886"',
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
            HtmlFormatter(style=get_style_by_name('borland'), noclasses=True)
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
                    f"{SPINTA_SERVER_URL}/test/dataset/TestModel/:changes",
                    TextLexer(), HtmlFormatter()
                )
            },
            'httpie': {
                'name': 'HTTPie',
                'query': highlight(
                    f'http GET "{SPINTA_SERVER_URL}/test/dataset/TestModel/:changes"',
                    TextLexer(), HtmlFormatter()
                )
            },
            'curl': {
                'name': 'curl',
                'query': highlight(
                    f'curl "{SPINTA_SERVER_URL}/test/dataset/TestModel/:changes"',
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
            HtmlFormatter(style=get_style_by_name('borland'), noclasses=True)
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

    resp = app.post(reverse('enum-delete', args=[
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

    url = reverse('model-create', args=[dataset.pk])
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="model-create",
        http_method="POST",
        path=url,
        args=(),
        kwargs={"pk": dataset.pk}
    )
    form = app.get(url).forms['model-form']
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
    version = (Version.objects.get_for_object(new_model).select_related("revision").first())
    assert version.revision.comment == revision_comment.to_json()
    assert version.revision.user == user


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
    kwargs_dict = {"pk": dataset.pk, "model": model.name}
    url = reverse('model-update', kwargs=kwargs_dict)
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="model-update",
        http_method="POST",
        path=url,
        args=(),
        kwargs=kwargs_dict
    )
    form = app.get(url).forms['model-form']
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
    version = Version.objects.get_for_object(model).select_related("revision").first()
    assert version.revision.comment == revision_comment.to_json()
    assert version.revision.user == user


@pytest.mark.django_db
def test_param_create_for_resource(app: DjangoTestApp):
    distribution = DatasetDistributionFactory(is_parameterized=True)
    dataset = distribution.dataset
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.OPEN_DATA_MANAGER
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
        role=Representative.OPEN_DATA_MANAGER
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
        role=Representative.OPEN_DATA_MANAGER
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
        role=Representative.OPEN_DATA_MANAGER
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

    resp = app.post(reverse('param-delete', args=[dataset.pk, param_item.pk]))
    assert resp.url == distribution.get_absolute_url()
    assert distribution.params.first().paramitem_set.count() == 0


@pytest.mark.django_db
def test_new_version_with_released_date_earlier_than_two_weeks(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today()
    form['version_type'] = "MAJOR"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        "Versija gali įsigalioti ne anksčiau kaip po 2 savaičių."
    ]]


@pytest.mark.django_db
def test_new_version_with_released_date_earlier_than_last_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form.submit()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    resp = form.submit()

    assert list(resp.context['form'].errors.values()) == [[
        "Versija negali įsigalioti anksčiau už praėjusią versiją."
    ]]


@pytest.mark.django_db
def test_new_version_with_new_structure(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    assert _Version.objects.count() == 1
    assert _Version.objects.first().dataset == dataset
    assert sorted(list(_Version.objects.first().metadataversion_set.values_list(
        'metadata__pk', flat=True
    ))) == sorted([
        dataset_meta.pk,
        model_meta.pk,
        prop_meta.pk
    ])


@pytest.mark.django_db
def test_new_version_with_updated_structure__dataset_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    dataset_meta.name = "test/dataset1"
    dataset_meta.draft = True
    dataset_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(dataset),
        metadata__object_id=dataset.pk
    ).first().name == 'test/dataset'
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == dataset
    assert new_version.metadataversion_set.first().name == 'test/dataset1'


@pytest.mark.django_db
def test_new_version_with_updated_structure__model_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    model_meta.name = "test/dataset/TestModel1"
    model_meta.draft = True
    model_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [model_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(model),
        metadata__object_id=model.pk
    ).first().name == "test/dataset/TestModel"
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == model
    assert new_version.metadataversion_set.first().name == "test/dataset/TestModel1"


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    prop_meta.name = "prop1"
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [prop_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(prop),
        metadata__object_id=prop.pk
    ).first().name == "prop"
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == prop
    assert new_version.metadataversion_set.first().name == 'prop1'


@pytest.mark.django_db
def test_new_version_with_updated_structure__model_base(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    base_model = ModelFactory(dataset=dataset)
    base_model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(base_model),
        object_id=base_model.pk,
        dataset=dataset,
        name="test/dataset/BaseModel"
    )
    base = BaseFactory(model=base_model)
    base_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(base),
        object_id=base.pk,
        dataset=dataset,
        name="test/dataset/BaseModel"
    )
    model.base = base
    model.save()
    model_meta.draft = True
    model_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [model_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(model),
        metadata__object_id=model.pk
    ).first().base is None
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == model
    assert new_version.metadataversion_set.first().base == base


@pytest.mark.django_db
def test_new_version_with_updated_structure__model_ref(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    model_meta.ref = 'id'
    model_meta.draft = True
    model_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [model_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(model),
        metadata__object_id=model.pk
    ).first().ref is None
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == model
    assert new_version.metadataversion_set.first().ref == 'id'


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_type(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    prop_meta.type = 'integer'
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [prop_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(prop),
        metadata__object_id=prop.pk
    ).first().type == 'string'
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == prop
    assert new_version.metadataversion_set.first().type == 'integer'


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_ref(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    prop_meta.ref = "test/dataset/TestModel"
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [prop_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(prop),
        metadata__object_id=prop.pk
    ).first().ref is None
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == prop
    assert new_version.metadataversion_set.first().ref == "test/dataset/TestModel"


@pytest.mark.django_db
def test_new_version_with_updated_structure__model_level(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        level_given=3
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    model_meta.level_given = 5
    model_meta.draft = True
    model_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [model_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(model),
        metadata__object_id=model.pk
    ).first().level_given == 3
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == model
    assert new_version.metadataversion_set.first().level_given == 5


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_level(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
        level_given=3
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    prop_meta.level_given = 5
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [prop_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(prop),
        metadata__object_id=prop.pk
    ).first().level_given == 3
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == prop
    assert new_version.metadataversion_set.first().level_given == 5


@pytest.mark.django_db
def test_new_version_with_updated_structure__property_access(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
        access=3
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    prop_meta.access = 5
    prop_meta.draft = True
    prop_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [prop_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(prop),
        metadata__object_id=prop.pk
    ).first().access == 3
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == prop
    assert new_version.metadataversion_set.first().access == 5


@pytest.mark.django_db
def test_new_version_with_updated_structure__enum_prepare(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
        access=3
    )
    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk
    )
    enum_item = EnumItemFactory(enum=enum)
    enum_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title='Test value',
        description='For testing',
        prepare='1',
        access=Metadata.OPEN,
        source="TEST",
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk, enum_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    enum_meta.prepare = '2'
    enum_meta.draft = True
    enum_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [enum_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(enum_item),
        metadata__object_id=enum_item.pk
    ).first().prepare == '1'
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == enum_item
    assert new_version.metadataversion_set.first().prepare == '2'


@pytest.mark.django_db
def test_new_version_with_updated_structure__enum_source(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    model_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )
    dataset_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    prop_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
        access=3
    )
    enum = EnumFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk
    )
    enum_item = EnumItemFactory(enum=enum)
    enum_meta = MetadataFactory(
        content_type=ContentType.objects.get_for_model(enum_item),
        object_id=enum_item.pk,
        dataset=dataset,
        title='Test value',
        description='For testing',
        prepare='1',
        access=Metadata.OPEN,
        source="TEST",
    )

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=14)
    form['version_type'] = "MAJOR"
    form['metadata'] = [dataset_meta.pk, model_meta.pk, prop_meta.pk, enum_meta.pk]
    form['description'] = "Add new structure to version"
    form.submit()

    enum_meta.source = 'TEST1'
    enum_meta.draft = True
    enum_meta.save()

    form = app.get(reverse('version-create', args=[dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = [enum_meta.pk]
    form['description'] = "Update structure version"
    form.submit()

    assert dataset.dataset_version.count() == 2
    old_version = dataset.dataset_version.order_by('created').first()
    assert old_version.metadataversion_set.filter(
        metadata__content_type=ContentType.objects.get_for_model(enum_item),
        metadata__object_id=enum_item.pk
    ).first().source == 'TEST'
    new_version = dataset.dataset_version.order_by('-created').first()
    assert new_version.metadataversion_set.count() == 1
    assert new_version.metadataversion_set.first().metadata.object == enum_item
    assert new_version.metadataversion_set.first().source == 'TEST1'


@pytest.mark.django_db
def test_structure_tab_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse('dataset-structure', args=[dataset.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_structure_tab_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER,
    )
    app.set_user(user)
    response = app.get(reverse('dataset-structure', args=[dataset.pk]))
    assert response.context['dataset'] == dataset


@pytest.mark.django_db
def test_version_list_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    VersionFactory(dataset=dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse('version-list', args=[dataset.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_version_list_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER
    )
    app.set_user(user)
    response = app.get(reverse('version-list', args=[dataset.pk]))
    assert list(response.context['versions']) == [version]


@pytest.mark.django_db
def test_version_detail_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse('version-detail', args=[dataset.pk, version.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_version_detail_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    version = VersionFactory(dataset=dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER
    )
    app.set_user(user)
    response = app.get(reverse('version-detail', args=[dataset.pk, version.pk]))
    assert response.context['version'] == version


@pytest.mark.django_db
def test_model_structure_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse('model-structure', args=[dataset.pk, model.name]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_model_structure_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER
    )
    app.set_user(user)
    response = app.get(reverse('model-structure', args=[dataset.pk, model.name]))
    assert response.context['model'] == model


@pytest.mark.django_db
def test_property_structure_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse('property-structure', args=[dataset.pk, model.name, prop.name]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_property_structure_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER
    )
    app.set_user(user)
    response = app.get(reverse('property-structure', args=[dataset.pk, model.name, prop.name]))
    assert response.context['prop'] == prop


@pytest.mark.django_db
def test_model_data_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse('model-data', args=[dataset.pk, model.name]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_model_data_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER
    )
    app.set_user(user)
    response = app.get(reverse('model-data', args=[dataset.pk, model.name]))
    assert response.context['model'] == model


@pytest.mark.django_db
def test_object_data_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse('object-data', args=[dataset.pk, model.name, "123456789"]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_object_data_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER
    )
    app.set_user(user)
    response = app.get(reverse('object-data', args=[dataset.pk, model.name, "123456789"]))
    assert response.context['model'] == model


@pytest.mark.django_db
def test_api_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse('getall-api', args=[dataset.pk, model.name]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_api_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
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
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER
    )
    app.set_user(user)
    response = app.get(reverse('getall-api', args=[dataset.pk, model.name]))
    assert response.context['model'] == model


@pytest.mark.django_db
def test_visibility_without_access(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,private,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,City,,,,,,,,protected,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,Province,,,,,,,,package,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,State,,,,,,,,public,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,,residence,string,,,,5,,public,open,dct:residence,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest))
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == [
        "datasets/gov/ivpk/adp/Province",
        "datasets/gov/ivpk/adp/State"
    ]

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "Country"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Country", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "City"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "City", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "City", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403


    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "Province"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200


    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "State"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "residence"]),
        expect_errors=True,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_model_visibility_with_manager_access(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,private,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,City,,,,,,,,protected,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,Province,,,,,,,,package,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,State,,,,,,,,public,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,,residence,string,,,,5,,public,open,dct:residence,,,,\n"
    )

    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest))
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    ct = ContentType.objects.get_for_model(structure.dataset)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=structure.dataset.pk,
        role=Representative.OPEN_DATA_MANAGER
    )
    app.set_user(representative.user)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == [
        "datasets/gov/ivpk/adp/City",
        "datasets/gov/ivpk/adp/Country",
        "datasets/gov/ivpk/adp/Province",
        "datasets/gov/ivpk/adp/State",
    ]
    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "Country"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Country", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "City"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "City", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "City", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "Province"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "State"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "residence"]),
        expect_errors=True,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_model_visibility_with_open_data_representative_access(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,private,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,City,,,,,,,,protected,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,Province,,,,,,,,package,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,State,,,,,,,,public,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,,residence,string,,,,5,,public,open,dct:residence,,,,\n"
    )
    organization = OrganizationFactory(kind=Organization.GOV)
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest))
    )
    structure.dataset.organization = organization
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)
    representative = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(structure.dataset.organization),
        object_id=structure.dataset.organization.pk,
        role=Representative.OPEN_DATA_MANAGER,
        #open_data_representative=True
    )
    app.set_user(representative.user)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == [
        "datasets/gov/ivpk/adp/Province",
        "datasets/gov/ivpk/adp/State",
    ]
    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "Country"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Country", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "City"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "City", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "City", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "Province"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "State"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 403

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "residence"]),
        expect_errors=True,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_model_visibility_with_information_system_representative_access(app: DjangoTestApp):
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,private,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,City,,,,,,,,protected,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,Province,,,,,,,,package,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,State,,,,,,,,public,,,,,,\n"
        ",,,,,id,integer,,,,5,,private,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,protected,open,dct:title,,,,\n"
        ",,,,,number,string,,,,5,,package,open,dct:number,,,,\n"
        ",,,,,residence,string,,,,5,,public,open,dct:residence,,,,\n"
    )
    organization = OrganizationFactory(kind=Organization.GOV)
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest))
    )
    structure.dataset.organization = organization
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    representative = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(structure.dataset.organization),
        object_id=structure.dataset.organization.pk,
        role=Representative.RESOURCE_MANAGER,
    )
    app.set_user(representative.user)

    resp = app.get(reverse("dataset-structure", args=[structure.dataset.pk]))
    assert list(resp.context["models"].values_list("metadata__name", flat=True)) == [
        "datasets/gov/ivpk/adp/City",
        "datasets/gov/ivpk/adp/Country",
        "datasets/gov/ivpk/adp/Province",
        "datasets/gov/ivpk/adp/State",
    ]
    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "Country"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Country", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "City"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "City", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "City", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "Province"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "Province", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("model-structure", args=[structure.dataset.pk, "State"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "id"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "title"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "number"]),
        expect_errors=True,
    )
    assert resp.status_code == 200

    resp = app.get(
        reverse("property-structure", args=[structure.dataset.pk, "State", "residence"]),
        expect_errors=True,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_model_create_with_public_visibility_without_uri_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("model-create", args=[dataset.pk])).forms["model-form"]
    form["name"] = "Test"
    form["visibility"] = Metadata.VISIBILITY_PUBLIC
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Stulpelis 'Klasė' turi būti užpildytas pasirenkant šį metaduomenų matomumo lygį."]
    ]


@pytest.mark.django_db
def test_property_create__higher_visibility_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        visibility=Metadata.PRIVATE,
    )
    form = app.get(reverse("property-create", args=[dataset.pk, model.name])).forms[
        "property-form"
    ]
    form["name"] = "property"
    form["access"] = Metadata.OPEN
    form["visibility"] = Metadata.PROTECTED
    form["type"] = "any"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Metaduomenų matomumas 'protected' negali būti didesnis nei duomenų modelio matomumas 'private'."]
    ]


@pytest.mark.django_db
def test_property_enum_item_create__higher_visibility_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    model = ModelFactory()
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
        name="test/dataset",
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
        visibility=Metadata.PRIVATE,
    )
    form = app.get(
        reverse("enum-create", args=[dataset.pk, model.name, prop.name])
    ).forms["enum-form"]
    form["value"] = 2
    form["source"] = 2
    form["access"] = Metadata.OPEN
    form["title"] = "Test value"
    form["description"] = "For testing"
    form["visibility"] = Metadata.PROTECTED
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        [
            "Metaduomenų matomumas 'protected' negali būti didesnis nei duomenų lauko matomumas 'private'."
        ]
    ]

@pytest.mark.django_db
def test_property_enum_item_create__higher_visibility_then_model_with_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        visibility=Metadata.PRIVATE
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset",
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="integer",
    )
    form = app.get(
        reverse("enum-create", args=[dataset.pk, model.name, prop.name])
    ).forms["enum-form"]
    form["value"] = 2
    form["source"] = 2
    form["access"] = Metadata.OPEN
    form["title"] = "Test value"
    form["description"] = "For testing"
    form["visibility"] = Metadata.PROTECTED
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        [
            "Metaduomenų matomumas 'protected' negali būti didesnis nei duomenų modelio matomumas 'private'."
        ]
    ]

@pytest.mark.django_db
def test_manifest_export_openapi(app: DjangoTestApp):
    """Test OpenAPI manifest export returns valid spec with correct metadata, schemas, tags, and paths."""
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        ',,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        ',,,,Country,,,,,,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n'
        ',,,,,title,string,,,,5,,,private,dct:title,,,,\n'
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
    resp = app.get(reverse('dataset-structure-export-openapi', args=[structure.dataset.pk]))

    assert resp.status_code == 200
    assert resp.content_type == 'application/json'
    
    openapi_spec = resp.json
    
    expected_keys = ['openapi', 'info', 'externalDocs', 'servers', 'tags', 'components', 'paths']
    assert list(openapi_spec.keys()) == expected_keys, "OpenAPI spec missing required top-level fields"
    
    info = openapi_spec['info']
    assert info['summary'] == structure.dataset.title, "Info summary should match dataset title"
    assert info['description'] == structure.dataset.description, "Info description should match dataset description"
    assert info['version'] == '1.0.0', "API version should be 1.0.0"
    
    schemas = set(openapi_spec['components']['schemas'].keys())
    expected_schemas = {"Country", "CountryCollection", "CountryChange", "CountryChanges"}
    assert expected_schemas <= schemas, f"Missing required schemas: {expected_schemas - schemas}"
    
    tag_names = {tag["name"] for tag in openapi_spec["tags"]}
    expected_tags = {"utility", "Country"}
    assert tag_names == expected_tags, f"Tags mismatch. Expected: {expected_tags}, Got: {tag_names}"
    
    utility_paths = {"/version", "/health"}
    model_paths = {
        "/datasets/gov/ivpk/adp/Country",
        "/datasets/gov/ivpk/adp/Country/{id}",
        "/datasets/gov/ivpk/adp/Country/:changes/{cid}"
    }
    expected_paths = utility_paths | model_paths
    actual_paths = set(openapi_spec["paths"].keys())
    assert actual_paths == expected_paths, (
        f"Paths mismatch. Missing: {expected_paths - actual_paths}, "
        f"Extra: {actual_paths - expected_paths}"
    )

@pytest.mark.django_db
def test_imported_metadata_gets_develop_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,Size,,SMALL,,,,,,,,,\n"
        ",,,,,,,,,MEDIUM,,,,,,,,,\n"
        ",,,,,,,,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename="file.csv", data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]
    assert list(resp_models.context["props"].values_list("metadata__status__codename", flat=True)) == ["develop", "develop", "develop"]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "id"]))
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]
    assert resp_props.context["prop"].metadata.get().status.codename == "develop"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "title"]))
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]
    assert resp_props.context["prop"].metadata.get().status.codename == "develop"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]

    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        assert enum_item.metadata.first().status.codename == "develop"


@pytest.mark.django_db
def test_published_metadata_gets_completed_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,Size,,SMALL,,,,,,,,,\n"
        ",,,,,,,,,MEDIUM,,,,,,,,,\n"
        ",,,,,,,,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename="file.csv", data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    metadata_ids = list(
        Metadata.objects.filter(
            dataset=structure.dataset,
            draft=True,
        ).values_list('id', flat=True)
    )

    form = app.get(reverse('version-create', args=[structure.dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = metadata_ids
    form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["completed"]
    assert list(resp_models.context["props"].values_list("metadata__status__codename", flat=True)) == ["completed", "completed", "completed"]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "id"]))
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["completed"]
    assert resp_props.context["prop"].metadata.get().status.codename == "completed"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "title"]))
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["completed"]
    assert resp_props.context["prop"].metadata.get().status.codename == "completed"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    assert list(resp_props.context["models"].values_list("metadata__status__codename", flat=True)) == ["completed"]

    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        assert enum_item.metadata.first().status.codename == "completed"


@pytest.mark.django_db
def test_changed_metadata_keeps_status_after_publishing(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename="file.csv", data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id

    metadata_ids = list(
        Metadata.objects.filter(
            dataset=structure.dataset,
            draft=True,
        ).values_list('id', flat=True)
    )

    model_form = app.get(reverse('model-update', args=[structure.dataset.pk, "Country"])).forms['model-form']
    model_form['status'] = Status.objects.filter(codename="discont").first().id
    model_form.submit()

    property_form = app.get(reverse('property-update', args=[structure.dataset.pk, "Country", "administration"])).forms['property-form']
    property_form['status'] = Status.objects.filter(codename="deprecated").first().id
    property_form.submit()

    enum_form = app.get(reverse('enum-update', args=[structure.dataset.pk, "Country", "administration", enum_id])).forms['enum-form']
    enum_form['status'] = Status.objects.filter(codename="withdrawn").first().id
    enum_form.submit()

    form = app.get(reverse('version-create', args=[structure.dataset.pk])).forms['version-form']
    form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    form['version_type'] = "MAJOR"
    form['metadata'] = metadata_ids
    form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["discont"]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "id"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "discont"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "title"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "completed"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "deprecated"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        assert enum_item.metadata.first().status.codename == "withdrawn"

@pytest.mark.django_db
def test_published_metadata_defaults_to_develop_after_hard_change(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,big,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename="file.csv", data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    metadata_ids = list(
        Metadata.objects.filter(
            dataset=structure.dataset,
            draft=True,
        ).values_list('id', flat=True)
    )
    publish_version_form = app.get(reverse('version-create', args=[structure.dataset.pk])).forms['version-form']
    publish_version_form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    publish_version_form['version_type'] = "MAJOR"
    publish_version_form['metadata'] = metadata_ids
    publish_version_form.submit()

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id
    new_enum_name = "Largety"

    model_form = app.get(reverse('model-update', args=[structure.dataset.pk, "Country"])).forms['model-form']
    model_form['level'] = 3
    model_form.submit()

    property_form = app.get(reverse('property-update', args=[structure.dataset.pk, "Country", "administration"])).forms['property-form']
    property_form['access'] = 2
    property_form.submit()

    enum_form = app.get(reverse('enum-update', args=[structure.dataset.pk, "Country", "administration", enum_id])).forms['enum-form']
    enum_form['value'] = new_enum_name
    enum_form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "title"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "completed"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "develop"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        enum_metadata = enum_item.metadata.first()
        if enum_metadata.name == new_enum_name:
            assert enum_metadata.status.codename == "completed"
        else:
            assert enum_metadata.status.codename == "develop"

@pytest.mark.django_db
def test_draft_metadata_defaults_to_develop_after_hard_change(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,big,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename="file.csv", data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id
    new_enum_name = "Largety"

    model_form = app.get(reverse('model-update', args=[structure.dataset.pk, "Country"])).forms['model-form']
    model_form['level'] = 3
    model_form.submit()

    property_form = app.get(reverse('property-update', args=[structure.dataset.pk, "Country", "administration"])).forms['property-form']
    property_form['access'] = 2
    property_form.submit()

    enum_form = app.get(reverse('enum-update', args=[structure.dataset.pk, "Country", "administration", enum_id])).forms['enum-form']
    enum_form['value'] = new_enum_name
    enum_form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "develop"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        enum_metadata = enum_item.metadata.first()
        assert enum_metadata.status.codename == "develop"

@pytest.mark.django_db
def test_changing_multiple_fields_in_draft_structure_respects_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,big,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename="file.csv", data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id
    new_enum_name = "Largety"

    model_form = app.get(reverse('model-update', args=[structure.dataset.pk, "Country"])).forms['model-form']
    model_form['level'] = 2
    model_form["status"] = 5
    model_form.submit()

    property_form = app.get(reverse('property-update', args=[structure.dataset.pk, "Country", "administration"])).forms['property-form']
    property_form['access'] = 2
    property_form["status"] = 5
    property_form.submit()

    enum_form = app.get(reverse('enum-update', args=[structure.dataset.pk, "Country", "administration", enum_id])).forms['enum-form']
    enum_form['value'] = new_enum_name
    enum_form["status"] = 5
    enum_form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["deprecated"]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "deprecated"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        enum_metadata = enum_item.metadata.first()
        if enum_metadata.name == new_enum_name:
            assert enum_metadata.status.codename == "completed"
        else:
            assert enum_metadata.status.codename == "deprecated"

@pytest.mark.django_db
def test_changing_multiple_fields_in_published_structure_respects_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,big,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename="file.csv", data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    metadata_ids = list(
        Metadata.objects.filter(
            dataset=structure.dataset,
            draft=True,
        ).values_list('id', flat=True)
    )
    publish_version_form = app.get(reverse('version-create', args=[structure.dataset.pk])).forms['version-form']
    publish_version_form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    publish_version_form['version_type'] = "MAJOR"
    publish_version_form['metadata'] = metadata_ids
    publish_version_form.submit()

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id
    new_enum_name = "Largety"

    model_form = app.get(reverse('model-update', args=[structure.dataset.pk, "Country"])).forms['model-form']
    model_form['level'] = 2
    model_form["status"] = 5
    model_form.submit()

    property_form = app.get(reverse('property-update', args=[structure.dataset.pk, "Country", "administration"])).forms['property-form']
    property_form['access'] = 2
    property_form["status"] = 5
    property_form.submit()

    enum_form = app.get(reverse('enum-update', args=[structure.dataset.pk, "Country", "administration", enum_id])).forms['enum-form']
    enum_form['value'] = new_enum_name
    enum_form["status"] = 5
    enum_form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["deprecated"]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "deprecated"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        enum_metadata = enum_item.metadata.first()
        if enum_metadata.name == new_enum_name:
            assert enum_metadata.status.codename == "completed"
        else:
            assert enum_metadata.status.codename == "deprecated"

@pytest.mark.django_db
def test_draft_metadata_form_does_not_change_status_is_kept(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,big,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename="file.csv", data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id

    model_form = app.get(reverse('model-update', args=[structure.dataset.pk, "Country"])).forms['model-form']
    model_form.submit()

    property_form = app.get(reverse('property-update', args=[structure.dataset.pk, "Country", "administration"])).forms['property-form']
    property_form.submit()

    enum_form = app.get(reverse('enum-update', args=[structure.dataset.pk, "Country", "administration", enum_id])).forms['enum-form']
    enum_form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["develop"]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "develop"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    prop = resp_props.context["prop"]
    for enum_item in prop.enums.first().enumitem_set.all():
        enum_metadata = enum_item.metadata.first()
        assert enum_metadata.status.codename == "develop"

@pytest.mark.django_db
def test_published_metadata_form_does_not_change_status_is_kept(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n"
        ",,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n"
        ",datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        ",,,,Country,,,,,,,,,,,,,,\n"
        ",,,,,id,integer,,,,5,discont,,open,dct:identifier,,Identifikatorius,,\n"
        ",,,,,title,string,,,,5,,,private,dct:title,,,,\n"
        ",,,,,administration,string,,,,5,,,open,dct:title,,,,\n"
        ",,,,,,enum,small,,SMALL,,,,,,,,,\n"
        ",,,,,,,big,,BIG,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename="file.csv", data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    metadata_ids = list(
        Metadata.objects.filter(
            dataset=structure.dataset,
            draft=True,
        ).values_list('id', flat=True)
    )
    publish_version_form = app.get(reverse('version-create', args=[structure.dataset.pk])).forms['version-form']
    publish_version_form['released'] = datetime.date.today() + datetime.timedelta(days=15)
    publish_version_form['version_type'] = "MAJOR"
    publish_version_form['metadata'] = metadata_ids
    publish_version_form.submit()

    enum_meta = Metadata.objects.filter(dataset=structure.dataset, name="small").first()

    enum = enum_meta.object
    enum_id = enum.id

    model_form = app.get(reverse('model-update', args=[structure.dataset.pk, "Country"])).forms['model-form']
    model_form.submit()

    property_form = app.get(reverse('property-update', args=[structure.dataset.pk, "Country", "administration"])).forms['property-form']
    property_form.submit()

    enum_form = app.get(reverse('enum-update', args=[structure.dataset.pk, "Country", "administration", enum_id])).forms['enum-form']
    enum_form.submit()

    resp_models = app.get(reverse("model-structure", args=[structure.dataset.pk, "Country"]))
    assert list(resp_models.context["models"].values_list("metadata__status__codename", flat=True)) == ["completed"]

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    assert resp_props.context["prop"].metadata.get().status.codename == "completed"

    resp_props = app.get(reverse("property-structure", args=[structure.dataset.pk, "Country", "administration"]))
    prop = resp_props.context["prop"]
    #TODO the status of enum should also be completed but because of a bug the name of the enum is changed even though nothing is submited. Change after bug fix
    for enum_item in prop.enums.first().enumitem_set.all():
        enum_metadata = enum_item.metadata.first()
        assert enum_metadata.status.codename == "develop"

@pytest.mark.django_db
def test_props_metadata_rendering(app: DjangoTestApp) -> None:
    model = ModelFactory()
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
        name="test/dataset",
    )

    prop_1 = PropertyFactory(model=model)
    prop_2 = PropertyFactory(model=model)

    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_1),
        object_id=prop_1.pk,
        dataset=dataset,
        name="prop_1",
        type="string",
        eli="https://example.com/prop_1",
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop_2),
        object_id=prop_2.pk,
        dataset=dataset,
        name="prop_2",
        type="integer",
        eli="https://example.com/prop_2",
    )

    response = app.get(reverse("model-structure", kwargs={"pk": dataset.pk, "model": model.name}))

    assert response.status_code == 200
    assert 'href="https://example.com/prop_1"' in response.content.decode()
    assert 'href="https://example.com/prop_2"' in response.content.decode()

@pytest.mark.django_db
def test_only_major_version_allowed_when_new_metadata(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]

    assert form["version_type"].options[0][0] == "MAJOR"

@pytest.mark.django_db
def test_minor_version_available_if_major_exists(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    form["version_type"] = "MAJOR"
    form.submit()

    second_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]

    assert [opt[0] for opt in second_version_form["version_type"].options] == ["MAJOR", "MINOR", "PATCH"]

@pytest.mark.django_db
def test_patch_version_available_if_minor_exists(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    major_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MAJOR)

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = major_version.pk
    minor_version_form.submit()

    patch_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]

    assert [opt[0] for opt in patch_version_form["version_type"].options] == ["MAJOR", "MINOR", "PATCH"]

@pytest.mark.django_db
def test_form_errors_if_major_not_selected(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    major_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["version_type"] = "MINOR"

    res = minor_version_form.submit(expect_errors=True)

    assert "Tėvinė versija turi būti pasirinkta" in res.text

@pytest.mark.django_db
def test_form_errors_if_minor_not_selected(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    major_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MAJOR)

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = major_version.pk
    minor_version_form.submit()

    patch_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    patch_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    patch_version_form["version_type"] = "PATCH"

    res = patch_version_form.submit(expect_errors=True)

    assert "Tėvinė versija turi būti pasirinkta" in res.text

@pytest.mark.django_db
def test_multiple_major_versions_increment_external_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    major_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_versions = _Version.objects.filter(dataset=dataset, version_type=VersionType.MAJOR).order_by("created")

    assert major_versions[0].external_version == "1.0.0"
    assert major_versions[1].external_version == "2.0.0"

@pytest.mark.django_db
def test_multiple_minor_versions_increment_external_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    major_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MAJOR)

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = major_version.pk
    minor_version_form.submit()

    latest_version = _Version.objects.last()

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = latest_version.pk
    minor_version_form.submit()

    minor_versions = _Version.objects.filter(dataset=dataset, version_type=VersionType.MINOR).order_by("created")

    assert minor_versions[0].external_version == "1.1.0"
    assert minor_versions[1].external_version == "1.2.0"

@pytest.mark.django_db
def test_multiple_patch_versions_increment_external_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    major_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    major_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    major_version_form["version_type"] = "MAJOR"
    major_version_form.submit()

    major_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MAJOR)

    minor_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    minor_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    minor_version_form["version_type"] = "MINOR"
    minor_version_form["related_version"] = major_version.pk
    minor_version_form.submit()

    minor_version = _Version.objects.get(dataset=dataset, version_type=VersionType.MINOR)

    patch_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    patch_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    patch_version_form["related_version"] = minor_version.pk
    patch_version_form["version_type"] = "PATCH"
    patch_version_form.submit()

    latest_version = _Version.objects.last()

    patch_version_form = app.get(reverse("version-create", args=[dataset.pk])).forms["version-form"]
    patch_version_form["released"] = datetime.date.today() + datetime.timedelta(days=15)
    patch_version_form["related_version"] = latest_version.pk
    patch_version_form["version_type"] = "PATCH"
    patch_version_form.submit()

    patch_versions = _Version.objects.filter(dataset=dataset, version_type=VersionType.PATCH).order_by("created")

    assert patch_versions[0].external_version == "1.1.1"
    assert patch_versions[1].external_version == "1.1.2"

def test_publish_form_shows_all_metadata_rows_params(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        ',,,,,,prefix,dct,,,,,,,http://purl.org/dc/terms/,,,,\n'
        '2,,,,,,param,country,,"lt",,,,,,,,,\n'
        '3,,,,,,,,,"lv",,,,,,,,,\n'
        '4,,,,,,,,,"ee",,,,,,,,,\n'
        '5,,,,City,,,,,,,,,,,,,,\n'
        '6,,,,,,param,type,,"created",,,,,,,,,\n'
        '7,,,,,,,,,"modified",,,,,,,,,\n'
        '8,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,\n'
        '9,,,,,type,string,,,,5,,,open,dct:type,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 11 # 10 fields from DSA + 1 for dataset_distribution

def test_publish_form_shows_all_metadata_rows_base(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        ',datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        '1,,,,Base,,,,,,4,,,,,,,,,\n'
        ',,,Base,,,,,,,4,,,,,,,,,\n'
        '2,,,,City,,,,,,5,,,,,,,,,\n'
        ',,,,,id,integer,,,,5,,,,,,,,,\n'
        ',,,,,title,string,,,,5,,,,,,,,,\n'
        ',,,,,country,ref,Country,,,4,,,,,,,,,\n'
        '3,,,,Country,,,,,,4,,,,,,,,,\n'
        ',,,,,id,integer,,,,3,,,,,,,,,\n'
        ',,,,,title,string,,,,2,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 10 # 9 fields from DSA, because Base as City Base is not displayed + 1 for dataset_distribution

def test_publish_form_shows_all_metadata_rows_enum(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n'
        '1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        '2,,,,,,prefix,dct,,,,,,,,http://purl.org/dc/terms/,,,\n'
        '3,,,,,,enum,Size,,SMALL,,,,,,,,,,\n'
        '4,,,,,,,,,MEDIUM,,,,,,,,,\n'
        '5,,,,,,,,,BIG,,,,,,,,,\n'
        '6,,,,City,,,,,,,,,,,,,,\n'
        '7,,,,,id,integer,,,,,5,,,open,dct:identifier,,Identifikatorius,\n'
        '8,,,,,size,Size,,,,,5,,,open,dct:size,,,\n'
        '9,,,,,type,string,,,,,5,,,open,dct:type,,,\n'
        '10,,,,,,enum,Type,,CREATED,,,,,,,,,\n'
        '11,,,,,,,,,MODIFIED,,,,,,,,,\n'
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 12 # 11 DSA rows + 1 dataset_distribution

def test_publish_form_shows_all_metadata_rows_single_defined_resource(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        '1,datasets/govsssss/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        '2,,,,City,,,,,,5,,,,,,,,,\n'
        '3,,,,,id,integer,,,,5,,,,,,,,,\n'
        '4,,,,,title,string,,,,5,,,,,,,,,\n'
        '5,,,,,country,ref,Country,,,4,,,,,,,,,\n'
        '6,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n'
        '7,,,,Country,,,,,,4,,,,,,,,,\n'
        '8,,,,,id,integer,,,,3,,,,,,,,,\n'
        '9,,,,,title,string,,,,2,,,,,,,,,\n'
    )

    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 9

def test_publish_form_shows_all_metadata_rows_multiple_resources(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        '1,datasets/govsssss/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        '2,,resource1,,,,,,http://www.example.com,,,,,,,,,Title,Description\n'
        '3,,,,City,,,,,,5,,,,,,,,,\n'
        '4,,,,,id,integer,,,,5,,,,,,,,,\n'
        '5,,,,,title,string,,,,5,,,,,,,,,\n'
        '6,,,,,country,ref,Country,,,4,,,,,,,,,\n'
        '7,,resource,,,,,,http://www.example2.com,,,,,,,,,Title,Description\n'
        '8,,,,Country,,,,,,4,,,,,,,,,\n'
        '9,,,,,id,integer,,,,3,,,,,,,,,\n'
        '10,,,,,title,string,,,,2,,,,,,,,,\n'
    )

    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    dataset_distributions = DatasetDistribution.objects.filter(dataset=structure.dataset)

    form = app.get(reverse("version-create", args=[structure.dataset.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 10
    assert len(dataset_distributions) == 2
    assert dataset_distributions.first().metadata.first().name == "resource1"
    assert dataset_distributions.last().metadata.first().name == "resource"

def test_publish_form_shows_all_metadata_rows_denorm_props(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    manifest = (
        'id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count\n'
        '1,datasets/govsssss/ivpk/adp,,,,,,,,,,,,,,,,,\n'
        '2,,,,City,,,,,,,,,,,,,,\n'
        '3,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,,\n'
        '4,,,,,title,string,,,,5,,,open,dct:title,,,,\n'
        '5,,,,,country,ref,Country,,,5,,,open,,,,,,\n'
        '6,,,,,country.id,,,,,5,,,open,,,,,,\n'
        '7,,,,,country.continent.id,,,,,5,,,open,,,,,,\n'
        '8,,resource,,,,,,http://www.example.com,,,,,,,,,Title,Description\n'
        '9,,,,Country,,,,,,4,,,,,,,,,\n'
        '10,,,,,id,integer,,,,3,,,,,,,,,\n'
        '11,,,,,title,string,,,,2,,,,,,,,,\n'
    )

    structure = DatasetStructureFactory(
        file=FilerFileFactory(
            file=FileField(filename='file.csv', data=manifest)
        )
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    create_structure_objects(structure)

    form = app.get(reverse("version-create", args=[structure.dataset.pk])).forms["version-form"]
    assert len(form.fields["metadata"]) == 12 # Denorm props create an additional property country.continent

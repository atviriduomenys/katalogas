from importlib import import_module

import pytest
from django_webtest import DjangoTestApp
from vitrina.classifiers.models import Category

data_migration = import_module('vitrina.classifiers.migrations.0007_remake_categories')


@pytest.fixture
def categories():
    category = Category.objects.create(title='parent', version=1, featured=False, depth=0, path='1')
    category1 = Category.objects.create(title='first_child', version=1, featured=False, parent=category, depth=0, path='2')
    Category.objects.create(title='second_child_1', version=1, featured=False, parent=category1, depth=0, path='3')
    Category.objects.create(title='second_child_2', version=1, featured=False, parent=category1, depth=0, path='4')
    data_migration._fix_mp(Category, ['title'])


@pytest.mark.django_db
def test_mp_bad_field_data_changed(app: DjangoTestApp, categories):
    cats = Category.objects.all()
    assert cats[0].path != '1'
    assert cats[1].path != '2'
    assert cats[2].path != '3'
    assert cats[3].path != '4'


@pytest.mark.django_db
def test_root_data_set(app: DjangoTestApp, categories):
    root_cats = Category.objects.filter(parent__isnull=True)

    assert root_cats[0].depth == 1
    assert root_cats[0].numchild == 1


@pytest.mark.django_db
def test_child_data_set(app: DjangoTestApp, categories):
    child_cats = Category.objects.filter(parent__isnull=False).order_by('depth')

    assert child_cats[0].depth == 2
    assert child_cats[0].numchild == 2
    assert child_cats[1].depth == 3
    assert child_cats[1].numchild == 0
    assert child_cats[2].depth == 3
    assert child_cats[2].numchild == 0


@pytest.mark.django_db
def test_path_generation(app: DjangoTestApp, categories):
    cats = Category.objects.all()

    assert cats[0].path == '0001'
    assert cats[1].path == '00010001'
    assert cats[2].path == '000100010001'
    assert cats[3].path == '000100010002'



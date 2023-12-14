import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from webtest import Upload

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.factories import MetadataFactory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


@pytest.mark.django_db
def test_change_form_wrong_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(reverse('resource-change', kwargs={'pk': resource.id}))
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location


@pytest.mark.django_db
def test_change_form_correct_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    form = app.get(reverse('resource-change', kwargs={'pk': resource.id})).forms['resource-form']
    form['title'] = "Edited title"
    form['description'] = "edited resource description"
    resp = form.submit()
    resource.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('resource-detail', args=[resource.dataset.pk, resource.pk])
    assert resource.title == 'Edited title'
    assert resource.description == 'edited resource description'
    assert resource.metadata.count() == 1
    assert resource.metadata.first().name == 'resource1'


@pytest.mark.django_db
def test_click_edit_button(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    response = app.get(reverse('dataset-detail', kwargs={'pk': resource.dataset_id}))
    response.click(linkid='change_resource')
    assert response.status_code == 200


@pytest.mark.django_db
def test_add_form_no_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    response = app.get(reverse('resource-add', kwargs={'pk': resource.dataset_id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_add_form_wrong_login(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    resource = DatasetDistributionFactory()
    response = app.get(reverse('resource-add', kwargs={'pk': resource.dataset_id}))
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location


@pytest.mark.django_db
def test_add_form_correct_login(app: DjangoTestApp):
    dataset = DatasetFactory()
    file_format = FileFormat(extension='URL')
    user = UserFactory(is_staff=True, organization=dataset.organization)
    app.set_user(user)
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'Added title'
    form['description'] = 'Added new resource description'
    form['format'] = file_format.id
    form['download_url'] = "www.google.lt"
    form['period_start'] = '2022-10-20'
    form['period_end'] = '2022-12-20'
    resp = form.submit()
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 1
    assert DatasetDistribution.objects.first().metadata.count() == 1
    assert DatasetDistribution.objects.first().metadata.first().name == 'resource1'


@pytest.mark.django_db
def test_change_form_data_gov_url_upload_checked(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse('resource-change', kwargs={'pk': resource.pk})).forms['resource-form']
    form['format'] = FileFormat(extension='URL')
    form['download_url'] = 'get.data.gov.lt'
    resp = form.submit()
    resource.refresh_from_db()
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 1
    assert resource.upload_to_storage is True


@pytest.mark.django_db
def test_change_form_upload_checked(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse('resource-change', kwargs={'pk': resource.pk})).forms['resource-form']
    form['upload_to_storage'] = True
    resp = form.submit()
    resource.refresh_from_db()
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 1
    assert resource.upload_to_storage is True


@pytest.mark.django_db
def test_click_add_button(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    response = app.get(reverse('dataset-detail', kwargs={'pk': resource.dataset_id}))
    response.click(linkid='add_resource')
    assert response.status_code == 200


@pytest.mark.django_db
def test_delete_no_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    response = app.get(reverse('resource-delete', kwargs={'pk': resource.id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_delete_wrong_login(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    resource = DatasetDistributionFactory()
    response = app.get(reverse('resource-delete', kwargs={'pk': resource.id}))
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location


@pytest.mark.django_db
def test_delete_correct_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    resp = app.get(reverse('resource-delete', kwargs={'pk': resource.pk}))
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 0


@pytest.mark.django_db
def test_click_delete_button(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    response = app.get(reverse('dataset-detail', kwargs={'pk': resource.dataset_id}))
    response.click(linkid='delete_resource')
    assert response.status_code == 200


@pytest.mark.django_db
def test_detail_tab_from_resource_detail_view(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    resp = app.get(reverse('resource-detail', args=[resource.dataset.pk, resource.pk]))
    resp = resp.click(linkid='detail_tab')
    assert resp.request.path == resource.dataset.get_absolute_url()


@pytest.mark.django_db
def test_create_resource_model(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    resource = DatasetDistributionFactory()
    form = app.get(reverse('resource-model-create', args=[resource.dataset.pk, resource.pk])).forms['model-form']
    form['name'] = "TestModel"
    resp = form.submit()
    assert resp.url == resource.get_absolute_url()
    assert resource.model_set.count() == 1
    assert resource.model_set.first().name == 'TestModel'


@pytest.mark.django_db
def test_create_resource_without_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    resource = DatasetDistributionFactory()
    dataset = resource.dataset
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(resource),
        object_id=resource.pk,
        name='resource3'
    )
    format = FileFormat(extension='URL')
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'New resource'
    form['format'] = format.pk
    form['download_url'] = "www.test.com"
    resp = form.submit()
    new_resource = DatasetDistribution.objects.exclude(pk=resource.pk)
    assert resp.url == new_resource.first().get_absolute_url()
    assert new_resource.count() == 1
    assert new_resource.first().metadata.count() == 1
    assert new_resource.first().metadata.first().name == 'resource4'


@pytest.mark.django_db
def test_create_resource_with_file_and_wrong_format(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    format = FileFormat(extension='URL')
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'New resource'
    form['format'] = format.pk
    form['file'] = Upload('test.csv', b'Column\nValue')
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        'Formatas nesutampa su įkelto failo formatu.'
    ]]


@pytest.mark.django_db
def test_create_resource_with_download_url_and_wrong_format(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    format = FileFormat(extension='CSV')
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'New resource'
    form['format'] = format.pk
    form['download_url'] = "www.test.com"
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        'Pasirinkite nuorodos formatą.'
    ]]

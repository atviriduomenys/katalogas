import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.classifiers.models import Concept
from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat, CompressionFormatFactory, \
    PackagingFormatFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure.factories import MetadataFactory, VersionFactory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


@pytest.mark.django_db
def test_change_form_wrong_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(reverse('resource-change', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk}))
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location


@pytest.mark.django_db
def test_change_form_correct_login(app: DjangoTestApp):
    version = VersionFactory()
    resource = DatasetDistributionFactory(title='base title', description='base description', dataset=version.dataset, metadata_version=version)
    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    form = app.get(reverse('resource-change', kwargs={'pk': resource.id, 'version_id': version.pk})).forms['resource-form']
    form['title'] = "Edited title"
    form['description'] = "edited resource description"
    form['level'] = 2
    form['metadata_version'] = version.pk
    resp = form.submit()
    resource.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('resource-detail', args=[resource.dataset.pk, version.pk, resource.pk])
    assert resource.title == 'Edited title'
    assert resource.description == 'edited resource description'
    assert resource.metadata.count() == 1
    assert resource.metadata.first().name == 'resource1'
    assert resource.metadata.first().title == "Edited title"
    assert resource.metadata.first().description == "edited resource description"
    assert resource.metadata.first().level_given == 2


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
    version = VersionFactory(dataset=dataset)
    file_format = FileFormat(extension='URL')
    user = UserFactory(is_staff=True, organization=dataset.organization)
    app.set_user(user)
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'Added title'
    form['description'] = 'Added new resource description'
    form['format'] = file_format.id
    form['download_url'] = "www.google.lt"
    form['level'] = 1
    form['metadata_version'] = version.pk
    resp = form.submit()
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 1
    assert DatasetDistribution.objects.first().metadata.count() == 1
    assert DatasetDistribution.objects.first().metadata.first().name == 'resource1'
    assert DatasetDistribution.objects.first().metadata.first().title == 'Added title'
    assert DatasetDistribution.objects.first().metadata.first().description == 'Added new resource description'
    assert DatasetDistribution.objects.first().metadata.first().level_given == 1


@pytest.mark.django_db
def test_change_form_data_gov_url_upload_checked(app: DjangoTestApp):
    file_format = FileFormat(title='URL', extension='URL')
    version = VersionFactory()
    resource = DatasetDistributionFactory(title='base title', description='base description',
                                          format=file_format, file=None, dataset=version.dataset, metadata_version=version)
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse('resource-change', kwargs={'pk': resource.pk, 'version_id': version.pk})).forms['resource-form']
    form['download_url'] = 'get.data.gov.lt'
    form['metadata_version'] = version.pk
    resp = form.submit()
    resource.refresh_from_db()
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 1
    assert resource.upload_to_storage is True


@pytest.mark.django_db
def test_change_form_upload_checked(app: DjangoTestApp):
    version = VersionFactory()
    resource = DatasetDistributionFactory(title='base title', description='base description', dataset=version.dataset, metadata_version=version)
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse('resource-change', kwargs={'pk': resource.pk, 'version_id': version.pk})).forms['resource-form']
    form['upload_to_storage'] = True
    form['metadata_version'] = version.pk
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
    response = app.get(reverse('resource-delete', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_delete_wrong_login(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    resource = DatasetDistributionFactory()
    response = app.post(reverse('resource-delete', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk}))
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location


@pytest.mark.django_db
def test_delete_correct_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    resp = app.post(reverse('resource-delete', kwargs={'pk': resource.pk, 'version_id': resource.metadata_version.pk}))
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 0


@pytest.mark.django_db
def test_detail_tab_from_resource_detail_view(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    resp = app.get(reverse('resource-detail', args=[resource.dataset.pk, resource.metadata_version.pk, resource.pk]))
    resp = resp.click(linkid='detail_tab')
    assert resp.request.path == resource.dataset.get_absolute_url()


@pytest.mark.django_db
def test_create_resource_model(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    resource = DatasetDistributionFactory()
    form = app.get(reverse('resource-model-create', args=[resource.dataset.pk, resource.metadata_version.pk, resource.pk])).forms['model-form']
    form['name'] = "TestModel"
    resp = form.submit()
    assert resp.url == resource.get_absolute_url()
    assert resource.model_set.count() == 1
    assert resource.model_set.first().name == 'TestModel'


@pytest.mark.django_db
def test_create_resource_without_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    version = VersionFactory()
    resource = DatasetDistributionFactory(dataset=version.dataset, metadata_version=version)
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
    form['metadata_version'] = version.pk
    resp = form.submit()
    new_resource = DatasetDistribution.objects.exclude(pk=resource.pk)
    assert resp.url == new_resource.first().get_absolute_url()
    assert new_resource.count() == 1
    assert new_resource.first().metadata.count() == 1
    assert new_resource.first().metadata.first().name == 'resource4'
    assert new_resource.first().metadata.first().metadata_version == version


@pytest.mark.django_db
def test_create_resource_with_existing_download_url(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = VersionFactory(dataset=dataset)
    format = FileFormat(extension='URL')
    DatasetDistributionFactory(
        dataset=dataset,
        format=format,
        download_url="http://www.test.com"
    )
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'New resource'
    form['format'] = format.pk
    form['download_url'] = "http://www.test.com"
    form['metadata_version'] = version.pk
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        'Duomenų šaltinis su šia atsisiuntimo nuoroda jau egzistuoja.'
    ]]


@pytest.mark.django_db
def test_distribution_detail_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    resource = DatasetDistributionFactory(dataset=dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse('resource-detail', args=[dataset.pk, resource.pk, resource.metadata_version.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_distribution_detail_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    resource = DatasetDistributionFactory(dataset=dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.MANAGER

    )
    app.set_user(user)
    response = app.get(reverse('resource-detail', args=[dataset.pk, resource.metadata_version.pk, resource.pk]))
    assert response.context['object'] == resource


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_json(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    resource = DatasetDistributionFactory( uapi_format=True)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse('resource-model-create', args=[dataset.pk, resource.metadata_version.pk, resource.pk])).forms['model-form']
    form['name'] = "TestModel"
    form.submit()
    assert resource.model_set.first().name == 'TestModel'

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, resource.pk, "TestModel", "json"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/json'
    assert list(response.context['resource']['models']) == list(resource.model_set.all())
    assert response.context['format'] == 'JSON'
    assert response.context['resource']['dataset'] == dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_jsonl(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    version = VersionFactory(dataset=dataset)
    resource = DatasetDistributionFactory(uapi_format=True, metadata_version=version)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse('resource-model-create', args=[dataset.pk, version.pk, resource.pk])).forms['model-form']
    form['name'] = "TestModel"
    form.submit()
    assert resource.model_set.first().name == 'TestModel'

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, version.pk, resource.pk, "TestModel", "jsonl"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/jsonl'
    assert list(response.context['resource']['models']) == list(resource.model_set.all())
    assert response.context['format'] == 'JSONL'
    assert response.context['resource']['dataset'] == dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_csv(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    version = VersionFactory(dataset=dataset)
    resource = DatasetDistributionFactory(uapi_format=True, metadata_version=version)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse('resource-model-create', args=[dataset.pk, version.pk, resource.pk])).forms['model-form']
    form['name'] = "TestModel"
    form.submit()
    assert resource.model_set.first().name == 'TestModel'

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, version.pk, resource.pk, "TestModel", "csv"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:format/csv'
    assert list(response.context['resource']['models']) == list(resource.model_set.all())
    assert response.context['format'] == 'CSV'
    assert response.context['resource']['dataset'] == dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_json_multiple_models(app: DjangoTestApp):
    version = VersionFactory()
    resource = DatasetDistributionFactory(uapi_format=True, metadata_version=version)
    user = UserFactory(is_staff=True)
    app.set_user(user)
    for model_name in ["TestModel", "TestModel2", "TestModel3"]:
        form = app.get(reverse('resource-model-create', args=[resource.dataset.pk, version.pk, resource.pk])).forms['model-form']
        form['name'] = model_name
        form.submit()
    assert resource.model_set.count() == 3

    response = app.get(reverse('dynamic-resource-detail', args=[resource.dataset.pk, version.pk, resource.pk, "TestModel", "json"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/json'
    assert list(response.context['resource']['models']) == list(resource.model_set.all())
    assert response.context['format'] == 'JSON'
    assert response.context['resource']['dataset'] == resource.dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_jsonl_multiple_models(app: DjangoTestApp):
    version = VersionFactory()
    resource = DatasetDistributionFactory(dataset=version.dataset, uapi_format=True, metadata_version=version)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    for model_name in ["TestModel", "TestModel2", "TestModel3"]:
        form = app.get(reverse('resource-model-create', args=[resource.dataset.pk, version.pk, resource.pk])).forms['model-form']
        form['name'] = model_name
        form.submit()
    assert resource.model_set.count() == 3

    response = app.get(reverse('dynamic-resource-detail', args=[resource.dataset.pk, version.pk, resource.pk, "TestModel", "jsonl"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/jsonl'
    assert list(response.context['resource']['models']) == list(resource.model_set.all())
    assert response.context['format'] == 'JSONL'
    assert response.context['resource']['dataset'] == resource.dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_csv_multiple_models(app: DjangoTestApp):
    version = VersionFactory()
    resource = DatasetDistributionFactory(dataset=version.dataset, uapi_format=True, metadata_version=version)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    for model_name in ["TestModel", "TestModel2", "TestModel3"]:
        form = app.get(reverse('resource-model-create', args=[resource.dataset.pk, version.pk, resource.pk])).forms['model-form']
        form['name'] = model_name
        form.submit()
    assert resource.model_set.count() == 3

    response = app.get(reverse('dynamic-resource-detail', args=[resource.dataset.pk, version.pk, resource.pk, "TestModel", "csv"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:format/csv'
    assert str(response.context['resource']['models'][0]) == "TestModel"
    assert response.context['format'] == 'CSV'
    assert response.context['resource']['dataset'] == resource.dataset

    response = app.get(reverse('dynamic-resource-detail', args=[resource.dataset.pk, version.pk, resource.pk, "TestModel2", "csv"]))
    assert response.status_code == 200
    assert str(response.context['resource']['models'][0]) == "TestModel2"

    response = app.get(reverse('dynamic-resource-detail', args=[resource.dataset.pk, version.pk, resource.pk, "TestModel3", "csv"]))
    assert response.status_code == 200
    assert str(response.context['resource']['models'][0]) == "TestModel3"


@pytest.mark.django_db
def test_create_distribution_with_invalid_url(app: DjangoTestApp):
    dataset = DatasetFactory()
    file_format = FileFormat(extension='URL')
    user = UserFactory(is_staff=True, organization=dataset.organization)
    app.set_user(user)
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'Added title'
    form['description'] = 'Added new resource description'
    form['format'] = file_format.id
    form['download_url'] = "invalid"
    resp = form.submit()
    assert 'Įveskite tinkamą URL adresą.' in list(resp.context['form'].errors['download_url'])


@pytest.mark.django_db
def test_create_distribution__translation(app: DjangoTestApp):
    dataset = DatasetFactory()
    version = VersionFactory(dataset=dataset)
    file_format = FileFormat(extension='URL')
    user = UserFactory(is_staff=True, organization=dataset.organization)
    app.set_user(user)
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk}) + "?language=lt").forms['resource-form']
    form['title'] = 'Pavadinimas'
    form['description'] = 'Aprašymas'
    form['format'] = file_format.id
    form['download_url'] = "www.google.lt"
    form['metadata_version'] = version.pk
    resp = form.submit()
    assert resp.status_code == 302
    assert DatasetDistribution.objects.count() == 1
    distribution = DatasetDistribution.objects.first()
    distribution.set_current_language("lt")
    assert distribution.title == "Pavadinimas"
    assert distribution.description == "Aprašymas"
    distribution.set_current_language("en")
    assert distribution.title == "Title"
    assert distribution.description == "Description"


@pytest.mark.django_db
def test_update_distribution__translation(app: DjangoTestApp):
    version = VersionFactory()
    distribution = DatasetDistributionFactory(dataset=version.dataset, title="", description="", metadata_version=version)
    user = UserFactory(is_staff=True, organization=distribution.dataset.organization)
    app.set_user(user)
    form = app.get(reverse('resource-change', kwargs={'pk': distribution.pk, 'version_id': version.pk}) + "?language=lt").forms['resource-form']
    form['title'] = 'Pavadinimas'
    form['description'] = 'Aprašymas'
    form['metadata_version'] = version.pk
    resp = form.submit()
    distribution.refresh_from_db()
    assert resp.status_code == 302
    distribution.set_current_language("lt")
    assert distribution.title == "Pavadinimas"
    assert distribution.description == "Aprašymas"
    distribution.set_current_language("en")
    assert distribution.title == "Title"
    assert distribution.description == "Description"


@pytest.mark.django_db
def test_update_distribution__existing_translation(app: DjangoTestApp):
    distribution = DatasetDistributionFactory()
    user = UserFactory(is_staff=True, organization=distribution.dataset.organization)
    app.set_user(user)
    form = app.get(reverse('resource-change', kwargs={'pk': distribution.pk, 'version_id': distribution.metadata_version.pk}) + "?language=lt").forms['resource-form']
    form['title'] = 'Pavadinimas'
    form['description'] = 'Aprašymas'
    form['metadata_version'] = distribution.metadata_version.pk
    resp = form.submit()
    assert resp.status_code == 302

    form = app.get(reverse('resource-change', kwargs={'pk': distribution.pk, 'version_id': distribution.metadata_version.pk}) + "?language=en").forms['resource-form']
    form['title'] = 'Title'
    form['description'] = 'Description'
    form['metadata_version'] = distribution.metadata_version.pk
    resp = form.submit()

    distribution.refresh_from_db()
    assert resp.status_code == 302
    distribution.set_current_language("lt")
    assert distribution.title == "Pavadinimas"
    assert distribution.description == "Aprašymas"
    distribution.set_current_language("en")
    assert distribution.title == "Title"
    assert distribution.description == "Description"


@pytest.mark.django_db
def test_distribution_with_compression_and_packaging_formats(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = VersionFactory(dataset=dataset)
    file_format = FileFormat()
    compression_format = CompressionFormatFactory()
    packaging_format = PackagingFormatFactory()

    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    breakpoint()
    form['title'] = 'New resource'
    form['format'] = file_format.pk
    form['download_url'] = "http://www.test.com"
    form['compression_format'] = compression_format.pk
    form['packaging_format'] = packaging_format.pk
    form['metadata_version'] = version.pk
    form.submit()

    assert DatasetDistribution.objects.count() == 1
    distribution = DatasetDistribution.objects.first()
    assert distribution.compression_format == compression_format
    assert distribution.packaging_format == packaging_format


@pytest.mark.django_db
def test_create_distribution_without_access_download_urls_and_file(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    version = VersionFactory(dataset=dataset)
    file_format = FileFormat()

    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'New resource'
    form['format'] = file_format.pk
    form['metadata_version'] = version.pk
    resp = form.submit()

    assert len(resp.context['form'].errors) == 3
    assert resp.context['form'].errors['access_url'] == ['Pateikite duomenų prieigos nuorodą.']
    assert resp.context['form'].errors['download_url'] == ['Arba pateikite duomenų atsisiuntimo nuorodą.']
    assert resp.context['form'].errors['file'] == ['Arba įkelkite duomenų failą.']


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_rdf(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    version = VersionFactory(dataset=dataset)
    resource = DatasetDistributionFactory(uapi_format=True)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse('resource-model-create', args=[dataset.pk, version.pk, resource.pk])).forms['model-form']
    form['name'] = "TestModel"
    form.submit()
    assert resource.model_set.first().name == 'TestModel'

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, version.pk, resource.pk, "TestModel", "rdf"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/rdf'
    assert list(response.context['resource']['models']) == list(resource.model_set.all())
    assert response.context['format'] == 'RDF'
    assert response.context['resource']['dataset'] == dataset


@pytest.mark.django_db
def test_distribution_form_status_options(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    response = app.get(reverse("resource-add", args=[dataset.pk]))
    form = response.forms["resource-form"]

    assert response.status_code == 200

    status_select = form.fields['status'][0]
    values = [value for _, _, value in status_select.options]
    assert values == ["Įgyvendintas – veikiantis", "Kuriamas", "Kūrimas suplanuotas", "Pasenęs", "Atsisakytas",]

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from unittest.mock import patch

from vitrina import settings
from vitrina.classifiers.factories import ApplicableLegislationFactory
from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.resources.factories import (
    DatasetDistributionFactory,
    FileFormat,
    CompressionFormatFactory,
    PackagingFormatFactory,
)
from vitrina.resources.models import DatasetDistribution
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure.factories import MetadataFactory, ModelFactory, VersionFactory
from vitrina.structure import VersionStatus
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_change_form_wrong_login(app: DjangoTestApp, is_versioned: bool):
    resource = DatasetDistributionFactory()
    if is_versioned:
        ModelFactory(dataset=resource.dataset, distribution=resource)
        resource_change_url = reverse('resource-change', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk})
    else:
        resource_change_url = reverse('resource-change-no-version', kwargs={'pk': resource.id})

    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(resource_change_url)
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location

@pytest.mark.parametrize("status", [s for s in VersionStatus.values if s != VersionStatus.DRAFT])
@pytest.mark.django_db
def test_change_form_in_not_draft_version_not_allowed(app: DjangoTestApp, status: str):
    resource = DatasetDistributionFactory()
    ModelFactory(dataset=resource.dataset, distribution=resource)
    resource.metadata_version.status = status
    resource.metadata_version.save()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    response = app.get(reverse('resource-change', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk}), expect_errors=True)
    assert response.status_code == 302
    assert response.location == resource.get_absolute_url()

@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_change_form_correct_login(app: DjangoTestApp, is_versioned: bool):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    if is_versioned:
        ModelFactory(dataset=resource.dataset, distribution=resource)
        resource_change_url = reverse('resource-change', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk})
        expected_url = reverse('resource-detail', args=[resource.dataset.pk, resource.metadata_version.pk, resource.pk])
        expected_metadata_rows = 1
    else:
        resource_change_url = reverse('resource-change-no-version', kwargs={'pk': resource.id})
        expected_url = reverse('resource-detail-no-version', args=[resource.dataset.pk, resource.pk])
        expected_metadata_rows = 0

    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    form = app.get(resource_change_url).forms['resource-form']
    form['title'] = "Edited title"
    form['description'] = "edited resource description"
    form['level'] = 2
    resp = form.submit()
    resource.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == expected_url
    assert resource.title == 'Edited title'
    assert resource.description == 'edited resource description'
    assert resource.metadata.count() == expected_metadata_rows
    assert resource.name.startswith('resource')
    assert resource.title == "Edited title"
    assert resource.description == "edited resource description"
    assert resource.level == 2


@pytest.mark.django_db
def test_click_edit_button(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    response = app.get(reverse('dataset-detail', kwargs={'pk': resource.dataset_id})).follow()
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
    form['level'] = 1
    resp = form.submit()
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 1
    assert DatasetDistribution.objects.first().metadata.count() == 0
    assert DatasetDistribution.objects.first().name == 'resource1'
    assert DatasetDistribution.objects.first().title == 'Added title'
    assert DatasetDistribution.objects.first().description == 'Added new resource description'
    assert DatasetDistribution.objects.first().level == 1


@pytest.mark.django_db
def test_create_dataset_distribution_with_applicable_legislation(app: DjangoTestApp):
    dataset = DatasetFactory()
    file_format = FileFormat(extension='URL')
    user = UserFactory(is_staff=True, organization=dataset.organization)
    applicable_legislation_urls = ["http://www.google.com", "http://www.example.com"]
    app.set_user(user) 
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['format'] = file_format.id
    form['download_url'] = "www.google.lt"
    form["applicable_legislation"] = applicable_legislation_urls
    with patch("vitrina.datasets.tasks.update_applicable_legislation_description.delay") as mocked_task:
            resp = form.submit()

    assert resp.status_code == 302
    assert mocked_task.call_count == 1
    dataset_distribution = DatasetDistribution.objects.get()
    assert set(dataset_distribution.applicable_legislation.values_list("url", flat=True)) == set(applicable_legislation_urls)


@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_update_dataset_distribution_with_applicable_legislation(app: DjangoTestApp, is_versioned: bool):
    resource = DatasetDistributionFactory(title='base title', description='base description')

    if is_versioned:
        ModelFactory(dataset=resource.dataset, distribution=resource)
        resource_change_url = reverse('resource-change', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk})
    else:
        resource_change_url = reverse('resource-change-no-version', kwargs={'pk': resource.id})

    resource.applicable_legislation.set(ApplicableLegislationFactory.create_batch(4))
    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    form = app.get(resource_change_url).forms['resource-form']
    new_urls = ("http://www.google.", "http://www.example.com")
    for i, field in enumerate(form.fields["applicable_legislation"]):
        field.value = new_urls[i] if i < len(new_urls) else ""

    with patch("vitrina.datasets.tasks.update_applicable_legislation_description.delay") as mocked_task:
        resp = form.submit()
        
    resource.refresh_from_db()
    assert resp.status_code == 302
    assert mocked_task.call_count == 1
    dataset_distribution = DatasetDistribution.objects.get()
    assert set(dataset_distribution.applicable_legislation.values_list("url", flat=True)) == set(new_urls)


@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_change_form_data_gov_url_upload_checked(app: DjangoTestApp, is_versioned: bool):
    file_format = FileFormat(title='URL', extension='URL')
    resource = DatasetDistributionFactory(title='base title', description='base description',
                                          format=file_format, file=None)
    if is_versioned:
        ModelFactory(dataset=resource.dataset, distribution=resource)
        resource_change_url = reverse('resource-change', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk})
    else:
        resource_change_url = reverse('resource-change-no-version', kwargs={'pk': resource.id})

    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(resource_change_url).forms['resource-form']
    form['download_url'] = 'get.data.gov.lt'
    resp = form.submit()
    resource.refresh_from_db()
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 1
    assert resource.upload_to_storage is True


@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_change_form_upload_checked(app: DjangoTestApp, is_versioned: bool):
    resource = DatasetDistributionFactory(title='base title', description='base description')

    if is_versioned:
        ModelFactory(dataset=resource.dataset, distribution=resource)
        resource_change_url = reverse('resource-change', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk})
    else:
        resource_change_url = reverse('resource-change-no-version', kwargs={'pk': resource.id})

    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(resource_change_url).forms['resource-form']
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
    response = app.get(reverse('dataset-detail', kwargs={'pk': resource.dataset_id})).follow()
    response.click(linkid='add_resource')
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_delete_no_login(app: DjangoTestApp, is_versioned: bool):
    resource = DatasetDistributionFactory()

    if is_versioned:
        ModelFactory(dataset=resource.dataset, distribution=resource)
        resource_delete_url = reverse('resource-delete', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk})
    else:
        resource_delete_url = reverse('resource-delete-no-version', kwargs={'pk': resource.id})

    response = app.get(resource_delete_url)
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_delete_wrong_login(app: DjangoTestApp, is_versioned: bool):
    user = UserFactory()
    app.set_user(user)
    resource = DatasetDistributionFactory()

    if is_versioned:
        ModelFactory(dataset=resource.dataset, distribution=resource)
        resource_delete_url = reverse('resource-delete', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk})
    else:
        resource_delete_url = reverse('resource-delete-no-version', kwargs={'pk': resource.id})

    response = app.get(resource_delete_url)
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location

@pytest.mark.parametrize("status", [s for s in VersionStatus.values if s != VersionStatus.DRAFT])
@pytest.mark.django_db
def test_delete_resource_version_not_draft(app: DjangoTestApp, status: str):
    resource = DatasetDistributionFactory()
    ModelFactory(dataset=resource.dataset, distribution=resource)
    resource.metadata_version.status = status
    resource.metadata_version.save()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    response = app.get(
        reverse('resource-delete', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk}),
        expect_errors=True)
    assert response.status_code == 302
    assert response.location == resource.get_absolute_url()


@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_delete_correct_login(app: DjangoTestApp, is_versioned: bool):
    resource = DatasetDistributionFactory(title='base title', description='base description')

    if is_versioned:
        ModelFactory(dataset=resource.dataset, distribution=resource)
        resource_delete_url = reverse('resource-delete', kwargs={'pk': resource.id, 'version_id': resource.metadata_version.pk})
    else:
        resource_delete_url = reverse('resource-delete-no-version', kwargs={'pk': resource.id})

    user = UserFactory(is_staff=True, organization=resource.dataset.organization)
    app.set_user(user)
    resp = app.post(resource_delete_url)
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_detail_tab_from_resource_detail_view(app: DjangoTestApp, is_versioned: bool):
    resource = DatasetDistributionFactory()

    if is_versioned:
        metadata_version = VersionFactory(dataset=resource.dataset)
        ModelFactory(dataset=resource.dataset, distribution=resource, metadata_version=metadata_version)
        resource_detail_url = reverse('resource-detail', kwargs={'pk': resource.dataset.id, 'version_id': resource.metadata_version.pk, 'resource_id': resource.pk})
    else:
        resource_detail_url = reverse('resource-detail-no-version', kwargs={'pk': resource.dataset.id, 'resource_id': resource.pk})

    resp = app.get(resource_detail_url)
    resp = resp.click(linkid='detail_tab')
    assert resp.request.path == resource.dataset.get_absolute_url()


@pytest.mark.django_db
def test_child_resources_tab_from_resource_detail_view_uses_dataset(
    app: DjangoTestApp,
):
    resource = DatasetDistributionFactory()
    response = app.get(reverse("resource-detail-no-version", args=[resource.dataset.pk, resource.pk]))
    child_resources_response = response.click(linkid="child_resources_tab")
    assert child_resources_response.request.path == reverse(
        "dataset-child-resources",
        args=[resource.dataset.pk],
    )


@pytest.mark.django_db
def test_create_resource_model(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    resource = DatasetDistributionFactory()
    metadata_version = VersionFactory(dataset=resource.dataset)
    ModelFactory(dataset=resource.dataset, distribution=resource, metadata_version=metadata_version)
    form = app.get(reverse('resource-model-create', args=[resource.dataset.pk, resource.metadata_version.pk, resource.pk])).forms['model-form']
    form['name'] = "TestModel"
    resp = form.submit()
    assert resp.url == resource.get_absolute_url()
    assert resource.model_set.count() == 2
    assert resource.model_set.last().name == 'TestModel'


@pytest.mark.django_db
def test_create_resource_without_name(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    resource = DatasetDistributionFactory()
    resource_name_number = resource.name.split("resource")[-1]
    dataset = resource.dataset
    format = FileFormat(extension='URL')
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'New resource'
    form['format'] = format.pk
    form['download_url'] = "www.test.com"
    resp = form.submit()
    new_resource = DatasetDistribution.objects.exclude(pk=resource.pk)
    assert resp.url == new_resource.first().get_absolute_url()
    assert new_resource.count() == 1
    assert new_resource.first().metadata.count() == 0
    assert new_resource.first().name == f'resource{int(resource_name_number) + 1}'


@pytest.mark.django_db
def test_create_resource_with_existing_download_url(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
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
    resp = form.submit()
    assert list(resp.context['form'].errors.values()) == [[
        'Duomenų šaltinis su šia atsisiuntimo nuoroda jau egzistuoja.'
    ]]


@pytest.mark.django_db
@pytest.mark.parametrize("is_versioned", [True, False])
def test_distribution_detail_with_non_public_dataset_without_access(app: DjangoTestApp, is_versioned: bool):
    dataset = DatasetFactory(is_public=False)
    resource = DatasetDistributionFactory(dataset=dataset)

    if is_versioned:
        metadata_version = VersionFactory(dataset=resource.dataset)
        ModelFactory(dataset=resource.dataset, distribution=resource, metadata_version=metadata_version)
        resource_detail_url = reverse('resource-detail', kwargs={'pk': resource.dataset.id, 'version_id': resource.metadata_version.pk, 'resource_id': resource.pk})
    else:
        resource_detail_url = reverse('resource-detail-no-version', kwargs={'pk': resource.dataset.id, 'resource_id': resource.pk})

    user = UserFactory()
    app.set_user(user)
    response = app.get(resource_detail_url, expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_versioned",
    [True, False],
)
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_distribution_detail_with_non_public_dataset_with_access(
    app: DjangoTestApp, is_versioned: bool, role: str
):
    dataset = DatasetFactory(is_public=False)
    resource = DatasetDistributionFactory(dataset=dataset)

    if is_versioned:
        metadata_version = VersionFactory(dataset=resource.dataset)
        ModelFactory(dataset=resource.dataset, distribution=resource, metadata_version=metadata_version)
        resource_detail_url = reverse('resource-detail', kwargs={'pk': resource.dataset.id, 'version_id': resource.metadata_version.pk, 'resource_id': resource.pk})
    else:
        resource_detail_url = reverse('resource-detail-no-version', kwargs={'pk': resource.dataset.id, 'resource_id': resource.pk})

    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=role,

    )
    app.set_user(user)
    response = app.get(resource_detail_url)
    assert response.context['object'] == resource


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_json(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    metadata_version = dataset.metadata.first().metadata_version
    resource = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        name="TestModel",
        metadata_version=metadata_version
        )

    user = UserFactory(is_staff=True)
    app.set_user(user)

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, metadata_version.pk, resource.pk, "TestModel", "json"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/json'
    assert list(response.context['resource']['models']) == list(dataset.model_set.all())
    assert response.context['format'] == 'JSON'
    assert response.context['resource']['dataset'] == dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_jsonl(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    metadata_version = dataset.metadata.first().metadata_version
    resource = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        name="TestModel",
        metadata_version=metadata_version
        )

    user = UserFactory(is_staff=True)
    app.set_user(user)

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, metadata_version.pk, resource.pk, "TestModel", "jsonl"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/jsonl'
    assert list(response.context['resource']['models']) == list(dataset.model_set.all())
    assert response.context['format'] == 'JSONL'
    assert response.context['resource']['dataset'] == dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_csv(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    metadata_version = dataset.metadata.first().metadata_version
    resource = DatasetDistributionFactory(uapi_format=True)
    model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        name="TestModel",
        metadata_version=metadata_version
        )

    user = UserFactory(is_staff=True)
    app.set_user(user)

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, metadata_version.pk, resource.pk, "TestModel", "csv"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:format/csv'
    assert list(response.context['resource']['models']) == list(dataset.model_set.all())
    assert response.context['format'] == 'CSV'
    assert response.context['resource']['dataset'] == dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_json_multiple_models(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    metadata_version = dataset.metadata.first().metadata_version
    resource = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        name="TestModel",
        metadata_version=metadata_version
    )
    model2 = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model2),
        object_id=model2.pk,
        name="TestModel2",
        metadata_version=metadata_version
    )
    model3 = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model3),
        object_id=model3.pk,
        name="TestModel3",
        metadata_version=metadata_version
    )

    user = UserFactory(is_staff=True)
    app.set_user(user)

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, metadata_version.pk, resource.pk, "TestModel", "json"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/json'
    assert list(response.context['resource']['models']) == list(dataset.model_set.all())
    assert response.context['format'] == 'JSON'
    assert response.context['resource']['dataset'] == resource.dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_jsonl_multiple_models(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    metadata_version = dataset.metadata.first().metadata_version
    resource = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        name="TestModel",
        metadata_version=metadata_version
    )
    model2 = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model2),
        object_id=model2.pk,
        name="TestModel2",
        metadata_version=metadata_version
    )
    model3 = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model3),
        object_id=model3.pk,
        name="TestModel3",
        metadata_version=metadata_version
    )

    user = UserFactory(is_staff=True)
    app.set_user(user)

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, metadata_version.pk, resource.pk, "TestModel", "jsonl"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/jsonl'
    assert list(response.context['resource']['models']) == list(dataset.model_set.all())
    assert response.context['format'] == 'JSONL'
    assert response.context['resource']['dataset'] == resource.dataset


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_csv_multiple_models(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    metadata_version = dataset.metadata.first().metadata_version
    resource = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        name="TestModel",
        metadata_version=metadata_version
    )
    model2 = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model2),
        object_id=model2.pk,
        name="TestModel2",
        metadata_version=metadata_version
    )
    model3 = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model3),
        object_id=model3.pk,
        name="TestModel3",
        metadata_version=metadata_version
    )

    user = UserFactory(is_staff=True)
    app.set_user(user)

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, metadata_version.pk, resource.pk, "TestModel", "csv"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:format/csv'
    assert str(response.context['resource']['models'][0]) == "TestModel"
    assert response.context['format'] == 'CSV'
    assert response.context['resource']['dataset'] == resource.dataset

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, metadata_version.pk, resource.pk, "TestModel2", "csv"]))
    assert response.status_code == 200
    assert str(response.context['resource']['models'][0]) == "TestModel2"

    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, metadata_version.pk, resource.pk, "TestModel3", "csv"]))
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
    file_format = FileFormat(extension='URL')
    user = UserFactory(is_staff=True, organization=dataset.organization)
    app.set_user(user)
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk}) + "?language=lt").forms['resource-form']
    form['title'] = 'Pavadinimas'
    form['description'] = 'Aprašymas'
    form['format'] = file_format.id
    form['download_url'] = "www.google.lt"
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
@pytest.mark.parametrize("is_versioned", [True, False])
def test_update_distribution__translation(app: DjangoTestApp, is_versioned: bool):
    distribution = DatasetDistributionFactory(title="", description="")

    if is_versioned:
        ModelFactory(dataset=distribution.dataset, distribution=distribution)
        resource_change_url = reverse('resource-change', kwargs={'pk': distribution.id, 'version_id': distribution.metadata_version.pk})
    else:
        resource_change_url = reverse('resource-change-no-version', kwargs={'pk': distribution.id})

    user = UserFactory(is_staff=True, organization=distribution.dataset.organization)
    app.set_user(user)
    form = app.get(resource_change_url + "?language=lt").forms['resource-form']
    form['title'] = 'Pavadinimas'
    form['description'] = 'Aprašymas'
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
@pytest.mark.parametrize("is_versioned", [True, False])
def test_update_distribution__existing_translation(app: DjangoTestApp, is_versioned: bool):
    distribution = DatasetDistributionFactory()
    if is_versioned:
        ModelFactory(dataset=distribution.dataset, distribution=distribution)
        resource_change_url = reverse('resource-change', kwargs={'pk': distribution.id, 'version_id': distribution.metadata_version.pk})
    else:
        resource_change_url = reverse('resource-change-no-version', kwargs={'pk': distribution.id})

    user = UserFactory(is_staff=True, organization=distribution.dataset.organization)
    app.set_user(user)
    form = app.get(resource_change_url + "?language=lt").forms['resource-form']
    form['title'] = 'Pavadinimas'
    form['description'] = 'Aprašymas'
    resp = form.submit()
    assert resp.status_code == 302

    form = app.get(resource_change_url + "?language=en").forms['resource-form']
    form['title'] = 'Title'
    form['description'] = 'Description'
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
    file_format = FileFormat()
    compression_format = CompressionFormatFactory()
    packaging_format = PackagingFormatFactory()

    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'New resource'
    form['format'] = file_format.pk
    form['download_url'] = "http://www.test.com"
    form['compression_format'] = compression_format.pk
    form['packaging_format'] = packaging_format.pk
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
    file_format = FileFormat()

    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'New resource'
    form['format'] = file_format.pk
    resp = form.submit()

    assert len(resp.context['form'].errors) == 3
    assert resp.context['form'].errors['access_url'] == ['Pateikite duomenų prieigos nuorodą.']
    assert resp.context['form'].errors['download_url'] == ['Arba pateikite duomenų atsisiuntimo nuorodą.']
    assert resp.context['form'].errors['file'] == ['Arba įkelkite duomenų failą.']


@pytest.mark.django_db
def test_distribution_detail_dynamic_resource_rdf(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True)
    resource = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    metadata_version = dataset.metadata.first().metadata_version
    model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        name="TestModel",
        metadata_version=metadata_version
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    response = app.get(reverse('dynamic-resource-detail', args=[dataset.pk, metadata_version.pk, resource.pk, "TestModel", "rdf"]))
    assert response.status_code == 200
    assert response.context['resource']['title'] == "TestModel"
    assert response.context['resource']['get_download_url'] == f'{SPINTA_SERVER_URL}/TestModel/:all/:format/rdf'
    assert list(response.context['resource']['models']) == list(dataset.model_set.all())
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

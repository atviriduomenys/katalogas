import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from hitcount.models import HitCount

from vitrina.classifiers.factories import CategoryFactory
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.likes.models import Like
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat, UapiFormat
from vitrina.structure.factories import ModelFactory
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_dataset_list_shows_the_real_hit_count(app: DjangoTestApp):
    dataset = DatasetFactory()
    HitCount.objects.create(
        content_type=ContentType.objects.get_for_model(Dataset),
        object_pk=dataset.pk,
        hits=4471,
    )

    response = app.get(reverse("dataset-list"))

    assert response.context["object_list"][0].hit_count == 4471
    assert "4471" in response.text


@pytest.mark.django_db
def test_dataset_list_shows_the_real_like_count(app: DjangoTestApp):
    dataset = DatasetFactory()
    content_type = ContentType.objects.get_for_model(Dataset)
    for _ in range(3):
        Like.objects.create(content_type=content_type, object_id=dataset.pk, user=UserFactory())

    response = app.get(reverse("dataset-list"))

    assert response.context["object_list"][0].like_count == 3


@pytest.mark.django_db
def test_dataset_list_shows_the_dataservice_formats(app: DjangoTestApp):
    for title in ["CSV", "JSON", "JSONL"]:
        FileFormat(title=title, extension=title)
    dataset = DatasetFactory()
    DatasetDistributionFactory(dataset=dataset, format=UapiFormat())
    ModelFactory(metadata_version__dataset=dataset)

    response = app.get(reverse("dataset-list"))

    shown = [str(fmt) for fmt in response.context["object_list"][0].display_formats]
    assert shown == [str(fmt) for fmt in dataset.distinct_formats]
    assert {"CSV", "JSON", "JSONL"}.issubset(set(shown))


@pytest.mark.django_db
def test_dataset_list_shows_the_root_category_icon(app: DjangoTestApp):
    root = CategoryFactory(title="Aplinka", icon="cloud-sun")
    dataset = DatasetFactory(category=[root.add_child(title="Oras", featured=False)])

    response = app.get(reverse("dataset-list"))

    assert response.context["object_list"][0].icon == dataset.get_icon() == "cloud-sun"
    assert "fa-cloud-sun" in response.text


@pytest.mark.django_db
def test_dataset_list_icon_keeps_the_first_root_by_title(app: DjangoTestApp):
    first = CategoryFactory(title="Aplinka", icon="")
    second = CategoryFactory(title="Energetika", icon="bolt")
    dataset = DatasetFactory(category=[first, second])

    response = app.get(reverse("dataset-list"))

    assert response.context["object_list"][0].icon == dataset.get_icon() == ""


@pytest.mark.django_db
def test_dataset_list_icon_is_none_without_a_category(app: DjangoTestApp):
    dataset = DatasetFactory()

    response = app.get(reverse("dataset-list"))

    assert response.context["object_list"][0].icon == dataset.get_icon() is None

from datetime import datetime, date, timedelta

import pytz
import webtest
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.urls import reverse
from django_webtest import DjangoTestApp

import pytest
from factory.django import FileField
from filer.models import File
from reversion.models import Version
from webtest import Upload

from vitrina.catalogs.factories import CatalogFactory
from vitrina.classifiers.factories import (
    CategoryFactory,
    FrequencyFactory,
    AreaOfManagementFactory,
    ConceptSchemaFactory,
    ConceptFactory,
)
from vitrina.classifiers.factories import LicenceFactory
from vitrina.classifiers.models import Category, AreaOfManagement
from vitrina.comments.models import Comment
from vitrina.datasets.factories import (
    DatasetFactory,
    DatasetStructureFactory,
    DatasetGroupFactory,
    AttributionFactory,
    DatasetAttributionFactory,
    TypeFactory,
    RelationFactory,
    DatasetRelationFactory,
    ContactFactory,
    DCATResourceSubclassFactory,
)
from vitrina.datasets.factories import MANIFEST
from vitrina.datasets.forms import (
    ResourceForm,
    ServiceResourceForm,
    BaseResourceForm,
    InformationSystemResourceForm,
)
from vitrina.datasets.models import Dataset, DatasetStructure, Contact, Type, Relation
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.plans.factories import PlanFactory
from vitrina.plans.models import Plan, PlanDataset
from vitrina.projects.factories import ProjectFactory
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure.factories import ModelFactory, MetadataFactory
from vitrina.testing.templates import strip_empty_lines
from vitrina.users.factories import UserFactory, ManagerFactory
from vitrina.users.models import User
from vitrina.identifiers.factories import AgencyFactory, IdentifierFactory
from vitrina.identifiers.models import Identifier

timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.fixture
def dataset_detail_data():
    dataset = DatasetFactory()
    dataset_distribution = DatasetDistributionFactory(dataset=dataset)
    return {
        "dataset": dataset_distribution.dataset,
        "dataset_distribution": dataset_distribution,
    }


@pytest.mark.django_db
def test_dataset_detail_without_tags(app: DjangoTestApp, dataset_detail_data):
    resp = app.get(dataset_detail_data["dataset"].get_absolute_url())
    assert resp.context["tags"] == []


@pytest.mark.django_db
def test_dataset_detail_tags(app: DjangoTestApp, dataset_detail_data):
    dataset = DatasetFactory(tags=("tag-1", "tag-2", "tag-3"), status="HAS_DATA")
    resp = app.get(dataset.get_absolute_url())
    assert len(resp.context["tags"]) == 3
    assert resp.context["tags"] == [
        {"name": "tag-1", "pk": dataset.tags.get(name="tag-1").pk},
        {"name": "tag-2", "pk": dataset.tags.get(name="tag-2").pk},
        {"name": "tag-3", "pk": dataset.tags.get(name="tag-3").pk},
    ]


@pytest.mark.django_db
def test_dataset_detail_status(app: DjangoTestApp, dataset_detail_data):
    resp = app.get(dataset_detail_data["dataset"].get_absolute_url())
    assert resp.context["status"] == "Atvertas"


@pytest.mark.django_db
def test_dataset_detail_resources(app: DjangoTestApp, dataset_detail_data):
    resp = app.get(dataset_detail_data["dataset"].get_absolute_url())
    assert list(resp.context["resources"]) == [
        dataset_detail_data["dataset_distribution"]
    ]


@pytest.mark.django_db
def test_distribution_preview(app: DjangoTestApp, dataset_detail_data):
    resp = app.get(
        reverse(
            "dataset-distribution-preview",
            kwargs={
                "dataset_id": dataset_detail_data["dataset"].pk,
                "distribution_id": dataset_detail_data["dataset_distribution"].pk,
            },
        )
    )
    assert resp.json == {"data": [["Column"], ["Value"]]}


@pytest.fixture
def search_datasets():
    cat_parent1 = CategoryFactory(title="parent1")
    cat_parent2 = CategoryFactory(title="parent2")
    cat_child = cat_parent1.add_child(
        instance=CategoryFactory.build(title="child1"),
    )
    dataset1 = DatasetFactory(
        slug="ds1",
        published=timezone.localize(datetime(2022, 6, 1)),
        tags=("test_tag_1", "test_tag_2"),
    )
    dataset1.category.add(cat_parent1)
    dataset1.set_current_language("en")
    dataset1.title = "Dataset 1"
    dataset1.description = "Description 1"
    dataset1.save()
    dataset1.set_current_language("lt")
    dataset1.title = "Duomenų rinkinys vienas"
    dataset1.description = "test_lt_desc 1"
    dataset1.save()

    dataset2 = DatasetFactory(
        slug="ds2",
        published=timezone.localize(datetime(2022, 8, 1)),
        tags=("test_tag_2", "test_tag_3"),
    )
    dataset2.category.add(cat_parent2)
    dataset2.set_current_language("en")
    dataset2.title = "Dataset 2"
    dataset2.description = "Description 2"
    dataset2.save()
    dataset2.set_current_language("lt")
    dataset2.title = "Duomenų rinkinys du\"<'>\\"
    dataset2.description = "test_lt_desc 2"
    dataset2.save()

    dataset3 = DatasetFactory(
        slug="ds3",
        published=timezone.localize(datetime(2022, 7, 1)),
        tags=("test_tag_4", "test_tag_5"),
    )
    dataset3.category.add(cat_child)
    dataset3.set_current_language("en")
    dataset3.title = "Dataset 3"
    dataset3.description = "Description 3"
    dataset3.save()
    dataset3.set_current_language("lt")
    dataset3.title = "Duomenų rinkinys trys"
    dataset3.description = "test_lt_desc 3"
    dataset3.save()
    return [dataset1, dataset2, dataset3]


@pytest.mark.haystack
def test_dataset_list_view_anon_user_with_datasets(app: DjangoTestApp):
    DatasetFactory()
    DatasetFactory()
    DatasetFactory()
    resp = app.get(reverse("dataset-list"))
    assert len(resp.context["object_list"]) == 3


@pytest.mark.haystack
def test_dataset_list_view_anon_user_without_datasets(app: DjangoTestApp):
    resp = app.get(reverse("dataset-list"))
    assert len(resp.context["object_list"]) == 0


@pytest.mark.haystack
def test_dataset_list_view_all_shown_for_staff(app: DjangoTestApp):
    org1 = OrganizationFactory()
    org2 = OrganizationFactory()
    DatasetFactory(organization=org1, is_public=False)
    DatasetFactory(organization=org1)
    DatasetFactory(organization=org2)
    DatasetFactory(organization=org2, is_public=False)
    user = UserFactory(is_staff=True)
    app.set_user(user)
    resp = app.get(reverse("dataset-list"))
    assert len(resp.context["object_list"]) == 4


@pytest.mark.haystack
def test_dataset_list_view_public_shown_for_regular_user(app: DjangoTestApp):
    org1 = OrganizationFactory()
    org2 = OrganizationFactory()
    DatasetFactory(organization=org1, is_public=False)
    DatasetFactory(organization=org1)
    DatasetFactory(organization=org2)
    DatasetFactory(organization=org2, is_public=False)
    user = UserFactory()
    app.set_user(user)
    resp = app.get(reverse("dataset-list"))
    assert len(resp.context["object_list"]) == 2


@pytest.mark.haystack
def test_org_dataset_url_is_hidden_for_anon_user(app: DjangoTestApp):
    resp = app.get(reverse("dataset-list"))
    assert not resp.html.find(id="org-dataset-url")


@pytest.mark.haystack
def test_manager_dataset_url_is_hidden_for_anon_user(app: DjangoTestApp):
    resp = app.get(reverse("dataset-list"))
    assert not resp.html.find(id="manager-dataset-url")


@pytest.mark.haystack
def test_org_dataset_url_is_hidden_for_normal_user(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    resp = app.get(reverse("dataset-list"))
    assert not resp.html.find(id="org-dataset-url")


@pytest.mark.haystack
def test_manager_dataset_url_is_hidden_for_normal_user(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    resp = app.get(reverse("dataset-list"))
    assert not resp.html.find(id="manager-dataset-url")


@pytest.mark.haystack
def test_manager_dataset_url_is_hidden_for_manager_if_no_datasets(app: DjangoTestApp):
    org = OrganizationFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=org.pk,
        role=Representative.MANAGER,
    )
    app.set_user(rep.user)
    resp = app.get(reverse("dataset-list"))
    assert not resp.html.find(id="manager-dataset-url")


@pytest.mark.haystack
def test_org_dataset_url_is_shown_for_coordinator(app: DjangoTestApp):
    org = OrganizationFactory()
    DatasetFactory(organization=org)
    user = User.objects.create_user(
        email="test@test.com", password="test123", organization=org
    )
    app.set_user(user)
    resp = app.get(reverse("dataset-list"))
    assert resp.html.find(id="org-dataset-url")


@pytest.mark.haystack
def test_manager_dataset_url_is_shown_for_manager(app: DjangoTestApp):
    org = OrganizationFactory()
    DatasetFactory(organization=org)
    ct = ContentType.objects.get_for_model(Dataset)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=org.pk,
        role=Representative.MANAGER,
    )
    app.set_user(rep.user)
    resp = app.get(reverse("dataset-list"))
    assert resp.html.find(id="manager-dataset-url")


@pytest.mark.haystack
def test_org_datasets_are_shown_for_coordinator(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(title="testt", organization=org)
    user = User.objects.create_user(
        email="test@test.com", password="test123", organization=org
    )
    app.set_user(user)
    resp = app.get(reverse("dataset-list"))
    resp = resp.click(linkid="org-dataset-url")
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [dataset.pk]


@pytest.mark.haystack
def test_manager_datasets_are_shown_for_manager(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    ct = ContentType.objects.get_for_model(Dataset)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=org.pk,
        role=Representative.MANAGER,
    )
    app.set_user(rep.user)
    resp = app.get(reverse("dataset-list"))
    resp = resp.click(linkid="manager-dataset-url")
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [dataset.pk]


@pytest.mark.haystack
def test_datasets_from_multiple_orgs_are_shown_for_manager(app: DjangoTestApp):
    org = OrganizationFactory()
    org2 = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    dataset2 = DatasetFactory(organization=org2)
    ct = ContentType.objects.get_for_model(Dataset)
    user = User.objects.create_user(email="test@test.com", password="test123")
    rep = RepresentativeFactory(
        content_type=ct, object_id=org.pk, role=Representative.MANAGER, user=user
    )
    rep2 = RepresentativeFactory(
        content_type=ct, object_id=org2.pk, role=Representative.MANAGER, user=user
    )
    app.set_user(user)
    resp = app.get(reverse("dataset-list"))
    resp = resp.click(linkid="manager-dataset-url")
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [dataset.pk, dataset2.pk]
    )


@pytest.mark.haystack
def test_search_without_query(app: DjangoTestApp, search_datasets):
    resp = app.get(reverse("dataset-list"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]
    )


@pytest.mark.haystack
def test_search_with_query_that_doesnt_match(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "doesnt-match"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == []


@pytest.mark.haystack
def test_search_with_query_that_matches_one(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "vienas"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        search_datasets[0].pk
    ]


@pytest.mark.haystack
def test_search_with_query_that_matches_all(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "rinkinys"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]
    )


@pytest.mark.haystack
def test_search_with_query_that_matches_all_with_english_title(
    app: DjangoTestApp, search_datasets
):
    for dataset in search_datasets:
        dataset.set_current_language("en")
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "Dataset"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]
    )


@pytest.mark.haystack
def test_search_with_query_that_matches_all_description(
    app: DjangoTestApp, search_datasets
):
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "test_lt_desc"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            search_datasets[0].pk,
            search_datasets[1].pk,
            search_datasets[2].pk,
        ]
    )


@pytest.mark.haystack
def test_search_with_query_that_matches_all_with_english_description(
    app: DjangoTestApp, search_datasets
):
    for dataset in search_datasets:
        dataset.set_current_language("en")
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "Description"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            search_datasets[0].pk,
            search_datasets[1].pk,
            search_datasets[2].pk,
        ]
    )


@pytest.mark.haystack
def test_search_with_query_that_matches_child_category(
    app: DjangoTestApp, search_datasets
):
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "child1"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            search_datasets[2].pk,
        ]
    )


@pytest.mark.haystack
def test_search_with_query_that_matches_category_and_parent_category(
    app: DjangoTestApp, search_datasets
):
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "parent1"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            search_datasets[0].pk,
            search_datasets[2].pk,
        ]
    )


@pytest.mark.haystack
def test_search_with_query_that_matches_tag_of_one_dataset(
    app: DjangoTestApp, search_datasets
):
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "test_tag_1"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            search_datasets[0].pk,
        ]
    )


@pytest.mark.haystack
def test_search_with_query_that_matches_tag_of_two_datasets(
    app: DjangoTestApp, search_datasets
):
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "test_tag_2"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            search_datasets[0].pk,
            search_datasets[1].pk,
        ]
    )


@pytest.fixture
def status_filter_data():
    dataset1 = DatasetFactory()
    dataset2 = DatasetFactory(status=Dataset.INVENTORED)
    return [dataset1, dataset2]


@pytest.mark.haystack
def test_status_filter_without_query(app: DjangoTestApp, status_filter_data):
    resp = app.get(reverse("dataset-list"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [status_filter_data[0].pk, status_filter_data[1].pk]
    )
    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["status"].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_status_filter_inventored(app: DjangoTestApp, status_filter_data):
    resp = app.get(
        "%s?selected_facets=status_exact:%s"
        % (reverse("dataset-list"), Dataset.INVENTORED)
    )

    objects = [int(obj.pk) for obj in resp.context["object_list"]]
    assert objects == [status_filter_data[1].pk]

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["status"].items() if i.selected]
    assert selected == [Dataset.INVENTORED]


@pytest.fixture
def organization_filter_data():
    organization = OrganizationFactory()

    dataset1 = DatasetFactory(organization=organization, slug="ds1")
    dataset2 = DatasetFactory(organization=organization, slug="ds2")

    return {"organization": organization, "datasets": [dataset1, dataset2]}


@pytest.mark.haystack
def test_organization_filter_without_query(
    app: DjangoTestApp, organization_filter_data
):
    resp = app.get(reverse("dataset-list"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            organization_filter_data["datasets"][0].pk,
            organization_filter_data["datasets"][1].pk,
        ]
    )

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["organization"].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_organization_filter_with_organization(
    app: DjangoTestApp, organization_filter_data
):
    resp = app.get(
        "%s?selected_facets=organization_exact:%s"
        % (reverse("dataset-list"), organization_filter_data["organization"].pk)
    )
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            organization_filter_data["datasets"][0].pk,
            organization_filter_data["datasets"][1].pk,
        ]
    )

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["organization"].items() if i.selected]
    assert selected == [str(organization_filter_data["organization"].pk)]


@pytest.fixture
def category_filter_data():
    organization = OrganizationFactory()

    category1 = CategoryFactory(title="Cat 1")
    category2 = category1.add_child(
        instance=CategoryFactory.build(title="Cat 1.1"),
    )
    category3 = category1.add_child(
        instance=CategoryFactory.build(title="Cat 1.2"),
    )
    category4 = category2.add_child(
        instance=CategoryFactory.build(title="Cat 2.1"),
    )
    dataset_with_category1 = DatasetFactory(slug="ds1", organization=organization)
    dataset_with_category1.category.add(category1)
    dataset_with_category1.save()
    dataset_with_category2 = DatasetFactory(slug="ds2", organization=organization)
    dataset_with_category2.category.add(category2)
    dataset_with_category2.save()
    dataset_with_category3 = DatasetFactory(slug="ds3", organization=organization)
    dataset_with_category3.category.add(category3)
    dataset_with_category3.save()
    dataset_with_category4 = DatasetFactory(slug="ds4", organization=organization)
    dataset_with_category4.category.add(category4)
    dataset_with_category4.save()

    return {
        "categories": [category1, category2, category3, category4],
        "datasets": [
            dataset_with_category1,
            dataset_with_category2,
            dataset_with_category3,
            dataset_with_category4,
        ],
    }


@pytest.mark.haystack
def test_category_filter_without_query(app: DjangoTestApp, category_filter_data):
    resp = app.get(reverse("dataset-list"))
    assert len(resp.context["object_list"]) == 4

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["category"].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_category_filter_with_parent_category(app: DjangoTestApp, category_filter_data):
    resp = app.get(
        "%s?selected_facets=category_exact:%s"
        % (reverse("dataset-list"), category_filter_data["categories"][0].pk)
    )
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            category_filter_data["datasets"][0].pk,
            category_filter_data["datasets"][1].pk,
            category_filter_data["datasets"][2].pk,
            category_filter_data["datasets"][3].pk,
        ]
    )

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["category"].items() if i.selected]
    assert selected == [str(category_filter_data["categories"][0].pk)]


@pytest.mark.haystack
def test_category_filter_with_middle_category(
    app: DjangoTestApp,
    category_filter_data: dict[str, list[Category]],
):
    resp = app.get(
        "%s?selected_facets=category_exact:%s"
        % (reverse("dataset-list"), category_filter_data["categories"][1].pk)
    )
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            category_filter_data["datasets"][1].pk,
            category_filter_data["datasets"][3].pk,
        ]
    )

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["category"].items() if i.selected]
    assert selected == [str(category_filter_data["categories"][1].pk)]


@pytest.mark.haystack
def test_category_filter_with_child_category(
    app: DjangoTestApp,
    category_filter_data: dict[str, list[Category]],
):
    resp = app.get(
        "%s?selected_facets=category_exact:%s"
        % (reverse("dataset-list"), category_filter_data["categories"][3].pk)
    )
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        category_filter_data["datasets"][3].pk,
    ]

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["category"].items() if i.selected]
    assert selected == [str(category_filter_data["categories"][3].pk)]


@pytest.mark.haystack
def test_category_filter_with_parent_and_child_category(
    app: DjangoTestApp,
    category_filter_data: dict[str, list[Category]],
):
    resp = app.get(
        ("%s?selected_facets=category_exact:%s&selected_facets=category_exact:%s")
        % (
            reverse("dataset-list"),
            category_filter_data["categories"][0].pk,
            category_filter_data["categories"][3].pk,
        )
    )
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        category_filter_data["datasets"][3].pk,
    ]

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["category"].items() if i.selected]
    assert sorted(selected) == sorted(
        [
            str(category_filter_data["categories"][0].pk),
            str(category_filter_data["categories"][3].pk),
        ]
    )


@pytest.mark.skip
@pytest.mark.haystack
def test_data_group_filter_header_visible_if_data_groups_exist(
    app: DjangoTestApp,
):
    group = DatasetGroupFactory()
    category = CategoryFactory()
    category.groups.add(group)
    dataset = DatasetFactory()
    dataset.category.add(category)
    dataset.save()
    resp = app.get(reverse("dataset-list"))
    assert resp.html.find(id="data_group_filter_header")


@pytest.mark.skip
@pytest.mark.haystack
def test_data_group_filter_header_not_visible_if_data_groups_do_not_exist(
    app: DjangoTestApp,
):
    DatasetFactory()
    resp = app.get(reverse("dataset-list"))
    assert not resp.html.find(id="data_group_filter_header")


@pytest.fixture
def datasets():
    dataset1 = DatasetFactory(tags=("tag1", "tag2", "tag3"), slug="ds1")
    dataset2 = DatasetFactory(tags=("tag3", "tag4", "tag5"), slug="ds2")

    return [dataset1, dataset2]


@pytest.mark.haystack
def test_tag_filter_without_query(app: DjangoTestApp, datasets):
    resp = app.get(reverse("dataset-list"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            datasets[0].pk,
            datasets[1].pk,
        ]
    )
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [datasets[0].pk, datasets[1].pk]
    )

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["tags"].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_tag_filter_with_one_tag(app: DjangoTestApp, datasets):
    tag_id = datasets[0].tags.get(name="tag2").pk
    resp = app.get(
        "%s?selected_facets=tags_exact:%s" % (reverse("dataset-list"), tag_id)
    )
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [datasets[0].pk]

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["tags"].items() if i.selected]
    assert selected == [str(tag_id)]


@pytest.mark.haystack
def test_tag_filter_with_shared_tag(app: DjangoTestApp, datasets):
    tag_id = datasets[0].tags.get(name="tag3").pk
    resp = app.get(
        "%s?selected_facets=tags_exact:%s" % (reverse("dataset-list"), tag_id)
    )
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [datasets[0].pk, datasets[1].pk]
    )

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["tags"].items() if i.selected]
    assert selected == [str(tag_id)]


@pytest.mark.haystack
def test_tag_filter_with_multiple_tags(app: DjangoTestApp, datasets):
    tag_id_1 = datasets[1].tags.get(name="tag3").pk
    tag_id_2 = datasets[1].tags.get(name="tag4").pk
    resp = app.get(
        "%s?selected_facets=tags_exact:%s&selected_facets=tags_exact:%s"
        % (reverse("dataset-list"), tag_id_1, tag_id_2)
    )
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [datasets[1].pk]

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["tags"].items() if i.selected]
    assert sorted(selected) == sorted([str(tag_id_1), str(tag_id_2)])


@pytest.fixture
def frequency_filter_data():
    frequency = FrequencyFactory()
    organization = OrganizationFactory()

    dataset1 = DatasetFactory(frequency=frequency, organization=organization)
    dataset2 = DatasetFactory(frequency=frequency, organization=organization)

    return {"frequency": frequency, "datasets": [dataset1, dataset2]}


@pytest.mark.haystack
def test_frequency_filter_without_query(app: DjangoTestApp, frequency_filter_data):
    resp = app.get(reverse("dataset-list"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            frequency_filter_data["datasets"][0].pk,
            frequency_filter_data["datasets"][1].pk,
        ]
    )

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["frequency"].items() if i.selected]
    assert selected == []


@pytest.mark.haystack
def test_frequency_filter_with_frequency(app: DjangoTestApp, frequency_filter_data):
    resp = app.get(
        "%s?selected_facets=frequency_exact:%s"
        % (reverse("dataset-list"), frequency_filter_data["frequency"].pk)
    )
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [
            frequency_filter_data["datasets"][0].pk,
            frequency_filter_data["datasets"][1].pk,
        ]
    )

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["frequency"].items() if i.selected]
    assert selected == [frequency_filter_data["frequency"].pk]


@pytest.fixture
def date_filter_data():
    org = OrganizationFactory()
    dataset1 = DatasetFactory(
        organization=org, slug="ds1", published=timezone.localize(datetime(2022, 3, 1))
    )
    dataset2 = DatasetFactory(
        organization=org, slug="ds2", published=timezone.localize(datetime(2022, 2, 1))
    )
    dataset3 = DatasetFactory(
        organization=org, slug="ds3", published=timezone.localize(datetime(2021, 12, 1))
    )
    return [dataset1, dataset2, dataset3]


@pytest.mark.haystack
def test_date_filter_without_query(app: DjangoTestApp, date_filter_data):
    resp = app.get(reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        date_filter_data[0].pk,
        date_filter_data[1].pk,
        date_filter_data[2].pk,
    ]
    assert resp.context["form"].cleaned_data["date_from"] is None
    assert resp.context["form"].cleaned_data["date_to"] is None


@pytest.mark.haystack
def test_date_filter_wit_date_from(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-02-10" % reverse("dataset-list"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        date_filter_data[0].pk
    ]
    assert resp.context["form"].cleaned_data["date_from"] == date(2022, 2, 10)
    assert resp.context["form"].cleaned_data["date_to"] is None


@pytest.mark.haystack
def test_date_filter_with_date_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_to=2022-02-10" % reverse("dataset-list"))
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [date_filter_data[1].pk, date_filter_data[2].pk]
    )
    assert resp.context["form"].cleaned_data["date_from"] is None
    assert resp.context["form"].cleaned_data["date_to"] == date(2022, 2, 10)


@pytest.mark.haystack
def test_date_filter_with_dates_from_and_to(app: DjangoTestApp, date_filter_data):
    resp = app.get(
        "%s?date_from=2022-01-01&date_to=2022-02-10" % reverse("dataset-list")
    )
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        date_filter_data[1].pk
    ]
    assert resp.context["form"].cleaned_data["date_from"] == date(2022, 1, 1)
    assert resp.context["form"].cleaned_data["date_to"] == date(2022, 2, 10)


@pytest.mark.haystack
def test_dataset_filter_all(app: DjangoTestApp):
    organization = OrganizationFactory()
    category = CategoryFactory()
    frequency = FrequencyFactory()
    dataset_with_all_filters = DatasetFactory(
        status=Dataset.HAS_DATA,
        tags=("tag1", "tag2", "tag3"),
        published=timezone.localize(datetime(2022, 2, 9)),
        organization=organization,
        frequency=frequency,
    )
    dataset_with_all_filters.category.add(category)

    distribution = DatasetDistributionFactory()
    distribution.dataset = dataset_with_all_filters
    distribution.save()

    dataset_with_all_filters.set_current_language(settings.LANGUAGE_CODE)
    dataset_with_all_filters.slug = "ds1"
    dataset_with_all_filters.save()

    tag_id_1 = dataset_with_all_filters.tags.get(name="tag1").pk
    tag_id_2 = dataset_with_all_filters.tags.get(name="tag2").pk

    resp = app.get(
        reverse("dataset-list")
        + "?"
        + (
            f"selected_facets=status_exact:{Dataset.HAS_DATA}&"
            f"selected_facets=organization_exact:{organization.pk}&"
            f"selected_facets=category_exact:{category.pk}&"
            f"selected_facets=tags_exact:{tag_id_1}&"
            f"selected_facets=tags_exact:{tag_id_2}&"
            f"selected_facets=frequency_exact:{frequency.pk}&"
            "date_from=2022-01-01&"
            "date_to=2022-02-10"
        )
    )

    objects = [int(obj.pk) for obj in resp.context["object_list"]]
    assert objects == [dataset_with_all_filters.pk]

    selected = _get_selected(resp.context)
    assert selected == {
        "status": Dataset.HAS_DATA,
        "organization": str(organization.pk),
        "category": str(category.pk),
        "tags": [str(tag_id_1), str(tag_id_2)],
        "frequency": frequency.pk,
        "published": [
            (2022, "Y"),
            (2022, 1, "Q"),
            (2022, 2, "M"),
        ],
    }


@pytest.mark.haystack
def test_dataset_filter_with_pages(app: DjangoTestApp):
    inventored_dataset = None
    for i in range(25):
        if i == 0:
            inventored_dataset = DatasetFactory(status=Dataset.INVENTORED)
        else:
            DatasetFactory()

    resp = app.get("%s?page=2" % (reverse("dataset-list")))

    assert "page" not in resp.html.find(id="%s_id" % Dataset.INVENTORED).attrs["href"]
    resp = resp.click(linkid="%s_id" % Dataset.INVENTORED)

    objects = [int(obj.pk) for obj in resp.context["object_list"]]
    assert objects == [inventored_dataset.pk]

    selected = _get_selected(resp.context)
    assert selected["status"] == Dataset.INVENTORED


@pytest.fixture
def dataset_structure_data():
    organization = OrganizationFactory(slug="org", kind="gov")

    dataset1 = DatasetFactory(slug="ds2", organization=organization)
    dataset1.set_current_language(settings.LANGUAGE_CODE)
    dataset1.title = "dataset1"
    dataset1.save()

    dataset2 = DatasetFactory(slug="ds3", organization=organization)
    dataset2.set_current_language(settings.LANGUAGE_CODE)
    dataset2.title = "dataset2"
    dataset2.save()

    structure1 = DatasetStructureFactory(dataset=dataset1)
    structure2 = DatasetStructureFactory(
        dataset=dataset2, file=FileField(filename="file.csv", data=b"ab\0c")
    )
    return {"structure1": structure1, "structure2": structure2}


@pytest.mark.django_db
def test_public_manager_filtering(app: DjangoTestApp):
    organization = OrganizationFactory(slug="org", kind="gov")

    DatasetFactory(is_public=False, organization=organization)
    DatasetFactory(
        deleted=True,
        deleted_on=timezone.localize(datetime.now()),
        organization=organization,
    )
    DatasetFactory(deleted=True, deleted_on=None, organization=organization)
    DatasetFactory(deleted=None, deleted_on=None, organization=organization)
    DatasetFactory(organization=organization)

    public_datasets = Dataset.public.all()
    assert public_datasets.count() == 2


@pytest.mark.django_db
def test_change_form_no_login(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    response = app.get(reverse("dataset-change", kwargs={"pk": dataset.id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_change_form_wrong_login(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org)
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(
        reverse("dataset-change", kwargs={"pk": dataset.id}), expect_errors=True
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_change_form_correct_login(app: DjangoTestApp):
    frequency = FrequencyFactory(is_default=True)
    category = CategoryFactory()
    org = OrganizationFactory()
    dataset = DatasetFactory(
        published=timezone.localize(datetime(2022, 9, 7)),
        slug="test-dataset-slug",
        description="test description",
        frequency=frequency,
        organization=org,
    )
    dataset.category.add(category)
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset.manager = user
    form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms[
        "dataset-form"
    ]
    form["title"] = "Edited title"
    form["description"] = "edited dataset description"
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse("dataset-detail", kwargs={"pk": dataset.id})
    assert dataset.title == "Edited title"
    assert dataset.description == "edited dataset description"
    assert Version.objects.get_for_object(dataset).count() == 1
    assert (
        Version.objects.get_for_object(dataset).first().revision.comment
        == Dataset.EDITED
    )
    assert dataset.metadata.count() == 1
    assert dataset.metadata.first().title == "Edited title"
    assert dataset.metadata.first().description == "edited dataset description"


@pytest.mark.django_db
def test_click_edit_button(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(
        published=timezone.localize(datetime(2022, 9, 7)),
        slug="test-dataset-slug",
        organization=org,
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset.manager = user
    response = app.get(reverse("dataset-detail", kwargs={"pk": dataset.id}))
    response.click(linkid="change_dataset")
    assert response.status_code == 200


@pytest.mark.django_db
def test_add_form_no_login(app: DjangoTestApp):
    org = OrganizationFactory()
    subclass = DCATResourceSubclassFactory()
    response = app.get(
        reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})
    )
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_add_subclass_form_no_login(app: DjangoTestApp):
    org = OrganizationFactory()
    response = app.get(reverse("resource-subclass-add", kwargs={"pk": org.id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_add_form_wrong_login(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    org = OrganizationFactory()
    subclass = DCATResourceSubclassFactory()
    response = app.get(
        reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk}),
        expect_errors=True,
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_add_subclass_form_wrong_login(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    org = OrganizationFactory()
    response = app.get(
        reverse("resource-subclass-add", kwargs={"pk": org.id}), expect_errors=True
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_add_form_correct_login(app: DjangoTestApp):
    FrequencyFactory(is_default=True)
    subclass = DCATResourceSubclassFactory()
    org = OrganizationFactory(
        title="Org_title",
        created=timezone.localize(datetime(2022, 8, 22, 10, 30)),
        jurisdiction=AreaOfManagement.objects.get(id=1),
        slug="test-org-slug",
        kind="test_org_kind",
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(
        reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})
    ).forms["dataset-form"]
    form["title"] = "Added title"
    form["description"] = "Added new dataset description"
    form["tags"] = ["test tag"]
    form["access_rights"] = Dataset.PUBLIC
    resp = form.submit()
    added_dataset = Dataset.objects.filter(translations__title="Added title")
    assert added_dataset.count() == 2
    assert added_dataset[0].tags.all()[0].name == "test tag"
    assert added_dataset[0].access_rights == Dataset.PUBLIC
    assert resp.status_code == 302
    assert str(added_dataset[0].id) in resp.url
    assert Version.objects.get_for_object(added_dataset.first()).count() == 1
    assert (
        Version.objects.get_for_object(added_dataset.first()).first().revision.comment
        == Dataset.CREATED
    )
    assert added_dataset.first().metadata.count() == 1
    assert added_dataset.first().metadata.first().title == "Added title"
    assert (
        added_dataset.first().metadata.first().description
        == "Added new dataset description"
    )


@pytest.mark.haystack
@pytest.mark.django_db
def test_click_add_button(app: DjangoTestApp):
    org = OrganizationFactory(
        title="Org_title",
        created=timezone.localize(datetime(2022, 8, 22, 10, 30)),
        jurisdiction=AreaOfManagement.objects.get(id=1),
        slug="test-org-slug",
        kind="test_org_kind",
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    response = app.get(reverse("organization-datasets", kwargs={"pk": org.id}))
    response.click(linkid="add_dataset")
    assert response.status_code == 200


@pytest.fixture
def dataset():
    organization = OrganizationFactory(slug="org", kind="gov")
    dataset1 = DatasetFactory(slug="ds2", organization=organization)
    dataset1.set_current_language("en")
    dataset1.title = "dataset1"
    dataset1.save()
    dataset1.set_current_language("lt")
    dataset1.title = "dataset1"
    dataset1.save()

    return dataset1


@pytest.mark.django_db
def test_translations_default_language(app: DjangoTestApp, dataset):
    default_language = dataset.get_current_language()
    assert default_language == "lt"


@pytest.mark.django_db
def test_language_change(app: DjangoTestApp, dataset):
    dataset.set_current_language("en")
    current = dataset.get_current_language()
    assert current == "en"


@pytest.mark.django_db
def test_dataset_add_form_initial_values(app: DjangoTestApp):
    default_frequency = FrequencyFactory(is_default=True)
    subclass = DCATResourceSubclassFactory()
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(
        reverse(
            "dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk}
        )
    ).forms["dataset-form"]
    assert form["frequency"].value == str(default_frequency.pk)


@pytest.mark.django_db
def test_dataset_history_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    app.set_user(user)
    resp = app.get(reverse("dataset-history", args=[dataset.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dataset_history_view_with_permission(app: DjangoTestApp):
    user = ManagerFactory(is_staff=True)
    dataset = DatasetFactory(organization=user.organization)
    app.set_user(user)

    form = app.get(reverse("dataset-change", args=[dataset.pk])).forms["dataset-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    resp = form.submit().follow()
    resp = resp.click(linkid="history-tab")
    assert resp.context["detail_url_name"] == "dataset-detail"
    assert resp.context["history_url_name"] == "dataset-history"
    assert len(resp.context["history"]) == 1
    assert resp.context["history"][0]["action"] == "Redaguota"
    assert resp.context["history"][0]["user"] == user


@pytest.mark.django_db
def test_dataset_structure_import_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()

    app.set_user(user)
    url = reverse("dataset-structure-import", args=[dataset.pk])
    resp = app.get(url, expect_errors=True)

    assert resp.status_code == 403


@pytest.mark.django_db
def test_dataset_structure_import_not_standardized(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()

    app.set_user(user)
    resp = app.get(reverse("dataset-structure-import", args=[dataset.pk]))
    form = resp.forms["dataset-structure-form"]
    form["file"] = Upload("manifest.csv", b"Column\nValue")
    form.submit()

    dataset.refresh_from_db()
    structure = DatasetStructure.objects.get(dataset=dataset)
    assert dataset.current_structure == structure
    assert File.objects.count() == 1
    assert structure.file.original_filename == "manifest.csv"


@pytest.mark.django_db
def test_dataset_structure_import_standardized(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()

    app.set_user(user)
    resp = app.get(reverse("dataset-structure-import", args=[dataset.pk]))
    form = resp.forms["dataset-structure-form"]
    form["file"] = Upload("file.csv", MANIFEST.encode())
    form.submit()

    dataset.refresh_from_db()
    structure = DatasetStructure.objects.get(dataset=dataset)
    assert dataset.current_structure == structure
    assert File.objects.count() == 1
    assert structure.file.original_filename == "file.csv"


@pytest.mark.django_db
def test_dataset_members_view_bad_login(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(
        content_type=ct, object_id=dataset.pk, role=Representative.MANAGER
    )
    user = UserFactory()
    app.set_user(user)
    url = reverse(
        "dataset-members",
        kwargs={
            "pk": representative.object_id,
        },
    )
    response = app.get(url, expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_dataset_members_view_no_login(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        content_type=ct, object_id=dataset.pk, role=Representative.MANAGER
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)
    response = app.get(reverse("dataset-members", kwargs={"pk": dataset.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_dataset_members_create_member(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    url = reverse("dataset-members", kwargs={"pk": dataset.pk})

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)

    resp = app.get(url)

    resp = resp.click(linkid="add-member-btn")

    form = resp.forms["representative-form"]
    form["email"] = "test@example.com"
    form["role"] = Representative.MANAGER
    resp = form.submit()

    assert resp.headers["location"] == url

    rep = Representative.objects.get(
        content_type=ct,
        object_id=dataset.id,
        email="test@example.com",
    )
    assert rep.role == Representative.MANAGER
    assert rep.user is None
    assert rep.has_api_access is False
    assert rep.apikey_set.count() == 0

    assert len(mail.outbox) == 1
    assert "/register/" in mail.outbox[0].body


@pytest.mark.django_db
def test_dataset_members_add_member(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    url = reverse("dataset-members", kwargs={"pk": dataset.pk})
    user = UserFactory(email="test@example.com")
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)

    resp = app.get(url)

    resp = resp.click(linkid="add-member-btn")

    form = resp.forms["representative-form"]
    form["email"] = "test@example.com"
    form["role"] = Representative.MANAGER
    resp = form.submit()

    assert resp.headers["location"] == url

    rep = Representative.objects.get(
        content_type=ct,
        object_id=dataset.id,
        email="test@example.com",
    )
    assert rep.user == user
    assert rep.user.organization == dataset.organization
    assert rep.role == Representative.MANAGER
    assert rep.has_api_access is False
    assert rep.apikey_set.count() == 0

    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_member_subscription(app: DjangoTestApp):
    subscriptions_before = Subscription.objects.all()
    assert len(subscriptions_before) == 0

    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    url = reverse("dataset-members", kwargs={"pk": dataset.pk})
    user = UserFactory(email="test@example.com")
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)

    resp = app.get(url)

    resp = resp.click(linkid="add-member-btn")

    form = resp.forms["representative-form"]
    form["email"] = "test@example.com"
    form["role"] = Representative.MANAGER
    form["subscribe"] = True
    resp = form.submit()

    assert resp.headers["location"] == url

    rep = Representative.objects.get(
        content_type=ct,
        object_id=dataset.id,
        email="test@example.com",
    )
    assert rep.user == user
    assert rep.user.organization == dataset.organization
    assert rep.role == Representative.MANAGER
    assert rep.has_api_access is False
    assert rep.apikey_set.count() == 0

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["test@example.com"]

    subscriptions = Subscription.objects.all()
    assert len(subscriptions) == 1
    assert subscriptions[0].sub_type == Subscription.DATASET


@pytest.mark.django_db
def test_dataset_members_create_member_with_api_access(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    user = UserFactory(email="test@example.com")
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)
    resp = app.get(reverse("dataset-members", kwargs={"pk": dataset.pk}))
    resp = resp.click(linkid="add-member-btn")

    form = resp.forms["representative-form"]
    form["email"] = "test@example.com"
    form["role"] = Representative.MANAGER
    form["has_api_access"] = True
    form.submit()

    rep = Representative.objects.get(
        content_type=ct,
        object_id=dataset.id,
        email="test@example.com",
    )
    assert rep.user == user
    assert rep.has_api_access is True
    assert rep.apikey_set.count() == 1


@pytest.mark.django_db
def test_dataset_members_update_member(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    url = reverse("dataset-members", kwargs={"pk": dataset.pk})

    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)

    resp = app.get(url)

    resp = resp.click(linkid=f"update-member-{manager.pk}-btn")

    form = resp.forms["representative-form"]
    form["role"] = Representative.MANAGER
    resp = form.submit()

    assert resp.headers["location"] == url

    manager.refresh_from_db()
    assert manager.role == Representative.MANAGER
    assert manager.user.organization == dataset.organization

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_dataset_members_update_with_api_access(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)
    resp = app.get(reverse("dataset-members", kwargs={"pk": dataset.pk}))
    resp = resp.click(linkid=f"update-member-{coordinator.pk}-btn")

    form = resp.forms["representative-form"]
    form["has_api_access"] = True
    form.submit()

    coordinator.refresh_from_db()
    assert coordinator.has_api_access is True
    assert coordinator.apikey_set.count() == 1


@pytest.mark.django_db
def test_dataset_members_delete_member(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)
    url = reverse("dataset-members", kwargs={"pk": dataset.pk})

    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR,
    )

    app.set_user(coordinator.user)

    resp = app.get(url)

    resp = resp.click(linkid=f"delete-member-{manager.pk}-btn")

    form = resp.forms["delete-form"]
    resp = form.submit()

    assert resp.headers["location"] == url

    qs = Representative.objects.filter(
        content_type=ct,
        object_id=dataset.id,
        user=manager.user,
    )
    assert not qs.exists()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_add_project_with_permission(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory()
    dataset = DatasetFactory()
    app.set_user(user)
    resp = app.get(reverse("dataset-project-add", kwargs={"pk": dataset.pk}))
    form = resp.forms["dataset-add-project-form"]
    form["projects"] = (project.pk,)
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse("dataset-projects", kwargs={"pk": dataset.pk})
    assert project.datasets.all().first() == dataset


@pytest.mark.django_db
def test_add_project_with_no_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    app.set_user(user)
    resp = app.get(
        reverse("dataset-project-add", kwargs={"pk": dataset.pk}), expect_errors=True
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_remove_project_no_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory()
    dataset = DatasetFactory()
    project.datasets.add(dataset)
    assert project.datasets.all().count() == 1

    app.set_user(user)

    resp = app.get(
        reverse(
            "dataset-project-remove",
            kwargs={"pk": dataset.pk, "project_id": project.pk},
        ),
        expect_errors=True,
    )

    assert resp.status_code == 302


@pytest.mark.django_db
def test_remove_project_with_permission(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory()
    dataset = DatasetFactory()
    url = reverse("dataset-projects", kwargs={"pk": dataset.pk})

    project.datasets.add(dataset)
    assert project.datasets.all().count() == 1

    app.set_user(user)

    resp = app.get(url)
    resp = resp.click(linkid=f"remove-project-{project.pk}-btn")

    form = resp.forms["delete-form"]
    resp = form.submit()

    assert resp.headers["location"] == url
    assert project.datasets.all().count() == 0


@pytest.mark.haystack
def test_dataset_stats_view_no_login_with_query(
    app: DjangoTestApp, category_filter_data: dict[str, list[Category]]
):
    resp = app.get(
        "%s?selected_facets=category_exact:%s"
        % (reverse("dataset-list"), category_filter_data["categories"][1].pk)
    )
    # old_object_list = resp.context['object_list']
    # resp = resp.click(linkid="Dataset-stats-status")

    assert resp.status_code == 200
    # assert resp.context['dataset_count'] == len(old_object_list)


@pytest.mark.haystack
def test_dataset_jurisdictions(app: DjangoTestApp):
    parent_org = OrganizationFactory()
    child_org1 = parent_org.add_child(
        instance=OrganizationFactory.build(title="org-test-1")
    )
    child_org2 = parent_org.add_child(
        instance=OrganizationFactory.build(title="org-test-2")
    )
    DatasetFactory(organization=parent_org)
    DatasetFactory(organization=child_org1)
    DatasetFactory(organization=child_org1)
    DatasetFactory(organization=child_org2)
    DatasetFactory(organization=child_org2)

    resp = app.get(reverse("dataset-list"))
    filters = {f.name: f for f in resp.context["filters"]}
    jurisdictions = list(filters["jurisdiction"].items())
    # resp = resp.click(linkid="dataset-stats-supervisor")

    dataset_count = 0
    for org in jurisdictions:
        if dataset_count < org.count:
            dataset_count = org.count

    # assert resp.context['jurisdictions'] == jurisdictions
    # assert resp.context['max_count'] == dataset_count
    # assert len(resp.context['jurisdictions']) == 1
    # assert dataset_count == 5
    assert resp.status_code == 200


@pytest.mark.django_db
def test_dataset_resource_create_button(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    resp = app.get(dataset.get_absolute_url())
    resp = resp.click(linkid="add_resource")
    assert resp.request.path == reverse("resource-add", args=[dataset.pk])


@pytest.mark.django_db
def test_dataset_assign_new_category_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)

    group = DatasetGroupFactory()
    category = CategoryFactory()
    category.groups.add(group)

    dataset = DatasetFactory()
    resp = app.get(reverse("assign-category", args=[dataset.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dataset_assign_new_category(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    group = DatasetGroupFactory()
    category1 = CategoryFactory()
    category1.groups.add(group)
    category2 = CategoryFactory()
    category2.groups.add(group)
    category3 = CategoryFactory()
    category3.groups.add(group)

    dataset = DatasetFactory()
    resp = app.post(
        reverse("assign-category", args=[dataset.pk]),
        {"category": [category1.pk, category2.pk]},
    )
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert list(dataset.category.order_by("pk")) == [category1, category2]


@pytest.mark.django_db
def test_dataset_change_category(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    group = DatasetGroupFactory()
    category1 = CategoryFactory()
    category1.groups.add(group)
    category2 = CategoryFactory()
    category2.groups.add(group)
    category3 = CategoryFactory()
    category3.groups.add(group)

    dataset = DatasetFactory()
    dataset.category.add(category1)
    dataset.category.add(category2)

    resp = app.post(
        reverse("assign-category", args=[dataset.pk]), {"category": [category3.pk]}
    )
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert list(dataset.category.all()) == [category3]


@pytest.mark.django_db
def test_dataset_create_attribution_with_organization_and_agent(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    organization = OrganizationFactory()
    attribution = AttributionFactory()

    form = app.get(reverse("attribution-add", args=[dataset.pk])).forms[
        "attribution-form"
    ]
    form["attribution"] = attribution.pk
    form["organization"].force_value(organization.pk)
    form["agent"] = "Test organization"
    resp = form.submit()

    assert list(resp.context["form"].errors.values()) == [
        ['Negalima užpildyti abiejų "Organizacija" ir "Agentas" laukų.']
    ]


@pytest.mark.django_db
def test_dataset_create_attribution_without_organization_and_agent(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    attribution = AttributionFactory()

    form = app.get(reverse("attribution-add", args=[dataset.pk])).forms[
        "attribution-form"
    ]
    form["attribution"] = attribution.pk
    resp = form.submit()

    assert list(resp.context["form"].errors.values()) == [
        ['Privaloma užpildyti "Organizacija" arba "Agentas" lauką.']
    ]


@pytest.mark.django_db
def test_dataset_create_attribution_with_existing_organization(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    attribution = AttributionFactory()
    organization = OrganizationFactory()
    DatasetAttributionFactory(
        dataset=dataset, attribution=attribution, organization=organization
    )

    form = app.get(reverse("attribution-add", args=[dataset.pk])).forms[
        "attribution-form"
    ]
    form["attribution"] = attribution.pk
    form["organization"].force_value(organization.pk)
    resp = form.submit()

    assert list(resp.context["form"].errors.values()) == [
        [f'Ryšys "{attribution.title}" su šia organizacija jau egzistuoja.']
    ]


@pytest.mark.django_db
def test_dataset_create_attribution_with_existing_agent(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    attribution = AttributionFactory()
    DatasetAttributionFactory(
        dataset=dataset, attribution=attribution, agent="Test organization"
    )

    form = app.get(reverse("attribution-add", args=[dataset.pk])).forms[
        "attribution-form"
    ]
    form["attribution"] = attribution.pk
    form["agent"] = "Test organization"
    resp = form.submit()

    assert list(resp.context["form"].errors.values()) == [
        [f'Ryšys "{attribution.title}" su šiuo agentu jau egzistuoja.']
    ]


@pytest.mark.django_db
def test_dataset_create_attribution_with_organization(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    organization = OrganizationFactory()
    attribution = AttributionFactory()

    form = app.get(reverse("attribution-add", args=[dataset.pk])).forms[
        "attribution-form"
    ]
    form["attribution"] = attribution.pk
    form["organization"].force_value(organization.pk)
    resp = form.submit()

    assert resp.url == dataset.get_absolute_url()
    assert dataset.datasetattribution_set.count() == 1
    assert dataset.datasetattribution_set.first().organization == organization
    assert dataset.datasetattribution_set.first().attribution == attribution
    assert dataset.datasetattribution_set.first().agent is None


@pytest.mark.django_db
def test_dataset_create_attribution_with_agent(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    attribution = AttributionFactory()

    form = app.get(reverse("attribution-add", args=[dataset.pk])).forms[
        "attribution-form"
    ]
    form["attribution"] = attribution.pk
    form["agent"] = "Test organization"
    resp = form.submit()

    assert resp.url == dataset.get_absolute_url()
    assert dataset.datasetattribution_set.count() == 1
    assert dataset.datasetattribution_set.first().agent == "Test organization"
    assert dataset.datasetattribution_set.first().attribution == attribution
    assert dataset.datasetattribution_set.first().organization is None


@pytest.mark.django_db
def test_dataset_delete_attribution(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset_attribution = DatasetAttributionFactory()
    dataset = dataset_attribution.dataset

    resp = app.get(
        reverse("attribution-delete", args=[dataset.pk, dataset_attribution.pk])
    )

    assert resp.url == dataset.get_absolute_url()
    assert dataset.datasetattribution_set.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "subclass_name, form_class",
    [
        ("dataset", ResourceForm),
        ("catalog", ResourceForm),
        ("information_system", InformationSystemResourceForm),
        ("service", ServiceResourceForm),
        ("series", ResourceForm),
        ("foo", ResourceForm),
    ],
)
def test_dataset_create_uses_different_forms_based_on_dcat_subclass(
    app: DjangoTestApp, subclass_name: str, form_class: BaseResourceForm
) -> None:
    organization = OrganizationFactory()
    subclass = DCATResourceSubclassFactory(name=subclass_name)
    user = UserFactory(is_staff=True)
    app.set_user(user)
    response = app.get(
        reverse(
            "dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk}
        )
    )

    assert type(response.context.get("form")) == form_class


@pytest.mark.django_db
def test_dataset_create_information_system(app: DjangoTestApp):
    organization = OrganizationFactory()
    subclass = DCATResourceSubclassFactory(name="information_system")
    catalog = CatalogFactory()
    frequency = FrequencyFactory(is_default=True)
    concept_schema = ConceptSchemaFactory(
        uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
    )
    concept = ConceptFactory(concept_schemas=[concept_schema])
    user = UserFactory(is_staff=True)
    app.set_user(user)

    url = reverse(
        "dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk}
    )

    data = {
        "title": "test_information_system",
        "description": "test_information_system_description",
        "is_public": False,
        "tags": "tag1, tag2",
        "catalog": catalog.pk,
        "frequency": frequency.pk,
        "access_rights": Dataset.PUBLIC,
        "name": "test/information/system",
        "landing_page": "https://www.test.test",
        "information_system_type": concept.pk,
    }
    response = app.post(url, data)

    dataset = Dataset.objects.first()
    assert dataset
    assert response.url == dataset.get_absolute_url()
    assert dataset.title == "test_information_system"
    assert dataset.description == "test_information_system_description"
    assert dataset.is_public is False
    assert set(dataset.tags.all().values_list("name", flat=True)) == {"tag1", "tag2"}
    assert dataset.catalog == catalog
    assert dataset.frequency == frequency
    assert dataset.access_rights == Dataset.PUBLIC
    assert dataset.name == "test/information/system"
    assert dataset.landing_page == "https://www.test.test"
    assert dataset.information_system_type == concept


@pytest.mark.django_db
def test_dataset_with_subclass(app: DjangoTestApp):
    FrequencyFactory(is_default=True)
    organization = OrganizationFactory()
    subclass = DCATResourceSubclassFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(
        reverse(
            "dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk}
        )
    ).forms["dataset-form"]
    form["title"] = "Test dataset"
    form["description"] = "Test dataset description"
    form["is_public"] = True
    form["access_rights"] = Dataset.PUBLIC
    form.submit()
    added_dataset = Dataset.objects.filter(translations__title="Test dataset")
    assert added_dataset.count() == 2
    assert added_dataset.first().is_public is True
    assert added_dataset.first().subclass == subclass


@pytest.mark.django_db
def test_dataset_add_relation_with_existing_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset_relation = DatasetRelationFactory()

    form = app.get(
        reverse("dataset-relation-add", args=[dataset_relation.dataset.pk])
    ).forms["dataset-relation-form"]
    form["relation_type"] = f"{dataset_relation.relation.pk}"
    form["part_of"].force_value(dataset_relation.part_of.pk)
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        [
            f'"{dataset_relation.relation.title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.'
        ]
    ]


@pytest.mark.django_db
def test_dataset_add_relation_with_existing_inverse_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset_relation = DatasetRelationFactory()

    form = app.get(
        reverse("dataset-relation-add", args=[dataset_relation.part_of.pk])
    ).forms["dataset-relation-form"]
    form["relation_type"] = f"{dataset_relation.relation.pk}_inv"
    form["part_of"].force_value(dataset_relation.dataset.pk)
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        [
            f'"{dataset_relation.relation.inversive_title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.'
        ]
    ]


@pytest.mark.django_db
def test_dataset_add_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    dataset_part_of = DatasetFactory()
    relation = RelationFactory()

    form = app.get(reverse("dataset-relation-add", args=[dataset.pk])).forms[
        "dataset-relation-form"
    ]
    form["relation_type"] = f"{relation.pk}"
    form["part_of"].force_value(dataset_part_of.pk)
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.url == dataset.get_absolute_url()
    assert dataset.part_of.count() == 1
    assert dataset.part_of.first().part_of == dataset_part_of
    assert dataset.part_of.first().relation == relation


@pytest.mark.django_db
def test_dataset_add_inverse_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    dataset_part_of = DatasetFactory()
    relation = RelationFactory()

    form = app.get(reverse("dataset-relation-add", args=[dataset.pk])).forms[
        "dataset-relation-form"
    ]
    form["relation_type"] = f"{relation.pk}_inv"
    form["part_of"].force_value(dataset_part_of.pk)
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.url == dataset.get_absolute_url()
    assert dataset_part_of.part_of.count() == 1
    assert dataset_part_of.part_of.first().part_of == dataset
    assert dataset_part_of.part_of.first().relation == relation


def _get_selected(context):
    selected = {
        f.name: [i.value for i in f.items() if i.selected] for f in context["filters"]
    }
    selected = {k: (v[0] if len(v) == 1 else v) for k, v in selected.items() if v}
    return selected


@pytest.mark.django_db
def test_add_dataset_to_plan(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    plan = PlanFactory(deadline=(date.today() + timedelta(days=1)))

    form = app.get(reverse("dataset-plans-create", args=[dataset.pk])).forms[
        "dataset-plan-form"
    ]
    form["plan"] = plan.pk
    resp = form.submit()

    assert resp.url == reverse("dataset-plans", args=[dataset.pk])
    assert dataset.plandataset_set.count() == 1
    assert dataset.plandataset_set.first().plan == plan


@pytest.mark.django_db
def test_dataset_create_non_public(app: DjangoTestApp):
    FrequencyFactory(is_default=True)
    organization = OrganizationFactory()
    subclass = DCATResourceSubclassFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(
        reverse(
            "dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk}
        )
    ).forms["dataset-form"]
    form["title"] = "Test dataset"
    form["description"] = "Test dataset description"
    form["is_public"] = False
    form["access_rights"] = Dataset.PUBLIC
    form.submit()
    added_dataset = Dataset.objects.filter(translations__title="Test dataset")
    assert added_dataset.count() == 2
    assert added_dataset.first().is_public is False
    assert added_dataset.first().published is None
    assert added_dataset.first().access_rights == Dataset.PUBLIC


@pytest.mark.django_db
def test_dataset_create_public(app: DjangoTestApp):
    FrequencyFactory(is_default=True)
    organization = OrganizationFactory()
    subclass = DCATResourceSubclassFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(
        reverse(
            "dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk}
        )
    ).forms["dataset-form"]
    form["title"] = "Test dataset"
    form["description"] = "Test dataset description"
    form["is_public"] = True
    form["access_rights"] = Dataset.PUBLIC
    form.submit()
    added_dataset = Dataset.objects.filter(translations__title="Test dataset")
    assert added_dataset.count() == 2
    assert added_dataset.first().is_public is True
    assert added_dataset.first().published is not None
    assert added_dataset.first().access_rights == Dataset.PUBLIC

@pytest.mark.django_db
def test_child_dataset_create_public(app: DjangoTestApp):
    FrequencyFactory(is_default=True)
    organization = OrganizationFactory()
    subclass = DCATResourceSubclassFactory()
    parent_dataset = DatasetFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(
        reverse(
            "child-dataset-add",
            kwargs={"pk": organization.id, "parent_id":parent_dataset.pk, "subclass_uuid": subclass.pk}
        )
    ).forms["dataset-form"]
    form["title"] = "Test dataset"
    form["description"] = "Test dataset description"
    form["is_public"] = True
    form["access_rights"] = Dataset.PUBLIC
    form.submit()
    added_dataset :Dataset = Dataset.objects.filter(translations__title="Test dataset").first()
    assert added_dataset.is_public is True
    assert added_dataset.published is not None
    assert added_dataset.access_rights == Dataset.PUBLIC
    assert added_dataset.get_parent() == parent_dataset


@pytest.mark.django_db
def test_information_system_create_with_identifier(app: DjangoTestApp):
    FrequencyFactory(is_default=True)
    AgencyFactory()
    organization = OrganizationFactory()
    subclass = DCATResourceSubclassFactory(name="information_system")
    concept_schema = ConceptSchemaFactory(
        uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
    )
    concept = ConceptFactory(concept_schemas=[concept_schema])
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(
        reverse(
            "dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk}
        )
    ).forms["dataset-form"]
    form["title"] = "Test dataset"
    form["description"] = "Test dataset description"
    form["is_public"] = True
    form["access_rights"] = Dataset.PUBLIC
    form["identifier"] = "test-identifier"
    form["information_system_type"] = concept.pk
    form.submit()
    added_dataset = Dataset.objects.filter(translations__title="Test dataset")
    assert added_dataset.first().is_public is True
    assert added_dataset.first().published is not None
    assert added_dataset.first().access_rights == Dataset.PUBLIC
    assert added_dataset.first().identifier == "test-identifier"

    assert Identifier.objects.filter(notation="test-identifier", resource=added_dataset.first()).exists()


@pytest.mark.django_db
def test_dataset_update_existing_identifier(app: DjangoTestApp):
    subclass = DCATResourceSubclassFactory(name="information_system")
    concept_schema = ConceptSchemaFactory(
        uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
    )
    concept = ConceptFactory(concept_schemas=[concept_schema])
    dataset = DatasetFactory(subclass=subclass, information_system_type=concept)
    agency = AgencyFactory()
    IdentifierFactory(resource=dataset, notation="test-identifier", scheme_agency=agency)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms[
        "dataset-form"
    ]
    assert form["identifier"].value == "test-identifier"
    form["identifier"] = "new-identifier"
    form.submit()
    dataset.refresh_from_db()
    assert dataset.identifier == "new-identifier"
    
    identifiers = Identifier.objects.filter(resource=dataset)
    assert identifiers.count() == 1
    assert identifiers.first().notation == "new-identifier"
    

@pytest.mark.django_db
def test_dataset_update_non_existing_identifier(app: DjangoTestApp):
    AgencyFactory()
    subclass = DCATResourceSubclassFactory(name="information_system")
    concept_schema = ConceptSchemaFactory(
        uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
    )
    concept = ConceptFactory(concept_schemas=[concept_schema])
    dataset = DatasetFactory(subclass=subclass, information_system_type=concept)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms[
        "dataset-form"
    ]
    form["identifier"] = "new-identifier"
    form.submit()
    dataset.refresh_from_db()
    assert dataset.identifier == "new-identifier"

    identifiers = Identifier.objects.filter(resource=dataset)
    assert identifiers.count() == 1
    assert identifiers.first().notation == "new-identifier"


@pytest.mark.django_db
def test_dataset_update_from_public_to_non_public(app: DjangoTestApp):
    LicenceFactory(is_default=True)
    FrequencyFactory(is_default=True)
    dataset = DatasetFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)

    assert dataset.is_public is True
    assert dataset.published is not None

    form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms[
        "dataset-form"
    ]
    form["is_public"] = False
    form.submit()
    dataset.refresh_from_db()

    assert dataset.is_public is False
    assert dataset.published is None


@pytest.mark.django_db
def test_dataset_update_from_non_public_to_public(app: DjangoTestApp):
    LicenceFactory(is_default=True)
    FrequencyFactory(is_default=True)
    dataset = DatasetFactory(
        is_public=False,
        published=None,
    )
    user = UserFactory(is_staff=True)
    app.set_user(user)

    assert dataset.is_public is False
    assert dataset.published is None

    form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms[
        "dataset-form"
    ]
    form["is_public"] = True
    form.submit()
    dataset.refresh_from_db()

    assert dataset.is_public is True
    assert dataset.published is not None


@pytest.mark.django_db
def test_dataset_update_without_permission(app: DjangoTestApp):
    dataset1 = DatasetFactory()
    dataset2 = DatasetFactory()
    user = UserFactory()
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(dataset1),
        object_id=dataset1.pk,
    )
    app.set_user(user)

    resp = app.get(
        reverse("dataset-change", kwargs={"pk": dataset2.id}), expect_errors=True
    )
    assert resp.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "subclass_name, form_class",
    [
        ("dataset", ResourceForm),
        ("catalog", ResourceForm),
        ("information_system", InformationSystemResourceForm),
        ("service", ServiceResourceForm),
        ("series", ResourceForm),
        ("foo", ResourceForm),
    ],
)
def test_dataset_update_uses_different_forms_based_on_dcat_subclass(
    app: DjangoTestApp, subclass_name: str, form_class: BaseResourceForm
) -> None:
    subclass = DCATResourceSubclassFactory(name=subclass_name)
    dataset = DatasetFactory(subclass=subclass)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    response = app.get(reverse("dataset-change", kwargs={"pk": dataset.id}))

    assert type(response.context.get("form")) == form_class


@pytest.mark.django_db
def test_dataset_update_information_system(app: DjangoTestApp):
    subclass = DCATResourceSubclassFactory(name="information_system")
    dataset = DatasetFactory(subclass=subclass)
    catalog = CatalogFactory()
    frequency = FrequencyFactory(is_default=True)
    concept_schema = ConceptSchemaFactory(
        uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
    )
    concept = ConceptFactory(concept_schemas=[concept_schema])
    user = UserFactory(is_staff=True)
    app.set_user(user)

    url = reverse("dataset-change", kwargs={"pk": dataset.id})

    data = {
        "title": "test_information_system",
        "description": "test_information_system_description",
        "is_public": False,
        "tags": "tag1, tag2",
        "catalog": catalog.pk,
        "frequency": frequency.pk,
        "access_rights": Dataset.PUBLIC,
        "name": "test/information/system",
        "landing_page": "https://www.test.test",
        "information_system_type": concept.pk,
    }
    response = app.post(url, data)

    dataset = Dataset.objects.first()
    assert dataset
    assert response.url == dataset.get_absolute_url()
    assert dataset.title == "test_information_system"
    assert dataset.description == "test_information_system_description"
    assert dataset.is_public is False
    assert set(dataset.tags.all().values_list("name", flat=True)) == {"tag1", "tag2"}
    assert dataset.catalog == catalog
    assert dataset.frequency == frequency
    assert dataset.access_rights == Dataset.PUBLIC
    assert dataset.name == "test/information/system"
    assert dataset.landing_page == "https://www.test.test"
    assert dataset.information_system_type == concept


@pytest.mark.django_db
def test_add_dataset_to_plan_title(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization)

    form = app.get(reverse("dataset-plans-create", args=[dataset.pk])).forms[
        "plan-form"
    ]
    form.submit()

    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 1
    assert plan.first().title == "Duomenų atvėrimas"


@pytest.mark.django_db
def test_add_dataset_to_plan_title_with_distribution(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization)
    DatasetDistributionFactory(dataset=dataset)

    form = app.get(reverse("dataset-plans-create", args=[dataset.pk])).forms[
        "plan-form"
    ]
    form.submit()

    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 1
    assert plan.first().title == "Duomenų rinkinio papildymas"


@pytest.mark.django_db
def test_delete_dataset_from_last_plan(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.PLANNED)
    plan = PlanFactory()
    PlanDataset.objects.create(dataset=dataset, plan=plan)

    form = app.get(reverse("dataset-plans-delete", args=[plan.pk])).forms["delete-form"]
    form.submit()

    dataset.refresh_from_db()
    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 0
    assert dataset.status == Dataset.INVENTORED
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.INVENTORED


@pytest.mark.django_db
def test_delete_dataset_from_non_last_plan(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.PLANNED)
    plan1 = PlanFactory()
    PlanDataset.objects.create(dataset=dataset, plan=plan1)
    plan2 = PlanFactory()
    PlanDataset.objects.create(dataset=dataset, plan=plan2)

    form = app.get(reverse("dataset-plans-delete", args=[plan2.pk])).forms[
        "delete-form"
    ]
    form.submit()

    dataset.refresh_from_db()
    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 1
    assert dataset.status == Dataset.PLANNED
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_not_public_dataset_from_last_plan(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(
        organization=organization, is_public=False, status=Dataset.UNASSIGNED
    )
    plan = PlanFactory()
    PlanDataset.objects.create(dataset=dataset, plan=plan)

    form = app.get(reverse("dataset-plans-delete", args=[plan.pk])).forms["delete-form"]
    form.submit()

    dataset.refresh_from_db()
    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 0
    assert dataset.status == Dataset.UNASSIGNED
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_opened_dataset_from_last_plan(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    DatasetDistributionFactory(dataset=dataset)
    plan = PlanFactory()
    PlanDataset.objects.create(dataset=dataset, plan=plan)

    form = app.get(reverse("dataset-plans-delete", args=[plan.pk])).forms["delete-form"]
    form.submit()

    dataset.refresh_from_db()
    plan = Plan.objects.filter(plandataset__dataset=dataset)
    assert plan.count() == 0
    assert dataset.status == Dataset.HAS_DATA
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_last_distribution_from_dataset(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    resource = DatasetDistributionFactory(dataset=dataset)

    app.get(reverse("resource-delete", args=[resource.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.INVENTORED
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.INVENTORED


@pytest.mark.django_db
def test_delete_non_last_distribution_from_dataset(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    resource1 = DatasetDistributionFactory(dataset=dataset)
    resource2 = DatasetDistributionFactory(dataset=dataset)

    app.get(reverse("resource-delete", args=[resource2.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 1
    assert dataset.status == Dataset.HAS_DATA
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_last_distribution_from_non_public_dataset(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(
        organization=organization, status=Dataset.UNASSIGNED, is_public=False
    )
    resource = DatasetDistributionFactory(dataset=dataset)

    app.get(reverse("resource-delete", args=[resource.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.UNASSIGNED
    assert dataset.comments.count() == 0


@pytest.mark.django_db
def test_delete_last_distribution_from_dataset_with_plans(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    resource = DatasetDistributionFactory(dataset=dataset)
    plan = PlanFactory()
    PlanDataset.objects.create(dataset=dataset, plan=plan)

    app.get(reverse("resource-delete", args=[resource.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.PLANNED
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.PLANNED


@pytest.mark.django_db
def test_dataset_with_name_error(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()

    form = app.get(reverse("dataset-change", args=[dataset.pk])).forms["dataset-form"]
    form["name"] = "test/ąčę"
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        ["Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."]
    ]


@pytest.mark.haystack
def test_search_with_partial_word_query(app: DjangoTestApp, search_datasets):
    resp = app.get("%s?q=%s" % (reverse("dataset-list"), "vien"))
    assert [int(obj.pk) for obj in resp.context["object_list"]] == [
        search_datasets[0].pk
    ]


@pytest.mark.django_db
def test_project_tab_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    app.set_user(user)
    response = app.get(
        reverse("dataset-projects", args=[dataset.pk]), expect_errors=True
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_project_tab_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
    )
    app.set_user(user)
    response = app.get(reverse("dataset-projects", args=[dataset.pk]))
    assert response.context["dataset"] == dataset


@pytest.mark.django_db
def test_plan_tab_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse("dataset-plans", args=[dataset.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_plan_tab_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
    )
    app.set_user(user)
    response = app.get(reverse("dataset-plans", args=[dataset.pk]))
    assert response.context["dataset"] == dataset


@pytest.mark.django_db
def test_request_tab_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    app.set_user(user)
    response = app.get(
        reverse("dataset-requests", args=[dataset.pk]), expect_errors=True
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_request_tab_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
    )
    app.set_user(user)
    response = app.get(reverse("dataset-requests", args=[dataset.pk]))
    assert response.context["dataset"] == dataset


@pytest.mark.haystack
def test_access_rights_filter(app: DjangoTestApp):
    dataset1 = DatasetFactory(access_rights=Dataset.RESTRICTED)
    dataset2 = DatasetFactory(access_rights=Dataset.RESTRICTED)
    DatasetFactory(access_rights=Dataset.PUBLIC)
    resp = app.get(
        "%s?selected_facets=access_rights_exact:%s"
        % (reverse("dataset-list"), Dataset.RESTRICTED)
    )

    objects = sorted([int(obj.pk) for obj in resp.context["object_list"]])
    assert objects == sorted([dataset1.pk, dataset2.pk])

    filters = {f.name: f for f in resp.context["filters"]}
    selected = [i.value for i in filters["access_rights"].items() if i.selected]
    assert selected == [Dataset.RESTRICTED]


def parse_table(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "resource-table"})
    rows = table.find("tbody").find_all("tr")

    data = []
    for row in rows:
        cols = row.find_all("td")
        cols = [col.get_text(strip=True) for col in cols]
        data.append(cols)

    return data


@pytest.mark.django_db
def test_dataset_dynamic_resources(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    resource = DatasetDistributionFactory(uapi_format=True)
    form = app.get(
        reverse("resource-model-create", args=[resource.dataset.pk, resource.pk])
    ).forms["model-form"]
    form["name"] = "TestModel"
    form.submit()
    assert resource.model_set.first().name == "TestModel"

    response = app.get(reverse("dataset-detail", args=[resource.dataset.pk]))
    html = response.text
    table_data = parse_table(html)
    expected_data = [
        [
            "",
            "-",
            resource.title,
            "2022-01-01",
            "2022-12-31",
            "-",
            "Saugykla API",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "PeržiūrėtiAtsisiųsti",
            "Redaguoti",
            "Trinti",
        ],
        [
            "",
            "-",
            "TestModel",
            "2022-01-01",
            "2022-12-31",
            "-",
            "JSON",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
        [
            "",
            "-",
            "TestModel",
            "2022-01-01",
            "2022-12-31",
            "-",
            "JSONL",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
        [
            "",
            "-",
            "TestModel",
            "2022-01-01",
            "2022-12-31",
            "-",
            "RDF",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
        [
            "",
            "-",
            "TestModel",
            "2022-01-01",
            "2022-12-31",
            "-",
            "CSV",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
    ]
    assert table_data == expected_data


@pytest.mark.django_db
def test_dataset_dynamic_resources_multiple_models(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    resource = DatasetDistributionFactory(uapi_format=True)
    for model_name in ["TestModel", "TestModel2", "TestModel3"]:
        form = app.get(
            reverse("resource-model-create", args=[resource.dataset.pk, resource.pk])
        ).forms["model-form"]
        form["name"] = model_name
        form.submit()
    assert resource.model_set.count() == 3

    response = app.get(reverse("dataset-detail", args=[resource.dataset.pk]))
    html = response.text
    table_data = parse_table(html)
    expected_data = [
        [
            "",
            "-",
            resource.title,
            "2022-01-01",
            "2022-12-31",
            "-",
            "Saugykla API",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "PeržiūrėtiAtsisiųsti",
            "Redaguoti",
            "Trinti",
        ],
        [
            "",
            "-",
            "TestModel",
            "2022-01-01",
            "2022-12-31",
            "-",
            "JSON",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
        [
            "",
            "-",
            "TestModel",
            "2022-01-01",
            "2022-12-31",
            "-",
            "JSONL",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
        [
            "",
            "-",
            "TestModel",
            "2022-01-01",
            "2022-12-31",
            "-",
            "RDF",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
        [
            "",
            "-",
            "TestModel",
            "2022-01-01",
            "2022-12-31",
            "-",
            "CSV",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
        [
            "",
            "-",
            "TestModel2",
            "2022-01-01",
            "2022-12-31",
            "-",
            "CSV",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
        [
            "",
            "-",
            "TestModel3",
            "2022-01-01",
            "2022-12-31",
            "-",
            "CSV",
            resource.created.strftime("%Y-%m-%d"),
            resource.modified.strftime("%Y-%m-%d"),
            "",
            "",
            "Atidaryti",
        ],
    ]
    assert table_data == expected_data


@pytest.mark.django_db
def test_view_non_public_dataset_with_org_representative(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=None,
        role=Representative.MANAGER,
    )

    app.set_user(user)
    response = app.get(reverse("dataset-detail", args=[dataset.pk]))
    assert response.status_code == 200
    assert response.context["dataset"] == dataset


@pytest.mark.django_db
def test_edit_non_public_dataset_with_org_representative(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=None,
        role=Representative.MANAGER,
    )

    app.set_user(user)
    form = app.get(reverse("dataset-change", args=[dataset.pk])).forms["dataset-form"]
    form["title"] = "Edited title"
    form["description"] = "Edited description"
    response = form.submit()
    dataset.refresh_from_db()

    assert response.status_code == 302
    assert response.url == reverse("dataset-detail", args=[dataset.pk])
    assert dataset.title == "Edited title"
    assert dataset.description == "Edited description"


@pytest.mark.django_db
def test_add_member_to_dataset_with_org_representative(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=None,
        role=Representative.MANAGER,
    )

    app.set_user(user)
    response = app.get(
        reverse("dataset-members", args=[dataset.pk]), expect_errors=True
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_dataset_member_create_invalid_phone(app: DjangoTestApp):
    ds = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=ds.pk,
        role=Representative.COORDINATOR,
    )
    app.set_user(coordinator.user)
    resp = app.get(reverse("dataset-members", kwargs={"pk": ds.pk}))
    resp = resp.click(linkid="add-member-btn")
    form = resp.forms["representative-form"]
    form["email"] = "new@gmail.com"
    form["role"] = "manager"
    form["phone"] = "123456"
    form.submit()

    assert resp.status_code == 200
    assert Representative.objects.filter(email="new@gmail.com").count() == 0


@pytest.mark.django_db
def test_dataset_member_create_valid_phone(app: DjangoTestApp):
    ds = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=ds.pk,
        role=Representative.COORDINATOR,
    )
    app.set_user(coordinator.user)
    resp = app.get(reverse("dataset-members", kwargs={"pk": ds.pk}))
    resp = resp.click(linkid="add-member-btn")
    form = resp.forms["representative-form"]

    form["email"] = "new1@gmail.com"
    form["role"] = "manager"
    form["phone"] = "+37061234567"
    resp = form.submit()
    assert resp.status_code == 302
    rep_queryset = Representative.objects.filter(email="new1@gmail.com")
    assert rep_queryset.count() == 1
    assert rep_queryset.first().phone == "+37061234567"

    resp = app.get(reverse("dataset-members", kwargs={"pk": ds.pk}))
    resp = resp.click(linkid="add-member-btn")
    form = resp.forms["representative-form"]

    form["email"] = "new2@gmail.com"
    form["role"] = "manager"
    form["phone"] = "061234567"
    resp = form.submit()
    assert resp.status_code == 302
    rep_queryset = Representative.objects.filter(email="new2@gmail.com")
    assert rep_queryset.count() == 1
    assert rep_queryset.first().phone == "061234567"


@pytest.mark.django_db
def test_dataset_member_update_phone(app: DjangoTestApp, dataset):
    ds = DatasetFactory()
    ct = ContentType.objects.get_for_model(Dataset)

    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=ds.pk,
        role=Representative.COORDINATOR,
    )
    app.set_user(coordinator.user)
    resp = app.get(reverse("dataset-members", kwargs={"pk": ds.pk}))
    resp = resp.click(linkid=f"update-member-{coordinator.pk}-btn")
    form = resp.forms["representative-form"]
    form["phone"] = "061234567"
    resp = form.submit()
    assert resp.status_code == 302
    coordinator.refresh_from_db()
    assert coordinator.phone == "061234567"


@pytest.mark.haystack
def test_organization_dataset_list_with_matching_jurisdiction(app: DjangoTestApp):
    jurisdiction = AreaOfManagementFactory(name_lt="Organization")
    organization = OrganizationFactory(title="Organization", jurisdiction=jurisdiction)
    dataset1 = DatasetFactory(organization=organization)
    dataset2 = DatasetFactory(organization=organization)
    resp = app.get(
        "%s?selected_facets=organization_exact:%s"
        % (reverse("organization-datasets", args=[organization.pk]), organization.pk)
    )
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
        [dataset1.pk, dataset2.pk]
    )


@pytest.mark.django_db
def test_create_dataset_change_creator(app):
    frequency = FrequencyFactory(is_default=True)

    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)

    RepresentativeFactory(
        user=None,
        organization=publisher_org,
        role=Representative.MANAGER,
        object_id=org.pk,
        content_type=ContentType.objects.get_for_model(org),
    )

    subclass = DCATResourceSubclassFactory()
    user = UserFactory(is_staff=True, organization=publisher_org)
    app.set_user(user)

    form = app.get(
        reverse(
            "dataset-add", kwargs={"pk": publisher_org.id, "subclass_uuid": subclass.pk}
        )
    ).forms["dataset-form"]

    assert isinstance(form.fields["publisher"][0], webtest.forms.Hidden)
    assert not isinstance(form.fields["creator"][0], webtest.forms.Hidden)

    form["title"] = "Test Dataset"
    form["description"] = "This is a test dataset."
    form["frequency"] = str(frequency.pk)
    form["creator"] = str(org.pk)
    form["access_rights"] = Dataset.PUBLIC

    response = form.submit()

    assert response.status_code == 302
    assert Dataset.objects.filter(translations__title="Test Dataset").exists()
    ds = Dataset.objects.filter(translations__title="Test Dataset").first()
    assert ds.organization == org
    assert ds.publisher == publisher_org


@pytest.mark.django_db
def test_create_dataset_change_publisher(app):
    frequency = FrequencyFactory(is_default=True)

    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    subclass = DCATResourceSubclassFactory()
    RepresentativeFactory(
        user=None,
        organization=publisher_org,
        role=Representative.MANAGER,
        object_id=org.pk,
        content_type=ContentType.objects.get_for_model(org),
    )

    user = UserFactory(is_staff=True, organization=org)
    app.set_user(user)

    form = app.get(
        reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})
    ).forms["dataset-form"]

    assert not isinstance(form.fields["publisher"][0], webtest.forms.Hidden)
    assert isinstance(form.fields["creator"][0], webtest.forms.Hidden)

    form["title"] = "Test Dataset"
    form["description"] = "This is a test dataset."
    form["frequency"] = str(frequency.pk)
    form["publisher"] = str(publisher_org.pk)
    form["access_rights"] = Dataset.PUBLIC

    response = form.submit()

    assert response.status_code == 302
    assert Dataset.objects.filter(translations__title="Test Dataset").exists()
    ds = Dataset.objects.filter(translations__title="Test Dataset").first()
    assert ds.organization == org
    assert ds.publisher == publisher_org


@pytest.mark.django_db
def test_create_dataset_creator_options(app):
    org = OrganizationFactory()
    org2 = OrganizationFactory()
    org3 = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    subclass = DCATResourceSubclassFactory()
    for org_instance in [org, org2, org3]:
        RepresentativeFactory(
            user=None,
            organization=publisher_org,
            role=Representative.MANAGER,
            object_id=org_instance.pk,
            content_type=ContentType.objects.get_for_model(org),
        )

    user = UserFactory(is_staff=False, organization=publisher_org)
    app.set_user(user)
    form = app.get(
        reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})
    ).forms["dataset-form"]
    options = [option[2] for option in form.fields["creator"][0].options]
    assert len(options) == 5  # includes default option
    assert org.title in options
    assert org2.title in options
    assert org3.title in options
    assert publisher_org.title in options


@pytest.mark.django_db
def test_create_dataset_publisher_options(app):
    org = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    publisher_org2 = OrganizationFactory(publisher=True)
    publisher_org3 = OrganizationFactory(publisher=True)
    subclass = DCATResourceSubclassFactory()
    user = UserFactory(is_staff=True, organization=org)
    app.set_user(user)
    form = app.get(
        reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})
    ).forms["dataset-form"]
    options = [option[2] for option in form.fields["publisher"][0].options]
    assert len(options) == 4  # includes default option
    assert publisher_org.title in options
    assert publisher_org2.title in options
    assert publisher_org3.title in options


@pytest.mark.django_db
def test_dataset_detail_with_publisher(app: DjangoTestApp):
    frequency = FrequencyFactory(is_default=True)
    organization = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)
    user = UserFactory(is_staff=True)

    ds = DatasetFactory(
        organization=organization, publisher=publisher_org, frequency=frequency
    )

    app.set_user(user)
    response = app.get(reverse("dataset-detail", kwargs={"pk": ds.pk}))
    assert response.status_code == 200
    assert publisher_org.title in response.text
    assert publisher_org.email in response.text
    assert publisher_org.phone in response.text


@pytest.mark.django_db
def test_dataset_filter_by_publisher(app: DjangoTestApp):
    publisher1 = OrganizationFactory(publisher=True)
    publisher2 = OrganizationFactory(publisher=True)
    DatasetFactory(publisher=publisher1)
    DatasetFactory(publisher=publisher1)
    DatasetFactory(publisher=publisher2)

    user = UserFactory(is_staff=True)
    app.set_user(user)

    response = app.get(
        reverse("dataset-list") + f"?selected_facets=publisher_exact:{publisher1.pk}"
    )
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 2
    for ds in response.context["object_list"]:
        assert ds.publisher == [publisher1.pk]

    response = app.get(
        reverse("dataset-list") + f"?selected_facets=publisher_exact:{publisher2.pk}"
    )
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 1
    for ds in response.context["object_list"]:
        assert ds.publisher == [publisher2.pk]


@pytest.mark.django_db
def test_dataset_update_contact(app: DjangoTestApp):
    org = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=org)
    app.set_user(user)
    ds = DatasetFactory(organization=org)

    form = app.get(reverse("dataset-change", args=[ds.pk])).forms["dataset-form"]
    form["contact"] = f"org-{org.pk}"
    form.submit()
    assert Contact.objects.filter(
        dataset=ds,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
    ).exists()

    form = app.get(reverse("dataset-change", args=[ds.pk])).forms["dataset-form"]
    form["contact"] = f"user-{user.pk}"
    form.submit()
    assert Contact.objects.filter(dataset=ds).count() == 1
    assert Contact.objects.filter(
        dataset=ds,
        content_type=ContentType.objects.get_for_model(user),
        object_id=user.pk,
    ).exists()


@pytest.mark.django_db
def test_dataset_update_contact_options(app: DjangoTestApp):
    org = OrganizationFactory()
    org2 = OrganizationFactory()
    publisher_org = OrganizationFactory(publisher=True)

    user = UserFactory(is_staff=True, organization=org)
    user2 = UserFactory(is_staff=True, organization=org)
    user3 = UserFactory(is_staff=True)
    publisher_user = UserFactory(is_staff=True, organization=publisher_org)
    app.set_user(user)

    ds = DatasetFactory(organization=org, publisher=publisher_org)
    form = app.get(reverse("dataset-change", args=[ds.pk])).forms["dataset-form"]

    form_options = sorted([option[2] for option in form.fields["contact"][0].options])
    correct_options = sorted(
        [
            "---------",
            org.title,
            publisher_org.title,
            f"{user.first_name} {user.last_name}",
            f"{user2.first_name} {user2.last_name}",
            f"{publisher_user.first_name} {publisher_user.last_name}",
        ]
    )
    incorrect_options = sorted(
        ["---------", org2.title, f"{user3.first_name} {user3.last_name}"]
    )
    assert form_options == correct_options
    assert form_options != incorrect_options


@pytest.mark.django_db
def test_dataset_view_publisher_contacts(app: DjangoTestApp):
    org = OrganizationFactory(website="https://org.lt")
    publisher_org = OrganizationFactory(publisher=True, website="https://publisher.lt")
    user = UserFactory(is_staff=True, organization=org)
    ds = DatasetFactory(organization=org, publisher=publisher_org)
    app.set_user(user)
    response = app.get(reverse("dataset-detail", args=[ds.pk]))
    assert response.status_code == 200

    assert org.title in response.text
    assert org.website in response.text

    assert publisher_org.title in response.text
    assert publisher_org.website in response.text
    assert publisher_org.email in response.text
    assert publisher_org.phone in response.text


@pytest.mark.django_db
def test_dataset_view_user_contacts(app: DjangoTestApp):
    org = OrganizationFactory(website="https://org.lt")
    publisher_org = OrganizationFactory(publisher=True, website="https://publisher.lt")
    user = UserFactory(is_staff=True, organization=org)
    ds = DatasetFactory(organization=org, publisher=publisher_org)
    ContactFactory(
        dataset=ds,
        object_id=user.pk,
        content_type=ContentType.objects.get_for_model(user),
        email=user.email,
        phone=user.phone,
    )

    app.set_user(user)

    response = app.get(reverse("dataset-detail", args=[ds.pk]))
    assert response.status_code == 200

    assert org.title in response.text
    assert org.website in response.text

    assert publisher_org.title in response.text
    assert publisher_org.website in response.text

    assert user.get_full_name() in response.text
    assert user.email in response.text
    assert user.phone in response.text


@pytest.mark.django_db
def test_dataset_view_organization_contacts(app: DjangoTestApp):
    org = OrganizationFactory(website="https://org.lt")
    publisher_org = OrganizationFactory(publisher=True, website="https://publisher.lt")
    user = UserFactory(is_staff=True, organization=org)
    ds = DatasetFactory(organization=org, publisher=publisher_org)
    ContactFactory(
        dataset=ds,
        object_id=org.pk,
        content_type=ContentType.objects.get_for_model(org),
        email=org.email,
        phone=org.phone,
    )

    app.set_user(user)

    response = app.get(reverse("dataset-detail", args=[ds.pk]))
    assert response.status_code == 200

    assert org.title in response.text
    assert org.website in response.text
    assert org.email in response.text
    assert org.phone in response.text

    assert publisher_org.title in response.text
    assert publisher_org.website in response.text


@pytest.mark.django_db
def test_dataset_landing_page(app: DjangoTestApp):
    frequency = FrequencyFactory(is_default=True)
    org = OrganizationFactory()
    dataset = DatasetFactory(frequency=frequency, organization=org)
    user = UserFactory(is_staff=True)
    app.set_user(user)
    form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms[
        "dataset-form"
    ]
    form["landing_page"] = "https://example.com"
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse("dataset-detail", kwargs={"pk": dataset.id})
    assert dataset.landing_page == "https://example.com"


@pytest.mark.django_db
def test_dataset_rdf_download__dataset_with_landing_page(app: DjangoTestApp):
    iana = "http://www.iana.org/assignments"
    po = "http://publications.europa.eu/resource/authority"

    dataset = DatasetFactory(
        title={
            "lt": "Testas1",
            "en": "Test1",
        },
        description={
            "lt": "Duomenų rinkinio aprašymas.",
            "en": "Dataset description.",
        },
        published=datetime(2016, 8, 1),
        frequency=FrequencyFactory(uri=f"{po}/frequency/IRREG"),
        category=[
            CategoryFactory(title="Energy"),
            CategoryFactory(
                title="Environment",
                uri=f"{po}/data-theme/ENVI",
            ),
        ],
        organization=OrganizationFactory(
            title="Data Enterprise",
            email="data@example.com",
        ),
        landing_page="https://landing-page.com",
    )
    dist1 = DatasetDistributionFactory(
        dataset=dataset,
        title="Failas 1",
        description="Failas su prieigos nuoroda",
        format=FileFormat(
            uri=f"{po}/file-type/CSV",
            media_type_uri=f"{iana}/media-types/text/csv",
        ),
        access_url="https://access-url.com",
        licence=LicenceFactory(url=f"{po}/licence/CC_BY_4_0"),
        conditions="platinimo sąlygos",
    )
    dist2 = DatasetDistributionFactory(
        dataset=dataset,
        title="Failas 2",
        description="Failas be prieigos nuorodos",
        format=FileFormat(
            uri=f"{po}/file-type/JSON",
            media_type_uri=f"{iana}/media-types/application/json",
        ),
        licence=LicenceFactory(url=f"{po}/licence/CC_BY_4_0"),
        conditions="platinimo sąlygos",
    )

    res = app.get(reverse("dataset-rdf-download", args=[dataset.pk]))

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/rdf+xml"
    assert (
        strip_empty_lines(res.text)
        == f'''\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://example.com"
    xmlns:edp="https://europeandataportal.eu/voc#"
    xmlns:dct="http://purl.org/dc/terms/"
    xmlns:spdx="http://spdx.org/rdf/terms#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:j.0="http://data.europa.eu/88u/ontology/dcatapop#"
    xmlns:adms="http://www.w3.org/ns/adms#"
    xmlns:dqv="http://www.w3.org/ns/dqv#"
    xmlns:vcard="http://www.w3.org/2006/vcard/ns#"
    xmlns:skos="http://www.w3.org/2004/02/skos/core#"
    xmlns:schema="http://schema.org/"
    xmlns:dcat="http://www.w3.org/ns/dcat#"
    xmlns:foaf="http://xmlns.com/foaf/0.1/"
    xmlns:dcatap="http://data.europa.eu/r5r/"
    xmlns:eli="https://data.europa.eu/eli/">
    <dcat:Dataset rdf:about="http://example.com/datasets/{dataset.id}/">
        <dct:title xml:lang="en">Test1</dct:title>
        <dct:description xml:lang="en">Dataset description.</dct:description>
        <dct:title xml:lang="lt">Testas1</dct:title>
        <dct:description xml:lang="lt">Duomenų rinkinio aprašymas.</dct:description>
        <dcat:theme>
            <skos:Concept>
                <skos:prefLabel xml:lang="lt">Energy</skos:prefLabel>
            </skos:Concept>
        </dcat:theme>
        <dcat:theme>
            <skos:Concept rdf:about="http://publications.europa.eu/resource/authority/data-theme/ENVI"/>
        </dcat:theme>
        <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2016-08-01</dct:issued>
        <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dataset.modified.strftime("%Y-%m-%d")}</dct:modified>
        <dct:accessRights rdf:resource="http://publications.europa.eu/resource/authority/access-right/PUBLIC"/>
        <dct:publisher>
            <foaf:Organization>
                <foaf:name>Data Enterprise</foaf:name>
                <foaf:mbox rdf:resource="mailto:data@example.com"/>
            </foaf:Organization>
        </dct:publisher>
        <dct:accrualPeriodicity>
            <dct:Frequency rdf:about="http://publications.europa.eu/resource/authority/frequency/IRREG"/>
        </dct:accrualPeriodicity>
        <dcat:contactPoint>
            <vcard:Kind>
                <vcard:hasEmail rdf:resource="mailto:data@example.com"/>
            </vcard:Kind>
        </dcat:contactPoint>
        <dcat:landingPage rdf:resource="https://landing-page.com"/>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist1.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">Failas 1</dct:title>
                <dct:description xml:lang="lt">Failas su prieigos nuoroda</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{dist1.access_url}"/>
                <dcat:downloadURL rdf:resource="http://example.com{dist1.file.url}"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/text/csv"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/CSV"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist2.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">Failas 2</dct:title>
                <dct:description xml:lang="lt">Failas be prieigos nuorodos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{dataset.landing_page}"/>
                <dcat:downloadURL rdf:resource="http://example.com{dist2.file.url}"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/application/json"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/JSON"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
    </dcat:Dataset>
</rdf:RDF>'''
    )


@pytest.mark.django_db
def test_dataset_rdf_download__dataset_without_landing_page(app: DjangoTestApp):
    iana = "http://www.iana.org/assignments"
    po = "http://publications.europa.eu/resource/authority"

    dataset = DatasetFactory(
        title={
            "lt": "Testas1",
            "en": "Test1",
        },
        description={
            "lt": "Duomenų rinkinio aprašymas.",
            "en": "Dataset description.",
        },
        published=datetime(2016, 8, 1),
        frequency=FrequencyFactory(uri=f"{po}/frequency/IRREG"),
        category=[
            CategoryFactory(title="Energy"),
            CategoryFactory(
                title="Environment",
                uri=f"{po}/data-theme/ENVI",
            ),
        ],
        organization=OrganizationFactory(
            title="Data Enterprise",
            email="data@example.com",
        ),
    )
    dist1 = DatasetDistributionFactory(
        dataset=dataset,
        title="Failas 1",
        description="Failas su prieigos nuoroda",
        format=FileFormat(
            uri=f"{po}/file-type/CSV",
            media_type_uri=f"{iana}/media-types/text/csv",
        ),
        access_url="https://access-url.com",
        licence=LicenceFactory(url=f"{po}/licence/CC_BY_4_0"),
        conditions="platinimo sąlygos",
    )
    dist2 = DatasetDistributionFactory(
        dataset=dataset,
        title="Failas 2",
        description="Failas be prieigos nuorodos",
        format=FileFormat(
            uri=f"{po}/file-type/JSON",
            media_type_uri=f"{iana}/media-types/application/json",
        ),
        licence=LicenceFactory(url=f"{po}/licence/CC_BY_4_0"),
        conditions="platinimo sąlygos",
    )

    res = app.get(reverse("dataset-rdf-download", args=[dataset.pk]))

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/rdf+xml"
    assert (
        strip_empty_lines(res.text)
        == f'''\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://example.com"
    xmlns:edp="https://europeandataportal.eu/voc#"
    xmlns:dct="http://purl.org/dc/terms/"
    xmlns:spdx="http://spdx.org/rdf/terms#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:j.0="http://data.europa.eu/88u/ontology/dcatapop#"
    xmlns:adms="http://www.w3.org/ns/adms#"
    xmlns:dqv="http://www.w3.org/ns/dqv#"
    xmlns:vcard="http://www.w3.org/2006/vcard/ns#"
    xmlns:skos="http://www.w3.org/2004/02/skos/core#"
    xmlns:schema="http://schema.org/"
    xmlns:dcat="http://www.w3.org/ns/dcat#"
    xmlns:foaf="http://xmlns.com/foaf/0.1/"
    xmlns:dcatap="http://data.europa.eu/r5r/"
    xmlns:eli="https://data.europa.eu/eli/">
    <dcat:Dataset rdf:about="http://example.com/datasets/{dataset.id}/">
        <dct:title xml:lang="en">Test1</dct:title>
        <dct:description xml:lang="en">Dataset description.</dct:description>
        <dct:title xml:lang="lt">Testas1</dct:title>
        <dct:description xml:lang="lt">Duomenų rinkinio aprašymas.</dct:description>
        <dcat:theme>
            <skos:Concept>
                <skos:prefLabel xml:lang="lt">Energy</skos:prefLabel>
            </skos:Concept>
        </dcat:theme>
        <dcat:theme>
            <skos:Concept rdf:about="http://publications.europa.eu/resource/authority/data-theme/ENVI"/>
        </dcat:theme>
        <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2016-08-01</dct:issued>
        <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dataset.modified.strftime("%Y-%m-%d")}</dct:modified>
        <dct:accessRights rdf:resource="http://publications.europa.eu/resource/authority/access-right/PUBLIC"/>
        <dct:publisher>
            <foaf:Organization>
                <foaf:name>Data Enterprise</foaf:name>
                <foaf:mbox rdf:resource="mailto:data@example.com"/>
            </foaf:Organization>
        </dct:publisher>
        <dct:accrualPeriodicity>
            <dct:Frequency rdf:about="http://publications.europa.eu/resource/authority/frequency/IRREG"/>
        </dct:accrualPeriodicity>
        <dcat:contactPoint>
            <vcard:Kind>
                <vcard:hasEmail rdf:resource="mailto:data@example.com"/>
            </vcard:Kind>
        </dcat:contactPoint>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist1.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">Failas 1</dct:title>
                <dct:description xml:lang="lt">Failas su prieigos nuoroda</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{dist1.access_url}"/>
                <dcat:downloadURL rdf:resource="http://example.com{dist1.file.url}"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/text/csv"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/CSV"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist2.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">Failas 2</dct:title>
                <dct:description xml:lang="lt">Failas be prieigos nuorodos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="http://example.com{dist2.file.url}"/>
                <dcat:downloadURL rdf:resource="http://example.com{dist2.file.url}"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/application/json"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/JSON"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
    </dcat:Dataset>
</rdf:RDF>'''
    )


@pytest.mark.django_db
def test_dataset_rdf_download__dataset_with_spinta_data(app: DjangoTestApp):
    iana = "http://www.iana.org/assignments"
    po = "http://publications.europa.eu/resource/authority"

    dataset = DatasetFactory(
        title={
            "lt": "Testas1",
            "en": "Test1",
        },
        description={
            "lt": "Duomenų rinkinio aprašymas.",
            "en": "Dataset description.",
        },
        published=datetime(2016, 8, 1),
        frequency=FrequencyFactory(uri=f"{po}/frequency/IRREG"),
        category=[
            CategoryFactory(title="Energy"),
            CategoryFactory(
                title="Environment",
                uri=f"{po}/data-theme/ENVI",
            ),
        ],
        organization=OrganizationFactory(
            title="Data Enterprise",
            email="data@example.com",
        ),
    )
    data_service = DatasetFactory(service=True)
    dist = DatasetDistributionFactory(
        dataset=dataset,
        title="Duomenys",
        description="Duomenys iš spintos",
        format=FileFormat(title="Saugyklos API", extension="UAPI"),
        uapi_format=True,
        data_service=data_service,
        licence=LicenceFactory(url=f"{po}/licence/CC_BY_4_0"),
        conditions="platinimo sąlygos",
    )
    model = ModelFactory(dataset=dataset, distribution=dist)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )
    (
        FileFormat(
            title="JSON",
            extension="JSON",
            uri=f"{po}/file-type/JSON",
            media_type_uri=f"{iana}/media-types/application/json",
        ),
    )
    (
        FileFormat(
            title="JSONL",
            extension="JSONL",
            uri=f"{po}/file-type/JSONL",
            media_type_uri=f"{iana}/media-types/application/jsonl",
        ),
    )
    (
        FileFormat(
            title="CSV",
            extension="CSV",
            uri=f"{po}/file-type/CSV",
            media_type_uri=f"{iana}/media-types/application/csv",
        ),
    )
    (
        FileFormat(
            title="RDF",
            extension="RDF",
            uri=f"{po}/file-type/RDF",
            media_type_uri=f"{iana}/media-types/application/rdf",
        ),
    )

    res = app.get(reverse("dataset-rdf-download", args=[dataset.pk]))

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/rdf+xml"
    assert (
        strip_empty_lines(res.text)
        == f'''\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://example.com"
    xmlns:edp="https://europeandataportal.eu/voc#"
    xmlns:dct="http://purl.org/dc/terms/"
    xmlns:spdx="http://spdx.org/rdf/terms#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:j.0="http://data.europa.eu/88u/ontology/dcatapop#"
    xmlns:adms="http://www.w3.org/ns/adms#"
    xmlns:dqv="http://www.w3.org/ns/dqv#"
    xmlns:vcard="http://www.w3.org/2006/vcard/ns#"
    xmlns:skos="http://www.w3.org/2004/02/skos/core#"
    xmlns:schema="http://schema.org/"
    xmlns:dcat="http://www.w3.org/ns/dcat#"
    xmlns:foaf="http://xmlns.com/foaf/0.1/"
    xmlns:dcatap="http://data.europa.eu/r5r/"
    xmlns:eli="https://data.europa.eu/eli/">
    <dcat:Dataset rdf:about="http://example.com/datasets/{dataset.id}/">
        <dct:title xml:lang="en">Test1</dct:title>
        <dct:description xml:lang="en">Dataset description.</dct:description>
        <dct:title xml:lang="lt">Testas1</dct:title>
        <dct:description xml:lang="lt">Duomenų rinkinio aprašymas.</dct:description>
        <dcat:theme>
            <skos:Concept>
                <skos:prefLabel xml:lang="lt">Energy</skos:prefLabel>
            </skos:Concept>
        </dcat:theme>
        <dcat:theme>
            <skos:Concept rdf:about="http://publications.europa.eu/resource/authority/data-theme/ENVI"/>
        </dcat:theme>
        <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2016-08-01</dct:issued>
        <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dataset.modified.strftime("%Y-%m-%d")}</dct:modified>
        <dct:accessRights rdf:resource="http://publications.europa.eu/resource/authority/access-right/PUBLIC"/>
        <dct:publisher>
            <foaf:Organization>
                <foaf:name>Data Enterprise</foaf:name>
                <foaf:mbox rdf:resource="mailto:data@example.com"/>
            </foaf:Organization>
        </dct:publisher>
        <dct:accrualPeriodicity>
            <dct:Frequency rdf:about="http://publications.europa.eu/resource/authority/frequency/IRREG"/>
        </dct:accrualPeriodicity>
        <dcat:contactPoint>
            <vcard:Kind>
                <vcard:hasEmail rdf:resource="mailto:data@example.com"/>
            </vcard:Kind>
        </dcat:contactPoint>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist.id}/dataset/json">
                <dct:type rdf:resource="URL"/>
                <dct:title xml:lang="lt">Duomenys</dct:title>
                <dct:description xml:lang="lt">Duomenys iš spintos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset"/>
                <dcat:downloadURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset/:all/:format/json"/>
                <dcat:accessService rdf:resource="http://example.com/datasets/{data_service.pk}/"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/application/json"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/JSON"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist.id}/dataset/jsonl">
                <dct:type rdf:resource="URL"/>
                <dct:title xml:lang="lt">Duomenys</dct:title>
                <dct:description xml:lang="lt">Duomenys iš spintos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset"/>
                <dcat:downloadURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset/:all/:format/jsonl"/>
                <dcat:accessService rdf:resource="http://example.com/datasets/{data_service.pk}/"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/application/jsonl"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/JSONL"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist.id}/dataset/rdf">
                <dct:type rdf:resource="URL"/>
                <dct:title xml:lang="lt">Duomenys</dct:title>
                <dct:description xml:lang="lt">Duomenys iš spintos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset"/>
                <dcat:downloadURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset/:all/:format/rdf"/>
                <dcat:accessService rdf:resource="http://example.com/datasets/{data_service.pk}/"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/application/rdf"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/RDF"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://example.com/datasets/{dataset.id}/resource/{dist.id}/TestModel/csv">
                <dct:type rdf:resource="URL"/>
                <dct:title xml:lang="lt">Duomenys</dct:title>
                <dct:description xml:lang="lt">Duomenys iš spintos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset"/>
                <dcat:downloadURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset/TestModel/:format/csv"/>
                <dcat:accessService rdf:resource="http://example.com/datasets/{data_service.pk}/"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about="http://www.iana.org/assignments/media-types/application/csv"/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/CSV"/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
    </dcat:Dataset>
</rdf:RDF>'''
    )


@pytest.mark.django_db
def test_dataset_rdf_download__datas_service(app: DjangoTestApp):
    iana = "http://www.iana.org/assignments"
    po = "http://publications.europa.eu/resource/authority"

    dataset = DatasetFactory(
        title={
            "lt": "Testas1",
            "en": "Test1",
        },
        description={
            "lt": "Duomenų rinkinio aprašymas.",
            "en": "Dataset description.",
        },
        published=datetime(2016, 8, 1),
        frequency=FrequencyFactory(uri=f"{po}/frequency/IRREG"),
        category=[
            CategoryFactory(title="Energy"),
            CategoryFactory(
                title="Environment",
                uri=f"{po}/data-theme/ENVI",
            ),
        ],
        organization=OrganizationFactory(
            title="Data Enterprise",
            email="data@example.com",
        ),
        service=True,
        endpoint_url="https://endpoint-url.com",
        endpoint_type=FileFormat(
            uri=f"{po}/file-type/WMS",
            media_type_uri=f"{iana}/media-types/application/wms",
        ),
        endpoint_description="https://endpoint-description.com",
    )
    service_type = TypeFactory(name=Type.SERVICE)
    dataset.type.add(service_type)
    relation = DatasetRelationFactory(
        part_of=dataset, relation=RelationFactory(name=Relation.SERVICE)
    )
    relation.dataset.part_of.add(relation)

    res = app.get(reverse("dataset-rdf-download", args=[dataset.pk]))

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/rdf+xml"
    assert (
        strip_empty_lines(res.text)
        == f"""\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://example.com"
    xmlns:edp="https://europeandataportal.eu/voc#"
    xmlns:dct="http://purl.org/dc/terms/"
    xmlns:spdx="http://spdx.org/rdf/terms#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:j.0="http://data.europa.eu/88u/ontology/dcatapop#"
    xmlns:adms="http://www.w3.org/ns/adms#"
    xmlns:dqv="http://www.w3.org/ns/dqv#"
    xmlns:vcard="http://www.w3.org/2006/vcard/ns#"
    xmlns:skos="http://www.w3.org/2004/02/skos/core#"
    xmlns:schema="http://schema.org/"
    xmlns:dcat="http://www.w3.org/ns/dcat#"
    xmlns:foaf="http://xmlns.com/foaf/0.1/"
    xmlns:dcatap="http://data.europa.eu/r5r/"
    xmlns:eli="https://data.europa.eu/eli/">
    <dcat:DataService rdf:about="http://example.com/datasets/{dataset.id}/">
        <dct:title xml:lang="en">Test1</dct:title>
        <dct:description xml:lang="en">Dataset description.</dct:description>
        <dct:title xml:lang="lt">Testas1</dct:title>
        <dct:description xml:lang="lt">Duomenų rinkinio aprašymas.</dct:description>
        <dcat:theme>
            <skos:Concept>
                <skos:prefLabel xml:lang="lt">Energy</skos:prefLabel>
            </skos:Concept>
        </dcat:theme>
        <dcat:theme>
            <skos:Concept rdf:about="http://publications.europa.eu/resource/authority/data-theme/ENVI"/>
        </dcat:theme>
        <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2016-08-01</dct:issued>
        <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dataset.modified.strftime("%Y-%m-%d")}</dct:modified>
        <dct:accessRights rdf:resource="http://publications.europa.eu/resource/authority/access-right/PUBLIC"/>
        <dct:publisher>
            <foaf:Organization>
                <foaf:name>Data Enterprise</foaf:name>
                <foaf:mbox rdf:resource="mailto:data@example.com"/>
            </foaf:Organization>
        </dct:publisher>
        <dct:accrualPeriodicity>
            <dct:Frequency rdf:about="http://publications.europa.eu/resource/authority/frequency/IRREG"/>
        </dct:accrualPeriodicity>
        <dcat:contactPoint>
            <vcard:Kind>
                <vcard:hasEmail rdf:resource="mailto:data@example.com"/>
            </vcard:Kind>
        </dcat:contactPoint>
        <dcat:endpointURL rdf:resource="https://endpoint-url.com"/>
        <dct:format>
            <dct:MediaTypeOrExtent rdf:about="http://publications.europa.eu/resource/authority/file-type/WMS"/>
        </dct:format>
        <dcat:endpointDescription rdf:resource="https://endpoint-description.com"/>
        <dcat:servesDataset>
            <dcat:Dataset rdf:about="http://example.com/datasets/{relation.dataset.pk}/" />
        </dcat:servesDataset>
    </dcat:DataService>
</rdf:RDF>"""
    )

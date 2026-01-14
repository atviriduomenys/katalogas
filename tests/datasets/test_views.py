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
from filer.models import File
from reversion.models import Version
from webtest import Upload
from unittest.mock import patch

from vitrina.catalogs.factories import CatalogFactory
from vitrina.classifiers.factories import (
    CategoryFactory,
    FrequencyFactory,
    AreaOfManagementFactory,
    ConceptFactory,
    DocumentationFactory,
)
from vitrina.classifiers.factories import LicenceFactory, ApplicableLegislationFactory
from vitrina.classifiers.models import Category, AreaOfManagement, ConceptSchema
from vitrina.comments.factories import CommentFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import (
    DatasetFactory,
    DatasetGroupFactory,
    AttributionFactory,
    DatasetAttributionFactory,
    TypeFactory,
    RelationFactory,
    DatasetRelationFactory,
    ContactFactory,
    DCATResourceSubclassFactory,
    DatasetGroupCategoryUriFactory,
)
from vitrina.datasets.factories import MANIFEST
from vitrina.datasets.forms import (
    ResourceForm,
    ServiceResourceForm,
    BaseResourceForm,
    InformationSystemResourceForm,
    DatasetResourceForm,
    CatalogResourceForm,
)
from vitrina.datasets.models import Dataset, DatasetStructure, Type, Relation
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative, Organization
from vitrina.plans.factories import PlanFactory
from vitrina.plans.models import Plan, PlanDataset
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestObjectFactory, RequestFactory
from vitrina.requests.models import RequestObject
from vitrina.resources.factories import DatasetDistributionFactory, FileFormat
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure.factories import ModelFactory, MetadataFactory, VersionFactory
from vitrina.structure import VersionStatus
from vitrina.testing.templates import strip_empty_lines
from vitrina.users.factories import UserFactory, ManagerFactory
from vitrina.users.models import User
from vitrina.identifiers.factories import IdentifierFactory
from vitrina.identifiers.models import Identifier, Agency
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.utils import RevisionComment, RevisionSource

pytestmark = pytest.mark.django_db
timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.fixture
def dataset_detail_data() -> dict:
    dataset = DatasetFactory()
    dataset_distribution = DatasetDistributionFactory(dataset=dataset)
    return {
        "dataset": dataset_distribution.dataset,
        "dataset_distribution": dataset_distribution,
    }


@pytest.fixture
def search_datasets() -> list[Dataset]:
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


@pytest.fixture
def category_filter_data() -> dict[str, list[Category]]:
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


@pytest.fixture
def status_filter_data() -> list[Dataset]:
    dataset1 = DatasetFactory()
    dataset2 = DatasetFactory(status=Dataset.INVENTORED)
    return [dataset1, dataset2]


@pytest.fixture
def organization_filter_data() -> dict:
    organization = OrganizationFactory()

    dataset1 = DatasetFactory(organization=organization, slug="ds1")
    dataset2 = DatasetFactory(organization=organization, slug="ds2")

    return {"organization": organization, "datasets": [dataset1, dataset2]}


@pytest.fixture
def datasets() -> list[Dataset]:
    dataset1 = DatasetFactory(tags=("tag1", "tag2", "tag3"), slug="ds1")
    dataset2 = DatasetFactory(tags=("tag3", "tag4", "tag5"), slug="ds2")

    return [dataset1, dataset2]


@pytest.fixture
def frequency_filter_data() -> dict:
    frequency = FrequencyFactory()
    organization = OrganizationFactory()

    dataset1 = DatasetFactory(frequency=frequency, organization=organization)
    dataset2 = DatasetFactory(frequency=frequency, organization=organization)

    return {"frequency": frequency, "datasets": [dataset1, dataset2]}


@pytest.fixture
def date_filter_data() -> list[Dataset]:
    org = OrganizationFactory()
    dataset1 = DatasetFactory(organization=org, slug="ds1", published=timezone.localize(datetime(2022, 3, 1)))
    dataset2 = DatasetFactory(organization=org, slug="ds2", published=timezone.localize(datetime(2022, 2, 1)))
    dataset3 = DatasetFactory(organization=org, slug="ds3", published=timezone.localize(datetime(2021, 12, 1)))
    return [dataset1, dataset2, dataset3]


def _get_selected(context: dict) -> dict:
    selected = {f.name: [i.value for i in f.items() if i.selected] for f in context["filters"]}
    selected = {k: (v[0] if len(v) == 1 else v) for k, v in selected.items() if v}
    return selected


def parse_table(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "resource-table"})
    rows = table.find("tbody").find_all("tr")

    data = []
    for row in rows:
        cols = row.find_all("td")
        cols = [col.get_text(strip=True) for col in cols]
        data.append(cols)

    return data


class TestDatasetDetailView:
    def test_dataset_detail_without_tags(self, app: DjangoTestApp, dataset_detail_data: dict):
        resp = app.get(dataset_detail_data["dataset"].get_absolute_url()).follow()
        assert resp.context["tags"] == []

    def test_dataset_detail_tags(self, app: DjangoTestApp, dataset_detail_data: dict):
        dataset = DatasetFactory(tags=("tag-1", "tag-2", "tag-3"), status="HAS_DATA")
        resp = app.get(dataset.get_absolute_url()).follow()
        assert len(resp.context["tags"]) == 3
        assert resp.context["tags"] == [
            {"name": "tag-1", "pk": dataset.tags.get(name="tag-1").pk},
            {"name": "tag-2", "pk": dataset.tags.get(name="tag-2").pk},
            {"name": "tag-3", "pk": dataset.tags.get(name="tag-3").pk},
        ]

    def test_dataset_detail_status(self, app: DjangoTestApp, dataset_detail_data: dict):
        resp = app.get(dataset_detail_data["dataset"].get_absolute_url()).follow()
        assert resp.context["status"] == "Atvertas"

    def test_dataset_detail_resources(self, app: DjangoTestApp, dataset_detail_data: dict):
        resp = app.get(dataset_detail_data["dataset"].get_absolute_url()).follow()
        assert list(resp.context["resources"]) == [dataset_detail_data["dataset_distribution"]]

    def test_dataset_resource_create_button(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        resp = app.get(dataset.get_absolute_url()).follow()
        resp = resp.click(linkid="add_resource")
        assert resp.request.path == reverse("resource-add", args=[dataset.pk])

    def test_click_edit_button(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(
            published=timezone.localize(datetime(2022, 9, 7)),
            slug="test-dataset-slug",
            organization=org,
        )
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset.manager = user
        response = app.get(reverse("dataset-detail", kwargs={"pk": dataset.id})).follow()
        response.click(linkid="change_dataset")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "role",
        [
            (Representative.OPEN_DATA_MANAGER),
            (Representative.RESOURCE_MANAGER),
        ],
    )
    def test_view_non_public_dataset_with_org_representative(self, app: DjangoTestApp, role: str):
        dataset = DatasetFactory(is_public=False)
        user = UserFactory()
        organization = OrganizationFactory()
        user.organization = organization
        user.save()

        RepresentativeFactory(
            organization=organization,
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
            role=role,
        )

        app.set_user(user)
        response = app.get(reverse("dataset-detail", args=[dataset.pk])).follow()
        assert response.status_code == 200
        assert response.context["dataset"] == dataset

    def test_dataset_detail_with_publisher(self, app: DjangoTestApp):
        frequency = FrequencyFactory(is_default=True)
        organization = OrganizationFactory()
        publisher_org = OrganizationFactory(publisher=True)
        user = UserFactory(is_staff=True)

        ds = DatasetFactory(organization=organization, publisher=publisher_org, frequency=frequency)

        app.set_user(user)
        response = app.get(reverse("dataset-detail", kwargs={"pk": ds.pk})).follow()
        assert response.status_code == 200
        assert publisher_org.title in response.text
        assert publisher_org.email in response.text
        assert publisher_org.phone in response.text

    def test_dataset_view_publisher_contacts(self, app: DjangoTestApp):
        org = OrganizationFactory(website="https://org.lt")
        publisher_org = OrganizationFactory(publisher=True, website="https://publisher.lt")
        user = UserFactory(is_staff=True, organization=org)
        ds = DatasetFactory(organization=org, publisher=publisher_org)
        app.set_user(user)
        response = app.get(reverse("dataset-detail", args=[ds.pk])).follow()
        assert response.status_code == 200

        assert org.title in response.text
        assert org.website in response.text

        assert publisher_org.title in response.text
        assert publisher_org.website in response.text
        assert publisher_org.email in response.text
        assert publisher_org.phone in response.text

    def test_dataset_view_user_contacts(self, app: DjangoTestApp):
        org = OrganizationFactory(website="https://org.lt")
        publisher_org = OrganizationFactory(publisher=True, website="https://publisher.lt")
        user = UserFactory(is_staff=True, organization=org)
        contact = ContactFactory(
            organization=org,
            object_id=user.pk,
            content_type=ContentType.objects.get_for_model(user),
            email=user.email,
            phone=user.phone,
        )
        ds = DatasetFactory(organization=org, publisher=publisher_org, contact=contact)

        app.set_user(user)

        response = app.get(reverse("dataset-detail", args=[ds.pk])).follow()
        assert response.status_code == 200

        assert org.title in response.text
        assert org.website in response.text

        assert publisher_org.title in response.text
        assert publisher_org.website in response.text

        assert user.get_full_name() in response.text
        assert user.email in response.text
        assert user.phone in response.text

    def test_dataset_view_organization_contacts(self, app: DjangoTestApp):
        org = OrganizationFactory(website="https://org.lt")
        publisher_org = OrganizationFactory(publisher=True, website="https://publisher.lt")
        user = UserFactory(is_staff=True, organization=org)
        ds = DatasetFactory(organization=org, publisher=publisher_org)
        ContactFactory(
            organization=org,
            object_id=org.pk,
            content_type=ContentType.objects.get_for_model(org),
            email=org.email,
            phone=org.phone,
        )

        app.set_user(user)

        response = app.get(reverse("dataset-detail", args=[ds.pk])).follow()
        assert response.status_code == 200

        assert org.title in response.text
        assert org.website in response.text
        assert org.email in response.text
        assert org.phone in response.text

        assert publisher_org.title in response.text
        assert publisher_org.website in response.text


@pytest.mark.haystack
class TestDatasetListView:
    def test_dataset_list_view_anon_user_with_datasets(self, app: DjangoTestApp):
        DatasetFactory()
        DatasetFactory()
        DatasetFactory()
        resp = app.get(reverse("dataset-list"))
        assert len(resp.context["object_list"]) == 3

    def test_dataset_list_view_anon_user_without_datasets(self, app: DjangoTestApp):
        resp = app.get(reverse("dataset-list"))
        assert len(resp.context["object_list"]) == 0

    def test_dataset_list_view_all_shown_for_staff(self, app: DjangoTestApp):
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

    def test_dataset_list_view_public_shown_for_regular_user(self, app: DjangoTestApp):
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

    def test_org_dataset_url_is_hidden_for_anon_user(self, app: DjangoTestApp):
        resp = app.get(reverse("dataset-list"))
        assert not resp.html.find(id="org-dataset-url")

    def test_manager_dataset_url_is_hidden_for_anon_user(self, app: DjangoTestApp):
        resp = app.get(reverse("dataset-list"))
        assert not resp.html.find(id="manager-dataset-url")

    def test_org_dataset_url_is_hidden_for_normal_user(self, app: DjangoTestApp):
        user = User.objects.create_user(email="test@test.com", password="test123")
        app.set_user(user)
        resp = app.get(reverse("dataset-list"))
        assert not resp.html.find(id="org-dataset-url")

    def test_manager_dataset_url_is_hidden_for_normal_user(self, app: DjangoTestApp):
        user = User.objects.create_user(email="test@test.com", password="test123")
        app.set_user(user)
        resp = app.get(reverse("dataset-list"))
        assert not resp.html.find(id="manager-dataset-url")

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_MANAGER,
            Representative.RESOURCE_MANAGER,
        ],
    )
    def test_manager_dataset_url_is_hidden_for_manager_if_no_datasets(self, app: DjangoTestApp, role: str):
        org = OrganizationFactory()
        ct = ContentType.objects.get_for_model(Dataset)
        rep = RepresentativeFactory(
            content_type=ct,
            object_id=org.pk,
            role=role,
        )
        app.set_user(rep.user)
        resp = app.get(reverse("dataset-list"))
        assert not resp.html.find(id="manager-dataset-url")

    def test_org_dataset_url_is_shown_for_coordinator(self, app: DjangoTestApp):
        org = OrganizationFactory()
        DatasetFactory(organization=org)
        user = User.objects.create_user(email="test@test.com", password="test123", organization=org)
        app.set_user(user)
        resp = app.get(reverse("dataset-list"))
        assert resp.html.find(id="org-dataset-url")

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_MANAGER,
            Representative.RESOURCE_MANAGER,
        ],
    )
    def test_manager_dataset_url_is_shown_for_managers(self, app: DjangoTestApp, role):
        org = OrganizationFactory()
        DatasetFactory(organization=org)

        ct = ContentType.objects.get_for_model(Dataset)
        rep = RepresentativeFactory(
            content_type=ct,
            object_id=org.pk,
            role=role,
        )

        app.set_user(rep.user)
        resp = app.get(reverse("dataset-list"))

        assert resp.html.find(id="manager-dataset-url")

    def test_org_datasets_are_shown_for_coordinator(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(title="testt", organization=org)

        user = User.objects.create_user(
            email="test@test.com",
            password="test123",
            organization=org,
        )

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=org.pk,
            role=Representative.RESOURCE_COORDINATOR,
            user=user,
        )

        app.set_user(user)

        resp = app.get(reverse("dataset-list"))
        resp = resp.click(linkid="org-dataset-url")
        assert [int(obj.pk) for obj in resp.context["object_list"]] == [dataset.pk]

    def test_org_datasets_are_shown_for_open_data_coordinator(self, app: DjangoTestApp):
        org = OrganizationFactory()
        public_dataset = DatasetFactory(title="public_ds", organization=org, access_rights=Dataset.PUBLIC)
        restricted_dataset = DatasetFactory(title="restricted_ds", organization=org, access_rights=Dataset.RESTRICTED)
        confidential_dataset = DatasetFactory(
            title="confidential_ds", organization=org, access_rights=Dataset.NON_PUBLIC
        )

        user = User.objects.create_user(
            email="opendata@test.com",
            password="test123",
            organization=org,
        )
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=org.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
            user=user,
        )

        app.set_user(user)

        resp = app.get(reverse("dataset-list"))
        resp = resp.click(linkid="org-dataset-url")
        visible_dataset_ids = [int(obj.pk) for obj in resp.context["object_list"]]
        assert public_dataset.pk in visible_dataset_ids
        assert restricted_dataset.pk in visible_dataset_ids
        assert confidential_dataset.pk not in visible_dataset_ids

    def test_manager_datasets_are_shown_for_manager(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        ct = ContentType.objects.get_for_model(Organization)
        rep = RepresentativeFactory(
            content_type=ct,
            object_id=org.pk,
            role=Representative.OPEN_DATA_MANAGER,
        )
        app.set_user(rep.user)
        resp = app.get(reverse("dataset-list"))
        resp = resp.click(linkid="manager-dataset-url")
        assert [int(obj.pk) for obj in resp.context["object_list"]] == [dataset.pk]

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_MANAGER,
            Representative.RESOURCE_MANAGER,
        ],
    )
    def test_datasets_from_multiple_orgs_are_shown_for_manager(self, app: DjangoTestApp, role: str):
        org = OrganizationFactory()
        org2 = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        dataset2 = DatasetFactory(organization=org2)
        ct = ContentType.objects.get_for_model(Organization)
        user = User.objects.create_user(email="test@test.com", password="test123")
        RepresentativeFactory(content_type=ct, object_id=org.pk, role=role, user=user)
        RepresentativeFactory(content_type=ct, object_id=org2.pk, role=role, user=user)
        app.set_user(user)
        resp = app.get(reverse("dataset-list"))
        resp = resp.click(linkid="manager-dataset-url")
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted([dataset.pk, dataset2.pk])

    def test_search_without_query(self, app: DjangoTestApp, search_datasets: list[Dataset]):
        resp = app.get(reverse("dataset-list"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]
        )

    def test_search_with_query_that_doesnt_match(self, app: DjangoTestApp, search_datasets: list[Dataset]):
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "doesnt-match"))
        assert [int(obj.pk) for obj in resp.context["object_list"]] == []

    def test_search_with_query_that_matches_one(self, app: DjangoTestApp, search_datasets: list[Dataset]):
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "vienas"))
        assert [int(obj.pk) for obj in resp.context["object_list"]] == [search_datasets[0].pk]

    def test_search_with_query_that_matches_all(self, app: DjangoTestApp, search_datasets: list[Dataset]):
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "rinkinys"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]
        )

    def test_search_with_query_that_matches_all_with_english_title(
        self, app: DjangoTestApp, search_datasets: list[Dataset]
    ):
        for dataset in search_datasets:
            dataset.set_current_language("en")
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "Dataset"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [search_datasets[1].pk, search_datasets[2].pk, search_datasets[0].pk]
        )

    def test_search_with_query_that_matches_all_description(self, app: DjangoTestApp, search_datasets: list[Dataset]):
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "test_lt_desc"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [
                search_datasets[0].pk,
                search_datasets[1].pk,
                search_datasets[2].pk,
            ]
        )

    def test_search_with_query_that_matches_all_with_english_description(
        self, app: DjangoTestApp, search_datasets: list[Dataset]
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

    def test_search_with_query_that_matches_child_category(self, app: DjangoTestApp, search_datasets: list[Dataset]):
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "child1"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [
                search_datasets[2].pk,
            ]
        )

    def test_search_with_query_that_matches_category_and_parent_category(
        self, app: DjangoTestApp, search_datasets: list[Dataset]
    ):
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "parent1"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [
                search_datasets[0].pk,
                search_datasets[2].pk,
            ]
        )

    def test_search_with_query_that_matches_tag_of_one_dataset(
        self, app: DjangoTestApp, search_datasets: list[Dataset]
    ):
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "test_tag_1"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [
                search_datasets[0].pk,
            ]
        )

    def test_search_with_query_that_matches_tag_of_two_datasets(
        self, app: DjangoTestApp, search_datasets: list[Dataset]
    ):
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "test_tag_2"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [
                search_datasets[0].pk,
                search_datasets[1].pk,
            ]
        )

    def test_status_filter_without_query(self, app: DjangoTestApp, status_filter_data: list[Dataset]):
        resp = app.get(reverse("dataset-list"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [status_filter_data[0].pk, status_filter_data[1].pk]
        )
        filters = {f.name: f for f in resp.context["filters"]}
        selected = [i.value for i in filters["status"].items() if i.selected]
        assert selected == []

    def test_status_filter_inventored(self, app: DjangoTestApp, status_filter_data: list[Dataset]):
        resp = app.get(f"{reverse('dataset-list')}?selected_facets=status_exact:{Dataset.INVENTORED}")

        objects = [int(obj.pk) for obj in resp.context["object_list"]]
        assert objects == [status_filter_data[1].pk]

        filters = {f.name: f for f in resp.context["filters"]}
        selected = [i.value for i in filters["status"].items() if i.selected]
        assert selected == [Dataset.INVENTORED]

    def test_organization_filter_without_query(self, app: DjangoTestApp, organization_filter_data: dict):
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

    def test_organization_filter_with_organization(self, app: DjangoTestApp, organization_filter_data: dict):
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

    def test_category_filter_without_query(self, app: DjangoTestApp, category_filter_data: dict[str, list[Category]]):
        resp = app.get(reverse("dataset-list"))
        assert len(resp.context["object_list"]) == 4

        filters = {f.name: f for f in resp.context["filters"]}
        selected = [i.value for i in filters["category"].items() if i.selected]
        assert selected == []

    def test_category_filter_with_parent_category(
        self, app: DjangoTestApp, category_filter_data: dict[str, list[Category]]
    ):
        resp = app.get(
            "%s?selected_facets=category_exact:%s" % (reverse("dataset-list"), category_filter_data["categories"][0].pk)
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

    def test_category_filter_with_middle_category(
        self,
        app: DjangoTestApp,
        category_filter_data: dict[str, list[Category]],
    ):
        resp = app.get(
            "%s?selected_facets=category_exact:%s" % (reverse("dataset-list"), category_filter_data["categories"][1].pk)
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

    def test_category_filter_with_child_category(
        self,
        app: DjangoTestApp,
        category_filter_data: dict[str, list[Category]],
    ):
        resp = app.get(
            "%s?selected_facets=category_exact:%s" % (reverse("dataset-list"), category_filter_data["categories"][3].pk)
        )
        assert [int(obj.pk) for obj in resp.context["object_list"]] == [
            category_filter_data["datasets"][3].pk,
        ]

        filters = {f.name: f for f in resp.context["filters"]}
        selected = [i.value for i in filters["category"].items() if i.selected]
        assert selected == [str(category_filter_data["categories"][3].pk)]

    def test_category_filter_with_parent_and_child_category(
        self,
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
    def test_data_group_filter_header_visible_if_data_groups_exist(
        self,
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
    def test_data_group_filter_header_not_visible_if_data_groups_do_not_exist(
        self,
        app: DjangoTestApp,
    ):
        DatasetFactory()
        resp = app.get(reverse("dataset-list"))
        assert not resp.html.find(id="data_group_filter_header")

    def test_tag_filter_without_query(self, app: DjangoTestApp, datasets: list[Dataset]):
        resp = app.get(reverse("dataset-list"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [
                datasets[0].pk,
                datasets[1].pk,
            ]
        )
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted([datasets[0].pk, datasets[1].pk])

        filters = {f.name: f for f in resp.context["filters"]}
        selected = [i.value for i in filters["tags"].items() if i.selected]
        assert selected == []

    def test_tag_filter_with_one_tag(self, app: DjangoTestApp, datasets: list[Dataset]):
        tag_id = datasets[0].tags.get(name="tag2").pk
        resp = app.get("%s?selected_facets=tags_exact:%s" % (reverse("dataset-list"), tag_id))
        assert [int(obj.pk) for obj in resp.context["object_list"]] == [datasets[0].pk]

        filters = {f.name: f for f in resp.context["filters"]}
        selected = [i.value for i in filters["tags"].items() if i.selected]
        assert selected == [str(tag_id)]

    def test_tag_filter_with_shared_tag(self, app: DjangoTestApp, datasets: list[Dataset]):
        tag_id = datasets[0].tags.get(name="tag3").pk
        resp = app.get("%s?selected_facets=tags_exact:%s" % (reverse("dataset-list"), tag_id))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted([datasets[0].pk, datasets[1].pk])

        filters = {f.name: f for f in resp.context["filters"]}
        selected = [i.value for i in filters["tags"].items() if i.selected]
        assert selected == [str(tag_id)]

    def test_tag_filter_with_multiple_tags(self, app: DjangoTestApp, datasets: list[Dataset]):
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

    def test_frequency_filter_without_query(self, app: DjangoTestApp, frequency_filter_data: dict):
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

    def test_frequency_filter_with_frequency(self, app: DjangoTestApp, frequency_filter_data: dict):
        resp = app.get(
            "%s?selected_facets=frequency_exact:%s" % (reverse("dataset-list"), frequency_filter_data["frequency"].pk)
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

    def test_date_filter_without_query(self, app: DjangoTestApp, date_filter_data: list[Dataset]):
        resp = app.get(reverse("dataset-list"))
        assert [int(obj.pk) for obj in resp.context["object_list"]] == [
            date_filter_data[0].pk,
            date_filter_data[1].pk,
            date_filter_data[2].pk,
        ]
        assert resp.context["form"].cleaned_data["date_from"] is None
        assert resp.context["form"].cleaned_data["date_to"] is None

    def test_date_filter_wit_date_from(self, app: DjangoTestApp, date_filter_data: list[Dataset]):
        resp = app.get("%s?date_from=2022-02-10" % reverse("dataset-list"))
        assert [int(obj.pk) for obj in resp.context["object_list"]] == [date_filter_data[0].pk]
        assert resp.context["form"].cleaned_data["date_from"] == date(2022, 2, 10)
        assert resp.context["form"].cleaned_data["date_to"] is None

    def test_date_filter_with_date_to(self, app: DjangoTestApp, date_filter_data: list[Dataset]):
        resp = app.get("%s?date_to=2022-02-10" % reverse("dataset-list"))
        assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted(
            [date_filter_data[1].pk, date_filter_data[2].pk]
        )
        assert resp.context["form"].cleaned_data["date_from"] is None
        assert resp.context["form"].cleaned_data["date_to"] == date(2022, 2, 10)

    def test_date_filter_with_dates_from_and_to(self, app: DjangoTestApp, date_filter_data: list[Dataset]):
        resp = app.get("%s?date_from=2022-01-01&date_to=2022-02-10" % reverse("dataset-list"))
        assert [int(obj.pk) for obj in resp.context["object_list"]] == [date_filter_data[1].pk]
        assert resp.context["form"].cleaned_data["date_from"] == date(2022, 1, 1)
        assert resp.context["form"].cleaned_data["date_to"] == date(2022, 2, 10)

    def test_dataset_filter_all(self, app: DjangoTestApp):
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

    def test_dataset_filter_with_pages(self, app: DjangoTestApp):
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

    def test_dataset_stats_view_no_login_with_query(
        self,
        app: DjangoTestApp,
        category_filter_data: dict[str, list[Category]],
    ):
        resp = app.get(
            "%s?selected_facets=category_exact:%s" % (reverse("dataset-list"), category_filter_data["categories"][1].pk)
        )

        assert resp.status_code == 200

    def test_search_with_partial_word_query(self, app: DjangoTestApp, search_datasets: list[Dataset]):
        resp = app.get("%s?q=%s" % (reverse("dataset-list"), "vien"))
        assert [int(obj.pk) for obj in resp.context["object_list"]] == [search_datasets[0].pk]

    def test_access_rights_filter(self, app: DjangoTestApp):
        dataset1 = DatasetFactory(access_rights=Dataset.RESTRICTED)
        dataset2 = DatasetFactory(access_rights=Dataset.RESTRICTED)
        DatasetFactory(access_rights=Dataset.PUBLIC)
        resp = app.get("%s?selected_facets=access_rights_exact:%s" % (reverse("dataset-list"), Dataset.RESTRICTED))

        objects = sorted([int(obj.pk) for obj in resp.context["object_list"]])
        assert objects == sorted([dataset1.pk, dataset2.pk])

        filters = {f.name: f for f in resp.context["filters"]}
        selected = [i.value for i in filters["access_rights"].items() if i.selected]
        assert selected == [Dataset.RESTRICTED]

    def test_dataset_filter_by_publisher(self, app: DjangoTestApp):
        publisher1 = OrganizationFactory(publisher=True)
        publisher2 = OrganizationFactory(publisher=True)
        DatasetFactory(publisher=publisher1)
        DatasetFactory(publisher=publisher1)
        DatasetFactory(publisher=publisher2)

        user = UserFactory(is_staff=True)
        app.set_user(user)

        response = app.get(reverse("dataset-list") + f"?selected_facets=publisher_exact:{publisher1.pk}")
        assert response.status_code == 200
        assert len(response.context["object_list"]) == 2
        for ds in response.context["object_list"]:
            assert ds.publisher == [publisher1.pk]

        response = app.get(reverse("dataset-list") + f"?selected_facets=publisher_exact:{publisher2.pk}")
        assert response.status_code == 200
        assert len(response.context["object_list"]) == 1
        for ds in response.context["object_list"]:
            assert ds.publisher == [publisher2.pk]


class TestDatasetUpdateView:
    def test_change_form_no_login(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        response = app.get(reverse("dataset-change", kwargs={"pk": dataset.id}))
        assert response.status_code == 302
        assert settings.LOGIN_URL in response.location

    def test_change_form_wrong_login(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        user = User.objects.create_user(email="test@test.com", password="test123")
        app.set_user(user)
        response = app.get(reverse("dataset-change", kwargs={"pk": dataset.id}), expect_errors=True)
        assert response.status_code == 403

    def test_change_form_correct_login(self, app: DjangoTestApp):
        parent_dataset = DatasetFactory()
        frequency = FrequencyFactory(is_default=True)
        category = CategoryFactory()
        org = OrganizationFactory()
        dataset: Dataset = DatasetFactory(
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
        url = reverse("dataset-change", kwargs={"pk": dataset.id})
        revision_comment = RevisionComment(
            source=RevisionSource.VIEW,
            action="dataset-change",
            http_method="POST",
            path=url,
            args=(),
            kwargs={"pk": dataset.id},
        )
        form = app.get(url).forms["dataset-form"]
        form["title"] = "Edited title"
        form["description"] = "edited dataset description"
        form["parent"] = parent_dataset.pk
        resp = form.submit()
        dataset.refresh_from_db()
        assert resp.status_code == 302
        assert resp.url == reverse("dataset-detail", kwargs={"pk": dataset.id})
        assert dataset.title == "Edited title"
        assert dataset.description == "edited dataset description"
        assert Version.objects.get_for_object(dataset).count() == 1
        assert Version.objects.get_for_object(dataset).first().revision.comment == revision_comment.to_json()
        assert dataset.metadata.count() == 1
        assert dataset.metadata.first().title == "Edited title"
        assert dataset.metadata.first().description == "edited dataset description"
        assert dataset.get_parent() == parent_dataset

    def test_change_parent(self, app: DjangoTestApp):
        old_parent_dataset = DatasetFactory()
        new_parent_dataset = DatasetFactory()
        dataset: Dataset = DatasetFactory(
            published=timezone.localize(datetime(2022, 9, 7)),
            slug="test-dataset-slug",
            description="test description",
        )
        dataset.move(old_parent_dataset)
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset.manager = user
        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]

        form["parent"] = new_parent_dataset.pk
        resp = form.submit()
        dataset.refresh_from_db()
        assert resp.status_code == 302
        assert resp.url == reverse("dataset-detail", kwargs={"pk": dataset.id})
        assert dataset.get_parent() == new_parent_dataset

    def test_remove_parent(self, app: DjangoTestApp):
        old_parent_dataset = DatasetFactory()
        dataset: Dataset = DatasetFactory(
            published=timezone.localize(datetime(2022, 9, 7)),
            slug="test-dataset-slug",
            description="test description",
        )
        dataset.move(old_parent_dataset)
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset.manager = user
        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]

        form["parent"] = ""
        resp = form.submit()
        dataset.refresh_from_db()
        assert resp.status_code == 302
        assert resp.url == reverse("dataset-detail", kwargs={"pk": dataset.id})
        assert dataset.get_parent() is None

    def test_dataset_update_existing_identifier(self, app: DjangoTestApp):
        subclass = DCATResourceSubclassFactory(name="information_system")
        organization = OrganizationFactory()
        information_system_type_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
        )
        information_system_type_concept = ConceptFactory(concept_schemas=[information_system_type_concept_schema])
        information_system_importance_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI
        )
        information_system_importance_concept = ConceptFactory(
            concept_schemas=[information_system_importance_concept_schema]
        )
        dataset = DatasetFactory(
            subclass=subclass,
            information_system_type=information_system_type_concept,
            information_system_importance=information_system_importance_concept,
            information_system_creator=organization,
            information_system_publisher=organization,
        )
        agency = Agency.objects.filter(name="Registrų ir valstybės informacinių sistemų registras").first()
        IdentifierFactory(resource=dataset, notation="1234", scheme_agency=agency)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]
        assert form["identifier"].value == "1234"
        form["identifier"] = "4321"
        form.submit()
        dataset.refresh_from_db()
        assert dataset.identifier == "4321"

        identifiers = Identifier.objects.filter(resource=dataset)
        assert identifiers.count() == 1
        assert identifiers.first().notation == "4321"

    def test_dataset_update_non_existing_identifier_validation(self, app: DjangoTestApp):
        subclass = DCATResourceSubclassFactory(name="information_system")
        dataset = DatasetFactory(subclass=subclass)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]
        form["identifier"] = "not-valid-identifier"
        form.submit()
        response = form.submit(expect_errors=True)
        assert "Žymėjimas turi atitikti šabloną" in response.text

    def test_dataset_update_non_existing_identifier(self, app: DjangoTestApp):
        subclass = DCATResourceSubclassFactory(name="information_system")
        organization = OrganizationFactory()
        information_system_type_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
        )
        information_system_type_concept = ConceptFactory(concept_schemas=[information_system_type_concept_schema])
        information_system_importance_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI
        )
        information_system_importance_concept = ConceptFactory(
            concept_schemas=[information_system_importance_concept_schema]
        )
        dataset = DatasetFactory(
            subclass=subclass,
            information_system_type=information_system_type_concept,
            information_system_importance=information_system_importance_concept,
            information_system_creator=organization,
            information_system_publisher=organization,
        )
        user = UserFactory(is_staff=True)
        app.set_user(user)

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]
        form["identifier"] = "1234"
        form.submit()
        dataset.refresh_from_db()
        assert dataset.identifier == "1234"

        identifiers = Identifier.objects.filter(resource=dataset)
        assert identifiers.count() == 1
        assert identifiers.first().notation == "1234"

    def test_dataset_update_from_public_to_non_public(self, app: DjangoTestApp):
        LicenceFactory(is_default=True)
        FrequencyFactory(is_default=True)
        dataset = DatasetFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)

        assert dataset.is_public is True
        assert dataset.published is not None

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]
        form["is_public"] = False
        form.submit()
        dataset.refresh_from_db()

        assert dataset.is_public is False
        assert dataset.published is None

    def test_dataset_update_from_non_public_to_public(self, app: DjangoTestApp):
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

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]
        form["is_public"] = True
        form.submit()
        dataset.refresh_from_db()

        assert dataset.is_public is True
        assert dataset.published is not None

    def test_dataset_update_without_permission(self, app: DjangoTestApp):
        dataset1 = DatasetFactory()
        dataset2 = DatasetFactory()
        user = UserFactory()
        RepresentativeFactory(
            user=user,
            content_type=ContentType.objects.get_for_model(dataset1),
            object_id=dataset1.pk,
        )
        app.set_user(user)

        resp = app.get(reverse("dataset-change", kwargs={"pk": dataset2.id}), expect_errors=True)
        assert resp.status_code == 403

    @pytest.mark.parametrize(
        "subclass_name, form_class",
        [
            ("dataset", DatasetResourceForm),
            ("catalog", CatalogResourceForm),
            ("information_system", InformationSystemResourceForm),
            ("service", ServiceResourceForm),
            ("series", ResourceForm),
            ("foo", ResourceForm),
        ],
    )
    def test_dataset_update_uses_different_forms_based_on_dcat_subclass(
        self, app: DjangoTestApp, subclass_name: str, form_class: BaseResourceForm
    ) -> None:
        subclass = DCATResourceSubclassFactory(name=subclass_name)
        dataset = DatasetFactory(subclass=subclass)
        user = UserFactory(is_staff=True)
        app.set_user(user)

        response = app.get(reverse("dataset-change", kwargs={"pk": dataset.id}))

        assert type(response.context.get("form")) is form_class

    def test_dataset_update_information_system(self, app: DjangoTestApp) -> None:
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name="information_system")
        dataset = DatasetFactory(subclass=subclass, organization=organization)
        organization_name = organization.name
        catalog = CatalogFactory()
        frequency = FrequencyFactory(is_default=True)
        information_system_type_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
        )
        information_system_type_concept = ConceptFactory(concept_schemas=[information_system_type_concept_schema])
        information_system_importance_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI
        )
        information_system_importance_concept = ConceptFactory(
            concept_schemas=[information_system_importance_concept_schema]
        )
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
            "name": f"{organization_name}information_system_two",
            "landing_page": "https://www.test.test",
            "information_system_type": information_system_type_concept.pk,
            "information_system_importance": information_system_importance_concept.pk,
            "information_system_publisher": organization.pk,
            "information_system_creator": organization.pk,
        }
        response = app.post(url, data)

        dataset = Dataset.objects.filter(pk=dataset.pk).first()
        assert dataset
        assert response.url == dataset.get_absolute_url()
        assert dataset.title == "test_information_system"
        assert dataset.description == "test_information_system_description"
        assert dataset.is_public is False
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"tag1", "tag2"}
        assert dataset.catalog == catalog
        assert dataset.frequency == frequency
        assert dataset.access_rights == Dataset.PUBLIC
        assert dataset.name == f"{organization_name}information_system_two"
        assert dataset.landing_page == "https://www.test.test"
        assert dataset.information_system_type == information_system_type_concept
        assert dataset.information_system_importance == information_system_importance_concept
        assert dataset.information_system_publisher == organization
        assert dataset.information_system_creator == organization

    def test_dataset_with_name_error(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()

        form = app.get(reverse("dataset-change", args=[dataset.pk])).forms["dataset-form"]
        form["name"] = "test/ąčę"
        resp = form.submit()
        assert list(resp.context["form"].errors.values()) == [
            ["Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."]
        ]

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_MANAGER,
            Representative.RESOURCE_MANAGER,
        ],
    )
    def test_edit_non_public_dataset_with_org_representative(self, app: DjangoTestApp, role: str):
        dataset = DatasetFactory(is_public=False)
        user = UserFactory()
        organization = OrganizationFactory()
        user.organization = organization
        user.save()

        RepresentativeFactory(
            organization=organization,
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
            role=role,
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

    def test_dataset_change_with_applicable_legislation(self, app: DjangoTestApp):
        category = CategoryFactory()
        dataset = DatasetFactory()
        dataset.category.add(category)
        dataset.applicable_legislation.set(ApplicableLegislationFactory.create_batch(4))

        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset.manager = user

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]

        new_urls = ("http://www.google.", "http://www.example.com")
        for i, field in enumerate(form.fields["applicable_legislation"]):
            field.value = new_urls[i] if i < len(new_urls) else ""

        with patch("vitrina.datasets.tasks.update_applicable_legislation_description.delay") as mocked_task:
            response = form.submit()

        dataset.refresh_from_db()
        assert mocked_task.call_count == 1
        assert response.status_code == 302
        assert set(dataset.applicable_legislation.values_list("url", flat=True)) == set(new_urls)

    def test_dataset_change_with_documentation(self, app: DjangoTestApp):
        category = CategoryFactory()
        dataset = DatasetFactory()
        dataset.category.add(category)
        dataset.documentation.set(DocumentationFactory.create_batch(4))

        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset.manager = user

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]

        new_urls = ("http://www.google.", "http://www.example.com")
        for i, field in enumerate(form.fields["documentation"]):
            field.value = new_urls[i] if i < len(new_urls) else ""
        response = form.submit()
        dataset.refresh_from_db()

        assert response.status_code == 302
        assert set(dataset.documentation.values_list("documentation_link", flat=True)) == set(new_urls)

    def test_dataset_update_contact(self, app: DjangoTestApp):
        org = OrganizationFactory()
        user = UserFactory(is_staff=True, organization=org)
        app.set_user(user)
        contact = ContactFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(org),
            object_id=org.pk,
        )
        ds = DatasetFactory(organization=org)
        form = app.get(reverse("dataset-change", args=[ds.pk])).forms["dataset-form"]
        form["contact"] = contact.pk
        form.submit()
        ds.refresh_from_db()
        assert ds.contact == contact

    def test_dataset_update_contact_options(self, app: DjangoTestApp):
        org = OrganizationFactory()
        org2 = OrganizationFactory()
        publisher_org = OrganizationFactory(publisher=True)

        user = UserFactory(is_staff=True, organization=org)
        user2 = UserFactory(is_staff=True, organization=org)
        user3 = UserFactory(is_staff=True)
        publisher_user = UserFactory(is_staff=True, organization=publisher_org)
        app.set_user(user)

        ds = DatasetFactory(organization=org, publisher=publisher_org)
        ContactFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(org),
            object_id=org.pk,
        )
        ContactFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(publisher_org),
            object_id=publisher_org.pk,
        )
        ContactFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(user),
            object_id=user.pk,
        )
        ContactFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(user2),
            object_id=user2.pk,
        )
        ContactFactory(
            organization=org,
            content_type=ContentType.objects.get_for_model(publisher_user),
            object_id=publisher_user.pk,
        )
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
        incorrect_options = sorted(["---------", org2.title, f"{user3.first_name} {user3.last_name}"])
        assert form_options == correct_options
        assert form_options != incorrect_options

    def test_update_dateset_generates_name(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        org = OrganizationFactory()
        user = UserFactory(is_staff=True, organization=org)
        app.set_user(user)

        dataset = DatasetFactory(organization=org, title="Test Dataset", metadata="")

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]
        form["title"] = "Updated Test Dataset"
        form["description"] = "Updated dataset description"
        form["access_rights"] = Dataset.PUBLIC
        response = form.submit()

        assert response.status_code == 302
        dataset.refresh_from_db()
        assert dataset.name == f"{org.name}updated-test-dataset"

    def test_update_dateset_existing_name_cannot_be_removed(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        org = OrganizationFactory(name="Test Organization")
        user = UserFactory(is_staff=True, organization=org)
        app.set_user(user)

        dataset = DatasetFactory(organization=org, title="Test Dataset", metadata="test-organization/test-dataset")

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]
        form["title"] = "Updated Test Dataset"
        form["name"] = ""  # Attempt to remove name
        form["description"] = "Updated dataset description"
        form["access_rights"] = Dataset.PUBLIC

        response = form.submit()
        assert response.status_code == 200
        dataset.refresh_from_db()
        assert dataset.name == "test-organization/test-dataset"

    def test_dataset_landing_page(self, app: DjangoTestApp):
        frequency = FrequencyFactory(is_default=True)
        org = OrganizationFactory()
        dataset = DatasetFactory(frequency=frequency, organization=org)
        user = UserFactory(is_staff=True)
        app.set_user(user)
        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]
        form["landing_page"] = "https://example.com"
        resp = form.submit()
        dataset.refresh_from_db()
        assert resp.status_code == 302
        assert resp.url == reverse("dataset-detail", kwargs={"pk": dataset.id})
        assert dataset.landing_page == "https://example.com"

    def test_dataset_update_files(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        assert not dataset.dataset_files.all().exists()

        form = app.get(reverse("dataset-change", kwargs={"pk": dataset.id})).forms["dataset-form"]
        form["files"] = [Upload("foo.txt", content=b"foo")]
        form.submit()

        dataset.refresh_from_db()
        assert dataset.dataset_files.all().exists()
        assert form.enctype == "multipart/form-data"


class TestDatasetCreateView:
    def test_add_form_no_login(self, app: DjangoTestApp):
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory()
        response = app.get(reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk}))
        assert response.status_code == 302
        assert settings.LOGIN_URL in response.location

    def test_add_form_wrong_login(self, app: DjangoTestApp):
        user = User.objects.create_user(email="test@test.com", password="test123")
        app.set_user(user)
        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory()
        response = app.get(
            reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk}),
            expect_errors=True,
        )
        assert response.status_code == 403

    def test_add_form_correct_login(self, app: DjangoTestApp):
        parent_dataset = DatasetFactory()
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
        url = reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})
        revision_comment = RevisionComment(
            source=RevisionSource.VIEW,
            action="dataset-add",
            http_method="POST",
            path=url,
            args=(),
            kwargs={"pk": org.id, "subclass_uuid": subclass.pk},
        )
        form = app.get(url).forms["dataset-form"]
        form["title"] = "Added title"
        form["description"] = "Added new dataset description"
        form["tags"] = ["test tag"]
        form["access_rights"] = Dataset.PUBLIC
        form["parent"] = parent_dataset.id
        resp = form.submit()
        added_datasets = Dataset.objects.filter(translations__title="Added title")
        assert added_datasets.count() == 2
        added_dataset = added_datasets.first()
        assert added_dataset.tags.all()[0].name == "test tag"
        assert added_dataset.access_rights == Dataset.PUBLIC
        assert resp.status_code == 302
        assert str(added_dataset.id) in resp.url
        added_dataset = added_datasets.first()
        assert Version.objects.get_for_object(added_dataset).count() == 1
        assert Version.objects.get_for_object(added_dataset).first().revision.comment == revision_comment.to_json()
        assert added_dataset.metadata.count() == 1
        assert added_dataset.metadata.first().title == "Added title"
        assert added_dataset.metadata.first().description == "Added new dataset description"
        assert added_dataset.get_parent() == parent_dataset
        assert added_dataset.uuid is not None

    def test_dataset_add_form_initial_values(self, app: DjangoTestApp):
        default_frequency = FrequencyFactory(is_default=True)
        subclass = DCATResourceSubclassFactory()
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        form = app.get(reverse("dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        assert form["frequency"].value == str(default_frequency.pk)

    @pytest.mark.parametrize(
        "subclass_name, form_class",
        [
            ("dataset", DatasetResourceForm),
            ("catalog", CatalogResourceForm),
            ("information_system", InformationSystemResourceForm),
            ("service", ServiceResourceForm),
            ("series", ResourceForm),
            ("foo", ResourceForm),
        ],
    )
    def test_dataset_create_uses_different_forms_based_on_dcat_subclass(
        self, app: DjangoTestApp, subclass_name: str, form_class: BaseResourceForm
    ) -> None:
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name=subclass_name)
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(reverse("dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk}))

        assert type(response.context.get("form")) is form_class

    def test_dataset_create_information_system(self, app: DjangoTestApp):
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name="information_system")
        catalog = CatalogFactory()
        frequency = FrequencyFactory(is_default=True)
        information_system_type_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
        )
        information_system_type_concept = ConceptFactory(concept_schemas=[information_system_type_concept_schema])
        information_system_importance_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI
        )
        information_system_importance_concept = ConceptFactory(
            concept_schemas=[information_system_importance_concept_schema]
        )
        user = UserFactory(is_staff=True)
        app.set_user(user)

        url = reverse("dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk})

        data = {
            "title": "test_information_system",
            "description": "test_information_system_description",
            "is_public": False,
            "tags": "tag1, tag2",
            "catalog": catalog.pk,
            "frequency": frequency.pk,
            "access_rights": Dataset.PUBLIC,
            "name": f"{organization.name}test_information_system",
            "landing_page": "https://www.test.test",
            "information_system_type": information_system_type_concept.pk,
            "information_system_importance": information_system_importance_concept.pk,
            "information_system_publisher": organization.pk,
            "information_system_creator": organization.pk,
        }
        response = app.post(url, data)

        dataset = Dataset.objects.filter(pk=response.context["object"].pk).first()
        assert dataset
        assert response.url == dataset.get_absolute_url()
        assert dataset.title == "test_information_system"
        assert dataset.description == "test_information_system_description"
        assert dataset.is_public is False
        assert set(dataset.tags.all().values_list("name", flat=True)) == {"tag1", "tag2"}
        assert dataset.catalog == catalog
        assert dataset.frequency == frequency
        assert dataset.access_rights == Dataset.PUBLIC
        assert dataset.name == f"{organization.name}test_information_system"
        assert dataset.landing_page == "https://www.test.test"
        assert dataset.information_system_type == information_system_type_concept
        assert dataset.information_system_importance == information_system_importance_concept
        assert dataset.information_system_publisher == organization
        assert dataset.information_system_creator == organization

    def test_dataset_with_subclass(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        form = app.get(reverse("dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        form["title"] = "Test dataset"
        form["description"] = "Test dataset description"
        form["is_public"] = True
        form["access_rights"] = Dataset.PUBLIC
        form.submit()
        added_dataset = Dataset.objects.filter(translations__title="Test dataset")
        assert added_dataset.count() == 2
        assert added_dataset.first().is_public is True
        assert added_dataset.first().subclass == subclass

    def test_dataset_create_non_public(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        form = app.get(reverse("dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
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

    def test_dataset_create_public(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        form = app.get(reverse("dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
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

    def test_child_dataset_create_public(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory()
        parent_dataset = DatasetFactory()
        user = UserFactory(is_staff=True)
        app.set_user(user)
        form = app.get(
            reverse(
                "child-dataset-add",
                kwargs={"pk": organization.id, "parent_id": parent_dataset.pk, "subclass_uuid": subclass.pk},
            )
        ).forms["dataset-form"]
        form["title"] = "Test dataset"
        form["description"] = "Test dataset description"
        form["is_public"] = True
        form["access_rights"] = Dataset.PUBLIC
        form.submit()
        added_dataset: Dataset = Dataset.objects.filter(translations__title="Test dataset").first()
        assert added_dataset.is_public is True
        assert added_dataset.published is not None
        assert added_dataset.access_rights == Dataset.PUBLIC
        assert added_dataset.get_parent() == parent_dataset

    def test_information_system_create_with_identifier(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name="information_system")
        information_system_type_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
        )
        information_system_type_concept = ConceptFactory(concept_schemas=[information_system_type_concept_schema])
        information_system_importance_concept_schema = ConceptSchema.objects.get(
            uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI
        )
        information_system_importance_concept = ConceptFactory(
            concept_schemas=[information_system_importance_concept_schema]
        )
        user = UserFactory(is_staff=True)
        app.set_user(user)
        form = app.get(reverse("dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        form["title"] = "Test dataset"
        form["description"] = "Test dataset description"
        form["is_public"] = True
        form["access_rights"] = Dataset.PUBLIC
        form["identifier"] = "1234"
        form["information_system_type"] = information_system_type_concept.pk
        form["information_system_importance"] = information_system_importance_concept.pk
        form["information_system_creator"] = organization.pk
        form["information_system_publisher"] = organization.pk
        form.submit()
        added_dataset = Dataset.objects.filter(translations__title="Test dataset")
        assert added_dataset.first().is_public is True
        assert added_dataset.first().published is not None
        assert added_dataset.first().access_rights == Dataset.PUBLIC
        assert added_dataset.first().identifier == "1234"

        assert Identifier.objects.filter(notation="1234", resource=added_dataset.first()).exists()

    def test_information_system_create_with_identifier_validation(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        organization = OrganizationFactory()
        subclass = DCATResourceSubclassFactory(name="information_system")
        user = UserFactory(is_staff=True)
        app.set_user(user)
        form = app.get(reverse("dataset-add", kwargs={"pk": organization.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        form["title"] = "Test dataset"
        form["description"] = "Test dataset description"
        form["is_public"] = True
        form["access_rights"] = Dataset.PUBLIC
        form["identifier"] = "not-valid-identifier"
        form.submit()
        response = form.submit(expect_errors=True)
        assert "Žymėjimas turi atitikti šabloną" in response.text

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_MANAGER,
            Representative.RESOURCE_MANAGER,
        ],
    )
    def test_create_dataset_change_creator(self, app: DjangoTestApp, role: str):
        frequency = FrequencyFactory(is_default=True)

        org = OrganizationFactory()
        publisher_org = OrganizationFactory(publisher=True)

        RepresentativeFactory(
            user=None,
            organization=publisher_org,
            role=role,
            object_id=org.pk,
            content_type=ContentType.objects.get_for_model(org),
        )

        subclass = DCATResourceSubclassFactory()
        user = UserFactory(is_staff=True, organization=publisher_org)
        app.set_user(user)

        form = app.get(reverse("dataset-add", kwargs={"pk": publisher_org.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]

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

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_MANAGER,
            Representative.RESOURCE_MANAGER,
        ],
    )
    def test_create_dataset_change_publisher(self, app: DjangoTestApp, role: str):
        frequency = FrequencyFactory(is_default=True)

        org = OrganizationFactory()
        publisher_org = OrganizationFactory(publisher=True)
        subclass = DCATResourceSubclassFactory()
        RepresentativeFactory(
            user=None,
            organization=publisher_org,
            role=role,
            object_id=org.pk,
            content_type=ContentType.objects.get_for_model(org),
        )

        user = UserFactory(is_staff=True, organization=org)
        app.set_user(user)

        form = app.get(reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]

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

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_MANAGER,
            Representative.RESOURCE_MANAGER,
        ],
    )
    def test_create_dataset_creator_options(self, app: DjangoTestApp, role: str):
        org = OrganizationFactory()
        org2 = OrganizationFactory()
        org3 = OrganizationFactory()
        publisher_org = OrganizationFactory(publisher=True)
        subclass = DCATResourceSubclassFactory()
        for org_instance in [org, org2, org3]:
            RepresentativeFactory(
                user=None,
                organization=publisher_org,
                role=role,
                object_id=org_instance.pk,
                content_type=ContentType.objects.get_for_model(org),
            )

        user = UserFactory(is_staff=False, organization=publisher_org)
        app.set_user(user)
        form = app.get(reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        options = [option[2] for option in form.fields["creator"][0].options]
        assert len(options) == 5  # includes default option
        assert org.title in options
        assert org2.title in options
        assert org3.title in options
        assert publisher_org.title in options

    def test_create_dataset_publisher_options(self, app: DjangoTestApp):
        org = OrganizationFactory()
        publisher_org = OrganizationFactory(publisher=True)
        publisher_org2 = OrganizationFactory(publisher=True)
        publisher_org3 = OrganizationFactory(publisher=True)
        subclass = DCATResourceSubclassFactory()
        user = UserFactory(is_staff=True, organization=org)
        app.set_user(user)
        form = app.get(reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        options = [option[2] for option in form.fields["publisher"][0].options]
        assert len(options) == 4  # includes default option
        assert publisher_org.title in options
        assert publisher_org2.title in options
        assert publisher_org3.title in options

    def test_dataset_create_with_applicable_legislation(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        subclass = DCATResourceSubclassFactory()
        org = OrganizationFactory(
            title="Org_title",
            created=timezone.localize(datetime(2022, 8, 22, 10, 30)),
            jurisdiction=AreaOfManagement.objects.get(id=1),
            slug="test-org-slug",
            kind="test_org_kind",
        )
        applicable_legislation_urls = ["http://www.google.com", "http://www.example.com"]
        user = UserFactory(is_staff=True)
        app.set_user(user)

        form = app.get(reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        form["title"] = "Added title"
        form["description"] = "Added new dataset description"
        form["access_rights"] = Dataset.PUBLIC
        form["applicable_legislation"] = applicable_legislation_urls

        with patch("vitrina.datasets.tasks.update_applicable_legislation_description.delay") as mocked_task:
            response = form.submit()

        dataset = Dataset.objects.filter(translations__title="Added title").first()
        assert mocked_task.call_count == 1
        assert response.status_code == 302
        assert set(dataset.applicable_legislation.values_list("url", flat=True)) == set(applicable_legislation_urls)

    def test_dataset_create_with_documentation(self, app: DjangoTestApp):
        FrequencyFactory(is_default=True)
        subclass = DCATResourceSubclassFactory()
        org = OrganizationFactory(
            title="Org_title",
            created=timezone.localize(datetime(2022, 8, 22, 10, 30)),
            jurisdiction=AreaOfManagement.objects.get(id=1),
            slug="test-org-slug",
            kind="test_org_kind",
        )
        documentation_urls = ["http://www.google.com", "http://www.example.com"]
        user = UserFactory(is_staff=True)
        app.set_user(user)

        form = app.get(reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        form["title"] = "Added title"
        form["description"] = "Added new dataset description"
        form["access_rights"] = Dataset.PUBLIC
        form["documentation"] = documentation_urls
        response = form.submit()

        dataset = Dataset.objects.filter(translations__title="Added title").first()
        assert response.status_code == 302
        assert set(dataset.documentation.values_list("documentation_link", flat=True)) == set(documentation_urls)

    @pytest.mark.parametrize(
        "dataset_name, dataset_title, organization_name, organization_slug, organization_title, expected_dataset_name",
        [
            (
                None,
                "Test Dataset",
                "datasets/gov/test-organization/",
                "",
                "",
                "datasets/gov/test-organization/test-dataset",
            ),  # generates automatically
            (
                "datasets/gov/test-organization/test-organization/my-test-dataset",
                "Test Dataset",
                "datasets/gov/test-organization/",
                "",
                "",
                "datasets/gov/test-organization/test-organization/my-test-dataset",
            ),  # uses provided name
            (
                None,
                "Test Dataset",
                "",
                "test-organization-slug",
                "",
                "datasets/org/test-organization-slug/test-dataset",
            ),  # generates automatically
            (
                None,
                "Test Dataset",
                "",
                "",
                "Test Organization Title",
                "datasets/org/test-organization-title/test-dataset",
            ),  # generates automatically
        ],
    )
    def test_create_dataset_without_name_generates_automatically(
        self,
        app: DjangoTestApp,
        dataset_name,
        dataset_title,
        organization_name,
        organization_slug,
        organization_title,
        expected_dataset_name,
    ):
        FrequencyFactory(is_default=True)
        subclass = DCATResourceSubclassFactory()
        org = OrganizationFactory(name=organization_name, slug=organization_slug, title=organization_title)
        user = UserFactory(is_staff=True, organization=org)
        app.set_user(user)
        form = app.get(reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        form["title"] = dataset_title
        if dataset_name is not None:
            form["name"] = dataset_name
        form["description"] = "Added new dataset description"
        form["access_rights"] = Dataset.PUBLIC
        response = form.submit()
        assert response.status_code == 302
        assert Dataset.objects.exclude(id=1).count() == 1
        dataset = Dataset.objects.exclude(id=1).first()
        assert dataset.name == expected_dataset_name

    def test_create_dataset_without_name_generate_unique_name(self, app: DjangoTestApp):
        subclass = DCATResourceSubclassFactory()
        FrequencyFactory(is_default=True)
        org = OrganizationFactory()
        user = UserFactory(is_staff=True, organization=org)
        app.set_user(user)
        dataset1 = DatasetFactory(organization=org, title="Test Dataset", metadata=f"{org.name}test-dataset")
        VersionFactory(dataset=dataset1)
        dataset2 = DatasetFactory(organization=org, title="Second Test Dataset", metadata=f"{org.name}test-dataset_3")
        VersionFactory(dataset=dataset2)

        form = app.get(reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]
        form["title"] = "Test Dataset"
        form["description"] = "Added new dataset description"
        form["access_rights"] = Dataset.PUBLIC
        response = form.submit()
        assert response.status_code == 302
        assert Dataset.objects.exclude(id=1).count() == 3

        dataset1.refresh_from_db()
        assert dataset1.name == f"{org.name}test-dataset"

        dataset2.refresh_from_db()
        assert dataset2.name == f"{org.name}test-dataset_3"

        dataset3 = Dataset.objects.exclude(id=1).last()
        assert dataset3.name == f"{org.name}test-dataset_4"

    def test_dataset_create_files(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        subclass = DCATResourceSubclassFactory()
        FrequencyFactory(is_default=True)
        organization = OrganizationFactory()

        form = app.get(reverse("dataset-add", args=[organization.pk, subclass.pk])).forms["dataset-form"]
        form["title"] = "Test Dataset"
        form["description"] = "Added new dataset description"
        form["access_rights"] = Dataset.PUBLIC
        form["files"] = [Upload("foo.txt", content=b"foo")]
        form.submit()

        dataset = Dataset.objects.get(organization=organization)
        assert dataset.dataset_files.all().exists()
        assert form.enctype == "multipart/form-data"

    @pytest.mark.django_db
    def test_dataset_create_creates_representative_with_org_role(self, app: DjangoTestApp):
        frequency = FrequencyFactory(is_default=True)

        org = OrganizationFactory()
        subclass = DCATResourceSubclassFactory()

        user = UserFactory(is_staff=True)
        app.set_user(user)

        RepresentativeFactory(
            user=user,
            organization=org,
            role=Representative.OPEN_DATA_COORDINATOR,
            content_type=ContentType.objects.get_for_model(org),
            object_id=org.pk,
        )

        form = app.get(reverse("dataset-add", kwargs={"pk": org.id, "subclass_uuid": subclass.pk})).forms[
            "dataset-form"
        ]

        form["title"] = "Dataset without creator"
        form["description"] = "Test dataset"
        form["frequency"] = str(frequency.pk)
        form["access_rights"] = Dataset.PUBLIC

        response = form.submit()

        assert response.status_code == 302

        dataset = Dataset.objects.get(translations__title="Dataset without creator")

        rep = Representative.objects.filter(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
        ).first()

        assert rep is not None
        assert rep.role == Representative.OPEN_DATA_COORDINATOR


class TestDatasetDeleteView:
    def test_delete_dataset(self, app: DjangoTestApp) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)

        dataset = DatasetFactory()

        app.post(reverse("dataset-delete", args=[dataset.pk]))
        assert not Dataset.objects.filter(pk=dataset.pk).exists()


class TestDatasetMembers:
    def test_dataset_members_view_public_by_anyone_authenticated(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(dataset)
        representative = RepresentativeFactory(
            content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER
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
        assert response.status_code == 200

    def test_dataset_members_cant_view_public_by_anyone_authenticated(self, app: DjangoTestApp):
        dataset = DatasetFactory(is_public=False, access_rights=Dataset.CONFIDENTIAL)
        ct = ContentType.objects.get_for_model(dataset)
        representative = RepresentativeFactory(
            content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER
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

    def test_dataset_members_view_no_login(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(dataset)
        RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER)
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(reverse("dataset-members", kwargs={"pk": dataset.pk}))
        assert response.status_code == 200

    @pytest.mark.django_db(transaction=True)
    def test_dataset_members_create_member(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)
        coordinator_user = UserFactory()
        RepresentativeFactory(
            content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_COORDINATOR, user=coordinator_user
        )
        app.set_user(coordinator_user)
        url = reverse("dataset-members", kwargs={"pk": dataset.pk})

        resp = app.get(url)
        resp = resp.click(linkid="add-member-btn")

        form = resp.forms["representative-form"]
        form["email"] = "test@example.com"
        form["role"] = Representative.OPEN_DATA_MANAGER
        resp = form.submit()

        assert resp.headers["location"] == url

        rep = Representative.objects.get(
            content_type=ct,
            object_id=dataset.id,
            email="test@example.com",
        )
        assert rep.role == Representative.OPEN_DATA_MANAGER
        assert rep.user is None
        assert rep.has_api_access is False
        assert rep.apikey_set.count() == 0

        assert len(mail.outbox) == 1
        assert "/register/" in mail.outbox[0].body

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_COORDINATOR,
            Representative.OPEN_DATA_MANAGER,
            Representative.RESOURCE_MANAGER,
        ],
    )
    def test_dataset_members_create_member_in_information_system_forbidden_for_roles(
        self,
        app: DjangoTestApp,
        role: str,
    ):
        subclass = DCATResourceSubclassFactory(name="information_system")
        dataset = DatasetFactory(subclass=subclass)
        ct = ContentType.objects.get_for_model(Dataset)

        user = UserFactory()
        RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=role,
            user=user,
        )

        app.set_user(user)

        add_member_url = reverse(
            "dataset-representative-create",
            kwargs={"pk": dataset.pk},
        )

        resp = app.get(add_member_url, expect_errors=True)

        assert resp.status_code == 403

        assert not Representative.objects.filter(
            content_type=ct,
            object_id=dataset.pk,
            email="test@example.com",
        ).exists()

        assert len(mail.outbox) == 0

    def test_dataset_members_add_member(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)
        url = reverse("dataset-members", kwargs={"pk": dataset.pk})
        user = UserFactory(email="test@example.com", organization=None)  # User has NO org
        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        app.set_user(coordinator.user)

        resp = app.get(url)
        resp = resp.click(linkid="add-member-btn")

        form = resp.forms["representative-form"]
        form["email"] = "test@example.com"
        form["role"] = Representative.OPEN_DATA_MANAGER
        resp = form.submit()

        assert resp.headers["location"] == url

        rep = Representative.objects.get(
            content_type=ct,
            object_id=dataset.id,
            email="test@example.com",
        )
        assert rep.user == user
        user.refresh_from_db()
        assert rep.user.organization is None, "User should not be auto-assigned to dataset org"
        assert rep.role == Representative.OPEN_DATA_MANAGER
        assert rep.has_api_access is False
        assert rep.apikey_set.count() == 0

        assert len(mail.outbox) == 1

    def test_member_subscription(self, app: DjangoTestApp):
        subscriptions_before = Subscription.objects.all()
        assert len(subscriptions_before) == 0

        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)
        url = reverse("dataset-members", kwargs={"pk": dataset.pk})
        user = UserFactory(email="test@example.com", organization=None)  # User has NO org
        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        app.set_user(coordinator.user)

        resp = app.get(url)
        resp = resp.click(linkid="add-member-btn")

        form = resp.forms["representative-form"]
        form["email"] = "test@example.com"
        form["role"] = Representative.OPEN_DATA_MANAGER
        form["subscribe"] = True
        resp = form.submit()

        assert resp.headers["location"] == url

        rep = Representative.objects.get(
            content_type=ct,
            object_id=dataset.id,
            email="test@example.com",
        )
        assert rep.user == user
        user.refresh_from_db()
        assert rep.user.organization is None, "User should not be auto-assigned to dataset org"
        assert rep.role == Representative.OPEN_DATA_MANAGER
        assert rep.has_api_access is False
        assert rep.apikey_set.count() == 0

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["test@example.com"]

        subscriptions = Subscription.objects.all()
        assert len(subscriptions) == 1
        assert subscriptions[0].sub_type == Subscription.DATASET

    def test_dataset_members_create_member_with_api_access(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)
        user = UserFactory(email="test@example.com")
        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        app.set_user(coordinator.user)
        resp = app.get(reverse("dataset-members", kwargs={"pk": dataset.pk}))
        resp = resp.click(linkid="add-member-btn")

        form = resp.forms["representative-form"]
        form["email"] = "test@example.com"
        form["role"] = Representative.OPEN_DATA_MANAGER
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
    @pytest.mark.parametrize(
        "coordinator_role,target_role,new_role,can_update",
        [
            (
                Representative.OPEN_DATA_COORDINATOR,
                Representative.OPEN_DATA_MANAGER,
                Representative.OPEN_DATA_MANAGER,
                True,
            ),
            (
                Representative.OPEN_DATA_COORDINATOR,
                Representative.RESOURCE_MANAGER,
                Representative.RESOURCE_MANAGER,
                False,
            ),
            (
                Representative.RESOURCE_COORDINATOR,
                Representative.OPEN_DATA_MANAGER,
                Representative.OPEN_DATA_MANAGER,
                True,
            ),
            (
                Representative.RESOURCE_COORDINATOR,
                Representative.RESOURCE_MANAGER,
                Representative.RESOURCE_MANAGER,
                True,
            ),
        ],
    )
    def test_dataset_members_update_member(
        self, app: DjangoTestApp, coordinator_role, target_role, new_role, can_update
    ):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)
        url = reverse("dataset-members", kwargs={"pk": dataset.pk})

        target_rep = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=target_role,
        )
        original_org = target_rep.user.organization

        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=coordinator_role,
        )

        app.set_user(coordinator.user)

        resp = app.get(url)

        update_links = [
            link for link in resp.html.find_all("a") if f"update-member-{target_rep.pk}" in link.get("id", "")
        ]

        if can_update:
            assert len(update_links) == 1
            resp = resp.click(linkid=f"update-member-{target_rep.pk}-btn")
            form = resp.forms["representative-form"]
            form["role"] = new_role
            form.submit()

            target_rep.refresh_from_db()
            assert target_rep.role == new_role
            assert target_rep.user.organization == original_org, (
                "User's organization should not change during role update"
            )
        else:
            assert len(update_links) == 0

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "coordinator_role,target_role,new_role,can_update",
        [
            (
                Representative.OPEN_DATA_COORDINATOR,
                Representative.OPEN_DATA_MANAGER,
                Representative.OPEN_DATA_MANAGER,
                False,
            ),
            (
                Representative.OPEN_DATA_COORDINATOR,
                Representative.RESOURCE_MANAGER,
                Representative.RESOURCE_MANAGER,
                False,
            ),
            (
                Representative.RESOURCE_COORDINATOR,
                Representative.OPEN_DATA_MANAGER,
                Representative.OPEN_DATA_MANAGER,
                True,
            ),
            (
                Representative.RESOURCE_COORDINATOR,
                Representative.RESOURCE_MANAGER,
                Representative.RESOURCE_MANAGER,
                True,
            ),
            (
                Representative.RESOURCE_MANAGER,
                Representative.RESOURCE_MANAGER,
                Representative.OPEN_DATA_MANAGER,
                False,
            ),
        ],
    )
    def test_dataset_members_update_member_subclass_information_system(
        self, app: DjangoTestApp, coordinator_role, target_role, new_role, can_update
    ):
        subclass = DCATResourceSubclassFactory(name="information_system")
        dataset = DatasetFactory(subclass=subclass)
        ct = ContentType.objects.get_for_model(Dataset)
        url = reverse("dataset-members", kwargs={"pk": dataset.pk})

        target_rep = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=target_role,
        )
        original_org = target_rep.user.organization

        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=coordinator_role,
        )

        app.set_user(coordinator.user)

        resp = app.get(url)

        update_links = [
            link for link in resp.html.find_all("a") if f"update-member-{target_rep.pk}" in link.get("id", "")
        ]

        if can_update:
            assert len(update_links) == 1
            resp = resp.click(linkid=f"update-member-{target_rep.pk}-btn")
            form = resp.forms["representative-form"]
            form["role"] = new_role
            resp = form.submit()

            target_rep.refresh_from_db()
            assert target_rep.role == new_role
            assert target_rep.user.organization == original_org, (
                "User's organization should not change during role update"
            )
        else:
            assert len(update_links) == 0

    def test_dataset_members_update_with_api_access(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)

        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
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
    @pytest.mark.parametrize(
        "coordinator_role,target_role,can_delete",
        [
            (Representative.OPEN_DATA_COORDINATOR, Representative.OPEN_DATA_MANAGER, True),
            (Representative.OPEN_DATA_COORDINATOR, Representative.RESOURCE_MANAGER, False),
            (Representative.RESOURCE_COORDINATOR, Representative.OPEN_DATA_MANAGER, True),
            (Representative.RESOURCE_COORDINATOR, Representative.RESOURCE_MANAGER, True),
        ],
    )
    def test_dataset_members_delete_member(self, app: DjangoTestApp, coordinator_role, target_role, can_delete):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)
        url = reverse("dataset-members", kwargs={"pk": dataset.pk})

        target_rep = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=target_role,
        )

        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=coordinator_role,
        )

        app.set_user(coordinator.user)
        resp = app.get(url)

        delete_links = [
            link for link in resp.html.find_all("a") if f"delete-member-{target_rep.pk}" in link.get("id", "")
        ]

        if can_delete:
            resp = resp.click(linkid=f"delete-member-{target_rep.pk}-btn")
            form = resp.forms["delete-form"]
            resp = form.submit()
            assert not Representative.objects.filter(pk=target_rep.pk).exists()
        else:
            assert len(delete_links) == 0

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "coordinator_role,target_role,can_delete",
        [
            (Representative.OPEN_DATA_COORDINATOR, Representative.OPEN_DATA_MANAGER, False),
            (Representative.OPEN_DATA_COORDINATOR, Representative.RESOURCE_MANAGER, False),
            (Representative.RESOURCE_COORDINATOR, Representative.OPEN_DATA_MANAGER, True),
            (Representative.RESOURCE_COORDINATOR, Representative.RESOURCE_MANAGER, True),
            (Representative.RESOURCE_MANAGER, Representative.RESOURCE_MANAGER, False),
            (Representative.RESOURCE_MANAGER, Representative.OPEN_DATA_MANAGER, False),
        ],
    )
    def test_dataset_members_delete_member_subclass_information_system(
        self, app: DjangoTestApp, coordinator_role, target_role, can_delete
    ):
        subclass = DCATResourceSubclassFactory(name="information_system")
        dataset = DatasetFactory(subclass=subclass)
        ct = ContentType.objects.get_for_model(Dataset)
        url = reverse("dataset-members", kwargs={"pk": dataset.pk})

        target_rep = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=target_role,
        )

        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=coordinator_role,
        )

        app.set_user(coordinator.user)
        resp = app.get(url)

        delete_links = [
            link for link in resp.html.find_all("a") if f"delete-member-{target_rep.pk}" in link.get("id", "")
        ]

        if can_delete:
            resp = resp.click(linkid=f"delete-member-{target_rep.pk}-btn")
            form = resp.forms["delete-form"]
            resp = form.submit()
            assert not Representative.objects.filter(pk=target_rep.pk).exists()
        else:
            assert len(delete_links) == 0

    def test_remove_dataset_publisher_of_related_dataset_if_representative_is_deleted(self, app: DjangoTestApp) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)

        organization = OrganizationFactory()
        dataset = DatasetFactory(publisher=organization)
        ct = ContentType.objects.get_for_model(dataset)
        representative = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_MANAGER,
            organization=organization,
        )

        app.post(reverse("dataset-representative-delete", args=[dataset.pk, representative.pk]))

        assert not Representative.objects.filter(pk=representative.pk).exists()
        dataset.refresh_from_db()
        assert dataset.publisher is None

    def test_add_member_to_dataset_with_org_representative(self, app: DjangoTestApp):
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
            role=Representative.OPEN_DATA_MANAGER,
        )

        app.set_user(user)
        response = app.get(reverse("dataset-members", args=[dataset.pk]), expect_errors=True)
        assert response.status_code == 403

    def test_dataset_member_create_invalid_phone(self, app: DjangoTestApp):
        ds = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)

        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=ds.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
        )
        app.set_user(coordinator.user)
        resp = app.get(reverse("dataset-members", kwargs={"pk": ds.pk}))
        resp = resp.click(linkid="add-member-btn")
        form = resp.forms["representative-form"]
        form["email"] = "new@gmail.com"
        form["role"] = "open_data_manager"
        form["phone"] = "123456"
        form.submit()

        assert resp.status_code == 200
        assert Representative.objects.filter(email="new@gmail.com").count() == 0

    def test_dataset_member_create_valid_phone(self, app: DjangoTestApp):
        ds = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)

        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=ds.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
        )
        app.set_user(coordinator.user)
        resp = app.get(reverse("dataset-members", kwargs={"pk": ds.pk}))
        resp = resp.click(linkid="add-member-btn")
        form = resp.forms["representative-form"]

        form["email"] = "new1@gmail.com"
        form["role"] = "open_data_manager"
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
        form["role"] = "open_data_manager"
        form["phone"] = "061234567"
        resp = form.submit()
        assert resp.status_code == 302
        rep_queryset = Representative.objects.filter(email="new2@gmail.com")
        assert rep_queryset.count() == 1
        assert rep_queryset.first().phone == "061234567"

    def test_dataset_member_update_phone(self, app: DjangoTestApp):
        ds = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)

        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=ds.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
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

    def test_create_representative_with_organization_email_coordinator_role_fails(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)
        superuser = UserFactory(is_superuser=True)
        org = OrganizationFactory(publisher=True)

        RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
            user=superuser,
        )

        app.set_user(superuser)
        resp = app.get(reverse("dataset-representative-create", kwargs={"pk": dataset.pk}))

        form = resp.forms["representative-form"]
        form["email"] = org.email
        form["role"] = Representative.OPEN_DATA_COORDINATOR
        resp = form.submit()

        assert resp.status_code == 200
        assert "Organizacijai gali būti suteikta tik tvarkytojo rolė" in resp.text
        assert not Representative.objects.filter(email=org.email).exists()

    def test_create_representative_with_organization_email_manager_role_succeeds(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)
        superuser = UserFactory(is_superuser=True)
        org = OrganizationFactory(publisher=True)

        RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
            user=superuser,
        )

        app.set_user(superuser)
        resp = app.get(reverse("dataset-representative-create", kwargs={"pk": dataset.pk}))

        form = resp.forms["representative-form"]
        form["email"] = org.email
        form["role"] = Representative.OPEN_DATA_MANAGER
        resp = form.submit()

        assert resp.status_code == 302
        rep = Representative.objects.get(email=org.email)
        assert rep.organization == org
        dataset.refresh_from_db()
        assert dataset.publisher == org


class TestDatasetAttribution:
    def test_dataset_create_attribution_with_organization_and_agent(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        organization = OrganizationFactory()
        attribution = AttributionFactory()

        form = app.get(reverse("attribution-add", args=[dataset.pk])).forms["attribution-form"]
        form["attribution"] = attribution.pk
        form["organization"].force_value(organization.pk)
        form["agent"] = "Test organization"
        resp = form.submit()

        assert list(resp.context["form"].errors.values()) == [
            ['Negalima užpildyti abiejų "Organizacija" ir "Agentas" laukų.']
        ]

    def test_dataset_create_attribution_without_organization_and_agent(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        attribution = AttributionFactory()

        form = app.get(reverse("attribution-add", args=[dataset.pk])).forms["attribution-form"]
        form["attribution"] = attribution.pk
        resp = form.submit()

        assert list(resp.context["form"].errors.values()) == [
            ['Privaloma užpildyti "Organizacija" arba "Agentas" lauką.']
        ]

    def test_dataset_create_attribution_with_existing_organization(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        attribution = AttributionFactory()
        organization = OrganizationFactory()
        DatasetAttributionFactory(dataset=dataset, attribution=attribution, organization=organization)

        form = app.get(reverse("attribution-add", args=[dataset.pk])).forms["attribution-form"]
        form["attribution"] = attribution.pk
        form["organization"].force_value(organization.pk)
        resp = form.submit()

        assert list(resp.context["form"].errors.values()) == [
            [f'Ryšys "{attribution.title}" su šia organizacija jau egzistuoja.']
        ]

    def test_dataset_create_attribution_with_existing_agent(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        attribution = AttributionFactory()
        DatasetAttributionFactory(dataset=dataset, attribution=attribution, agent="Test organization")

        form = app.get(reverse("attribution-add", args=[dataset.pk])).forms["attribution-form"]
        form["attribution"] = attribution.pk
        form["agent"] = "Test organization"
        resp = form.submit()

        assert list(resp.context["form"].errors.values()) == [
            [f'Ryšys "{attribution.title}" su šiuo agentu jau egzistuoja.']
        ]

    def test_dataset_create_attribution_with_organization(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        organization = OrganizationFactory()
        attribution = AttributionFactory()

        form = app.get(reverse("attribution-add", args=[dataset.pk])).forms["attribution-form"]
        form["attribution"] = attribution.pk
        form["organization"].force_value(organization.pk)
        resp = form.submit()

        assert resp.url == dataset.get_absolute_url()
        assert dataset.datasetattribution_set.count() == 1
        assert dataset.datasetattribution_set.first().organization == organization
        assert dataset.datasetattribution_set.first().attribution == attribution
        assert dataset.datasetattribution_set.first().agent is None

    def test_dataset_create_attribution_with_agent(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        attribution = AttributionFactory()

        form = app.get(reverse("attribution-add", args=[dataset.pk])).forms["attribution-form"]
        form["attribution"] = attribution.pk
        form["agent"] = "Test organization"
        resp = form.submit()

        assert resp.url == dataset.get_absolute_url()
        assert dataset.datasetattribution_set.count() == 1
        assert dataset.datasetattribution_set.first().agent == "Test organization"
        assert dataset.datasetattribution_set.first().attribution == attribution
        assert dataset.datasetattribution_set.first().organization is None

    def test_dataset_delete_attribution(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset_attribution = DatasetAttributionFactory()
        dataset = dataset_attribution.dataset

        resp = app.post(reverse("attribution-delete", args=[dataset.pk, dataset_attribution.pk]))

        assert resp.url == dataset.get_absolute_url()
        assert dataset.datasetattribution_set.count() == 0


class TestDatasetPlans:
    def test_add_dataset_to_plan(self, app: DjangoTestApp):
        user = UserFactory(is_staff=True)
        app.set_user(user)
        dataset = DatasetFactory()
        plan = PlanFactory(deadline=(date.today() + timedelta(days=1)))

        form = app.get(reverse("dataset-plans-create", args=[dataset.pk])).forms["dataset-plan-form"]
        form["plan"] = plan.pk
        resp = form.submit()

        assert resp.url == reverse("dataset-plans", args=[dataset.pk])
        assert dataset.plandataset_set.count() == 1
        assert dataset.plandataset_set.first().plan == plan

    def test_add_dataset_to_plan_title(self, app: DjangoTestApp):
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True, organization=organization)
        app.set_user(user)
        dataset = DatasetFactory(organization=organization)

        form = app.get(reverse("dataset-plans-create", args=[dataset.pk])).forms["plan-form"]
        form.submit()

        plan = Plan.objects.filter(plandataset__dataset=dataset)
        assert plan.count() == 1
        assert plan.first().title == "Duomenų atvėrimas"

    def test_add_dataset_to_plan_title_with_distribution(self, app: DjangoTestApp):
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True, organization=organization)
        app.set_user(user)
        dataset = DatasetFactory(organization=organization)
        DatasetDistributionFactory(dataset=dataset)

        form = app.get(reverse("dataset-plans-create", args=[dataset.pk])).forms["plan-form"]
        form.submit()

        plan = Plan.objects.filter(plandataset__dataset=dataset)
        assert plan.count() == 1
        assert plan.first().title == "Duomenų rinkinio papildymas"

    def test_delete_dataset_from_last_plan(self, app: DjangoTestApp):
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
        assert dataset.comments.count() == 0

    def test_delete_dataset_from_non_last_plan(self, app: DjangoTestApp):
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True, organization=organization)
        app.set_user(user)
        dataset = DatasetFactory(organization=organization, status=Dataset.PLANNED)
        plan1 = PlanFactory()
        PlanDataset.objects.create(dataset=dataset, plan=plan1)
        plan2 = PlanFactory()
        PlanDataset.objects.create(dataset=dataset, plan=plan2)

        form = app.get(reverse("dataset-plans-delete", args=[plan2.pk])).forms["delete-form"]
        form.submit()

        dataset.refresh_from_db()
        plan = Plan.objects.filter(plandataset__dataset=dataset)
        assert plan.count() == 1
        assert dataset.status == Dataset.PLANNED
        assert dataset.comments.count() == 0

    def test_delete_not_public_dataset_from_last_plan(self, app: DjangoTestApp):
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True, organization=organization)
        app.set_user(user)
        dataset = DatasetFactory(organization=organization, is_public=False, status=Dataset.UNASSIGNED)
        plan = PlanFactory()
        PlanDataset.objects.create(dataset=dataset, plan=plan)

        form = app.get(reverse("dataset-plans-delete", args=[plan.pk])).forms["delete-form"]
        form.submit()

        dataset.refresh_from_db()
        plan = Plan.objects.filter(plandataset__dataset=dataset)
        assert plan.count() == 0
        assert dataset.status == Dataset.UNASSIGNED
        assert dataset.comments.count() == 0

    def test_delete_opened_dataset_from_last_plan(self, app: DjangoTestApp):
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

    def test_plan_tab_with_non_public_dataset_without_access(self, app: DjangoTestApp):
        dataset = DatasetFactory(is_public=False)
        user = UserFactory()
        app.set_user(user)
        response = app.get(reverse("dataset-plans", args=[dataset.pk]), expect_errors=True)
        assert response.status_code == 403

    def test_plan_tab_with_non_public_dataset_with_access(self, app: DjangoTestApp):
        dataset = DatasetFactory(is_public=False)
        user = UserFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )
        app.set_user(user)
        response = app.get(reverse("dataset-plans", args=[dataset.pk]))
        assert response.context["dataset"] == dataset


class TestDatasetProject:
    def test_add_project_with_permission(self, app: DjangoTestApp):
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

    def test_add_organization_project_with_permission(self, app: DjangoTestApp, organization: Organization):
        user = UserFactory()
        RepresentativeFactory(user=user, content_object=organization)
        project = ProjectFactory(organization=organization)
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

    def test_add_project_with_agreements(self, app: DjangoTestApp, organization: Organization):
        user = UserFactory(is_staff=True)
        project = ProjectFactory(organization=organization)
        AgreementFactory(project=project)
        dataset = DatasetFactory()
        app.set_user(user)
        resp = app.get(reverse("dataset-project-add", kwargs={"pk": dataset.pk}))
        assert resp.status_code == 302
        assert resp.url == reverse("dataset-projects", kwargs={"pk": dataset.pk})

    def test_project_tab_with_non_public_dataset_without_access(self, app: DjangoTestApp):
        dataset = DatasetFactory(is_public=False)
        user = UserFactory()
        app.set_user(user)
        response = app.get(reverse("dataset-projects", args=[dataset.pk]), expect_errors=True)
        assert response.status_code == 403

    def test_project_tab_with_non_public_dataset_with_access(self, app: DjangoTestApp):
        dataset = DatasetFactory(is_public=False)
        user = UserFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )
        app.set_user(user)
        response = app.get(reverse("dataset-projects", args=[dataset.pk]))
        assert response.context["dataset"] == dataset

    def test_add_project_with_no_available_projects(self, app: DjangoTestApp):
        user = UserFactory()
        dataset = DatasetFactory()
        app.set_user(user)
        resp = app.get(reverse("dataset-project-add", kwargs={"pk": dataset.pk}), expect_errors=True)
        assert resp.status_code == 302

    def test_remove_project_no_permission(self, app: DjangoTestApp):
        user = UserFactory()
        project = ProjectFactory()
        dataset = DatasetFactory()
        project.datasets.add(dataset)
        assert project.datasets.all().count() == 1

        app.set_user(user)

        resp = app.post(
            reverse(
                "dataset-project-remove",
                kwargs={"pk": dataset.pk, "project_id": project.pk},
            ),
            expect_errors=True,
        )

        assert resp.status_code == 302

    def test_remove_dataset_from_project(self, app: DjangoTestApp):
        user = UserFactory()
        project = ProjectFactory(user=user)
        dataset = DatasetFactory()
        project.datasets.add(dataset)
        assert project.datasets.all().count() == 1

        app.set_user(user)

        resp = app.post(
            reverse(
                "dataset-project-remove",
                kwargs={"pk": dataset.pk, "project_id": project.pk},
            ),
            expect_errors=True,
        )

        assert resp.status_code == 302
        assert Dataset.objects.exists()
        project.refresh_from_db()
        assert not project.datasets.exists()

    def test_remove_dataset_from_project_with_agreements(self, app: DjangoTestApp):
        user = UserFactory()
        project = ProjectFactory(user=user)
        dataset = DatasetFactory()
        project.datasets.add(dataset)
        AgreementFactory(project=project)
        assert project.datasets.all().count() == 1

        app.set_user(user)

        resp = app.post(
            reverse(
                "dataset-project-remove",
                kwargs={"pk": dataset.pk, "project_id": project.pk},
            ),
            expect_errors=True,
        )

        assert resp.status_code == 302
        assert dataset in project.datasets.all()

    def test_remove_project_with_permission(self, app: DjangoTestApp):
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


def test_add_subclass_form_no_login(app: DjangoTestApp):
    org = OrganizationFactory()
    response = app.get(reverse("resource-subclass-add", kwargs={"pk": org.id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


def test_add_subclass_form_wrong_login(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    org = OrganizationFactory()
    response = app.get(reverse("resource-subclass-add", kwargs={"pk": org.id}), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.haystack
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


@pytest.mark.haystack
def test_organization_dataset_list_with_matching_jurisdiction(app: DjangoTestApp):
    jurisdiction = AreaOfManagementFactory(id=30, name_lt="Organization")
    organization = OrganizationFactory(title="Organization", jurisdiction=jurisdiction)
    dataset1 = DatasetFactory(organization=organization)
    dataset2 = DatasetFactory(organization=organization)
    user = UserFactory()
    app.set_user(user)
    resp = app.get(
        "%s?selected_facets=organization_exact:%s"
        % (reverse("organization-datasets", args=[organization.pk]), organization.pk)
    )
    assert sorted([int(obj.pk) for obj in resp.context["object_list"]]) == sorted([dataset1.pk, dataset2.pk])


def test_dataset_history_cant_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory(is_public=True, access_rights=Dataset.CONFIDENTIAL)
    app.set_user(user)
    resp = app.get(reverse("dataset-history", args=[dataset.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_dataset_history_can_view_public(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory(is_public=True, access_rights=Dataset.PUBLIC)
    app.set_user(user)
    resp = app.get(reverse("dataset-history", args=[dataset.pk]), expect_errors=True)
    assert resp.status_code == 200


def test_dataset_history_view_with_permission(app: DjangoTestApp):
    user = ManagerFactory(is_staff=True)
    dataset = DatasetFactory(organization=user.organization)
    app.set_user(user)
    url = reverse("dataset-change", args=[dataset.pk])
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="dataset-change",
        http_method="POST",
        path=url,
        args=[],
        kwargs={"pk": dataset.pk},
    )
    form = app.get(url).forms["dataset-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    resp = form.submit().follow().follow()
    resp = resp.click(linkid="history-tab").click(linkid="history-tab")
    assert resp.context["detail_url_name"] == "dataset-detail"
    assert resp.context["history_url_name"] == "dataset-history"
    assert len(resp.context["history"]) == 1
    history_action = resp.context["history"][0]["action"]
    assert history_action["comment"] == f"{revision_comment.action}({revision_comment.kwargs})"
    assert resp.context["history"][0]["user"] == user


def test_dataset_structure_import_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    metadata_version = VersionFactory(dataset=dataset)
    app.set_user(user)
    url = reverse("dataset-structure-import", args=[dataset.pk, metadata_version.pk])
    resp = app.get(url, expect_errors=True)

    assert resp.status_code == 403


@pytest.mark.parametrize("status", [s for s in VersionStatus.values if s != VersionStatus.DRAFT])
def test_dataset_import_in_not_draft_version(app: DjangoTestApp, status: str):
    version = VersionFactory(status=status)
    user = UserFactory(is_staff=True)
    dataset = version.dataset

    app.set_user(user)
    url = reverse("dataset-structure-import", args=[dataset.pk, version.pk])
    response = app.get(url)
    assert response.status_code == 302
    assert response.location == dataset.get_absolute_url()


def test_dataset_structure_import_not_standardized(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()
    metadata_version = VersionFactory(dataset=dataset)

    app.set_user(user)
    resp = app.get(reverse("dataset-structure-import", args=[dataset.pk, metadata_version.pk]))
    form = resp.forms["dataset-structure-form"]
    form["file"] = Upload("manifest.csv", b"Column\nValue")
    form.submit()

    dataset.refresh_from_db()
    structure = DatasetStructure.objects.get(dataset=dataset)
    assert dataset.current_structure == structure
    assert File.objects.count() == 1
    assert structure.file.original_filename == "manifest.csv"


def test_dataset_structure_import_standardized(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()
    metadata_version = VersionFactory(dataset=dataset)

    app.set_user(user)
    resp = app.get(reverse("dataset-structure-import", args=[dataset.pk, metadata_version.pk]))
    form = resp.forms["dataset-structure-form"]
    form["file"] = Upload("file.csv", MANIFEST.encode())
    form.submit()

    dataset.refresh_from_db()
    structure = DatasetStructure.objects.get(dataset=dataset)
    assert dataset.current_structure == structure
    assert File.objects.count() == 1
    assert structure.file.original_filename == "file.csv"


def test_dataset_structure_import_with_version(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()
    version = VersionFactory(dataset=dataset, status=VersionStatus.DRAFT)

    app.set_user(user)
    resp = app.get(reverse("dataset-structure-import", args=[dataset.pk, version.pk]))
    form = resp.forms["dataset-structure-form"]
    form["file"] = Upload("file.csv", MANIFEST.encode())
    form.submit()

    dataset.refresh_from_db()
    structure = DatasetStructure.objects.get(dataset=dataset)
    assert dataset.current_structure == structure
    assert File.objects.count() == 1
    assert structure.file.original_filename == "file.csv"


def test_dataset_assign_new_category_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)

    group = DatasetGroupFactory()
    category = CategoryFactory()
    DatasetGroupCategoryUriFactory(
        group=group,
        category=category,
    )

    dataset = DatasetFactory()
    resp = app.get(reverse("assign-category", args=[dataset.pk]), expect_errors=True)
    assert resp.status_code == 403


def test_dataset_assign_new_category(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    group = DatasetGroupFactory()
    category1 = CategoryFactory()
    DatasetGroupCategoryUriFactory(
        group=group,
        category=category1,
    )
    category2 = CategoryFactory()
    DatasetGroupCategoryUriFactory(
        group=group,
        category=category2,
    )
    category3 = CategoryFactory()
    DatasetGroupCategoryUriFactory(
        group=group,
        category=category3,
    )

    dataset = DatasetFactory()
    resp = app.post(
        reverse("assign-category", args=[dataset.pk]),
        {"category": [category1.pk, category2.pk]},
    )
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert list(dataset.category.order_by("pk")) == [category1, category2]


def test_dataset_change_category(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)

    group = DatasetGroupFactory()
    category1 = CategoryFactory()
    DatasetGroupCategoryUriFactory(
        group=group,
        category=category1,
    )
    category2 = CategoryFactory()
    DatasetGroupCategoryUriFactory(
        group=group,
        category=category2,
    )
    category3 = CategoryFactory()
    DatasetGroupCategoryUriFactory(
        group=group,
        category=category3,
    )

    dataset = DatasetFactory()
    dataset.category.add(category1)
    dataset.category.add(category2)

    resp = app.post(reverse("assign-category", args=[dataset.pk]), {"category": [category3.pk]})
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert list(dataset.category.all()) == [category3]


def test_dataset_add_relation_with_existing_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset_relation = DatasetRelationFactory()

    form = app.get(reverse("dataset-relation-add", args=[dataset_relation.dataset.pk])).forms["dataset-relation-form"]
    form["relation_type"] = f"{dataset_relation.relation.pk}"
    form["part_of"].force_value(dataset_relation.part_of.pk)
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        [f'"{dataset_relation.relation.title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.']
    ]


def test_dataset_add_relation_with_existing_inverse_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset_relation = DatasetRelationFactory()

    form = app.get(reverse("dataset-relation-add", args=[dataset_relation.part_of.pk])).forms["dataset-relation-form"]
    form["relation_type"] = f"{dataset_relation.relation.pk}_inv"
    form["part_of"].force_value(dataset_relation.dataset.pk)
    resp = form.submit()
    assert list(resp.context["form"].errors.values()) == [
        [f'"{dataset_relation.relation.inversive_title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.']
    ]


def test_dataset_add_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    dataset_part_of = DatasetFactory()
    relation = RelationFactory()

    form = app.get(reverse("dataset-relation-add", args=[dataset.pk])).forms["dataset-relation-form"]
    form["relation_type"] = f"{relation.pk}"
    form["part_of"].force_value(dataset_part_of.pk)
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.url == dataset.get_absolute_url()
    assert dataset.part_of.count() == 1
    assert dataset.part_of.first().part_of == dataset_part_of
    assert dataset.part_of.first().relation == relation


def test_dataset_add_inverse_relation(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory()
    dataset_part_of = DatasetFactory()
    relation = RelationFactory()

    form = app.get(reverse("dataset-relation-add", args=[dataset.pk])).forms["dataset-relation-form"]
    form["relation_type"] = f"{relation.pk}_inv"
    form["part_of"].force_value(dataset_part_of.pk)
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.url == dataset.get_absolute_url()
    assert dataset_part_of.part_of.count() == 1
    assert dataset_part_of.part_of.first().part_of == dataset
    assert dataset_part_of.part_of.first().relation == relation


def test_delete_last_distribution_from_dataset(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    resource = DatasetDistributionFactory(dataset=dataset)
    ModelFactory(dataset=resource.dataset, distribution=resource)

    app.post(reverse("resource-delete", args=[resource.pk, resource.metadata_version.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.INVENTORED
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.INVENTORED


def test_delete_non_last_distribution_from_dataset(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    DatasetDistributionFactory(dataset=dataset)
    resource2 = DatasetDistributionFactory(dataset=dataset)
    ModelFactory(dataset=resource2.dataset, distribution=resource2)

    app.post(reverse("resource-delete", args=[resource2.pk, resource2.metadata_version.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 1
    assert dataset.status == Dataset.HAS_DATA
    assert dataset.comments.count() == 0


def test_delete_last_distribution_from_non_public_dataset(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.UNASSIGNED, is_public=False)
    resource = DatasetDistributionFactory(dataset=dataset)
    ModelFactory(dataset=resource.dataset, distribution=resource)

    app.post(reverse("resource-delete", args=[resource.pk, resource.metadata_version.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.UNASSIGNED
    assert dataset.comments.count() == 0


def test_delete_last_distribution_from_dataset_with_plans(app: DjangoTestApp):
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True, organization=organization)
    app.set_user(user)
    dataset = DatasetFactory(organization=organization, status=Dataset.HAS_DATA)
    resource = DatasetDistributionFactory(dataset=dataset)
    ModelFactory(dataset=resource.dataset, distribution=resource)
    plan = PlanFactory()
    PlanDataset.objects.create(dataset=dataset, plan=plan)

    app.post(reverse("resource-delete", args=[resource.pk, resource.metadata_version.pk]))

    dataset.refresh_from_db()
    assert dataset.datasetdistribution_set.count() == 0
    assert dataset.status == Dataset.PLANNED
    assert dataset.comments.count() == 1
    assert dataset.comments.first().type == Comment.STATUS
    assert dataset.comments.first().status == Comment.PLANNED


def test_request_tab_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    app.set_user(user)
    response = app.get(reverse("dataset-requests", args=[dataset.pk]), expect_errors=True)
    assert response.status_code == 403


def test_request_tab_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER,
    )
    app.set_user(user)
    response = app.get(reverse("dataset-requests", args=[dataset.pk]))
    assert response.context["dataset"] == dataset


def test_dataset_dynamic_resources(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="TestModel")
    resource = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    metadata_version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="TestModel",
        metadata_version=metadata_version,
    )
    response = app.get(reverse("dataset-detail", args=[dataset.pk])).follow()
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
            "Ištrinti",
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


def test_dataset_dynamic_resources_multiple_models(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    app.set_user(user)
    dataset = DatasetFactory(metadata="TestModel")
    resource = DatasetDistributionFactory(dataset=dataset, uapi_format=True)
    metadata_version = VersionFactory(dataset=dataset)
    model = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        name="TestModel",
        metadata_version=metadata_version,
    )
    model2 = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model2),
        object_id=model2.pk,
        name="TestModel2",
        metadata_version=metadata_version,
    )
    model3 = ModelFactory(dataset=dataset, metadata_version=metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model3),
        object_id=model3.pk,
        name="TestModel3",
        metadata_version=metadata_version,
    )

    response = app.get(reverse("dataset-detail", args=[resource.dataset.pk])).follow()
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
            "Ištrinti",
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
    ModelFactory(dataset=dataset, distribution=dist1, metadata_version=dataset.metadata.first().metadata_version)
    ModelFactory(dataset=dataset, distribution=dist2, metadata_version=dataset.metadata.first().metadata_version)

    res = app.get(reverse("dataset-rdf-download", args=[dataset.pk]))

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/rdf+xml"
    assert (
        strip_empty_lines(res.text)
        == f'''\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://localhost"
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
    <dcat:Dataset rdf:about="http://localhost/datasets/{dataset.id}/">
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
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/versions/{dist1.metadata_version.id}/resource/{dist1.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">Failas 1</dct:title>
                <dct:description xml:lang="lt">Failas su prieigos nuoroda</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{dist1.access_url}"/>
                <dcat:downloadURL rdf:resource="http://localhost{dist1.file.url}"/>
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
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/versions/{dist2.metadata_version.id}/resource/{dist2.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">Failas 2</dct:title>
                <dct:description xml:lang="lt">Failas be prieigos nuorodos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{dataset.landing_page}"/>
                <dcat:downloadURL rdf:resource="http://localhost{dist2.file.url}"/>
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
    ModelFactory(dataset=dataset, distribution=dist1, metadata_version=dataset.metadata.first().metadata_version)
    ModelFactory(dataset=dataset, distribution=dist2, metadata_version=dataset.metadata.first().metadata_version)

    res = app.get(reverse("dataset-rdf-download", args=[dataset.pk]))

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/rdf+xml"
    assert (
        strip_empty_lines(res.text)
        == f'''\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://localhost"
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
    <dcat:Dataset rdf:about="http://localhost/datasets/{dataset.id}/">
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
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/versions/{dist1.metadata_version.id}/resource/{dist1.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">Failas 1</dct:title>
                <dct:description xml:lang="lt">Failas su prieigos nuoroda</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist1.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{dist1.access_url}"/>
                <dcat:downloadURL rdf:resource="http://localhost{dist1.file.url}"/>
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
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/versions/{dist2.metadata_version.id}/resource/{dist2.id}">
                <dct:type rdf:resource="http://publications.europa.eu/resource/authority/distribution-type/DOWNLOADABLE_FILE"/>
                <dct:title xml:lang="lt">Failas 2</dct:title>
                <dct:description xml:lang="lt">Failas be prieigos nuorodos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist2.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="http://localhost{dist2.file.url}"/>
                <dcat:downloadURL rdf:resource="http://localhost{dist2.file.url}"/>
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
    model = ModelFactory(dataset=dataset, metadata_version=dataset.metadata.first().metadata_version)
    MetadataFactory(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        name="test/dataset/TestModel",
        metadata_version=dataset.metadata.first().metadata_version,
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
    xml:base="http://localhost"
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
    <dcat:Dataset rdf:about="http://localhost/datasets/{dataset.id}/">
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
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/resource/{dist.id}/dataset/json">
                <dct:type rdf:resource="URL"/>
                <dct:title xml:lang="lt">Duomenys</dct:title>
                <dct:description xml:lang="lt">Duomenys iš spintos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset"/>
                <dcat:downloadURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset/:all/:format/json"/>
                <dcat:accessService rdf:resource="http://localhost/datasets/{data_service.pk}/"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about=""/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about=""/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/resource/{dist.id}/dataset/jsonl">
                <dct:type rdf:resource="URL"/>
                <dct:title xml:lang="lt">Duomenys</dct:title>
                <dct:description xml:lang="lt">Duomenys iš spintos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset"/>
                <dcat:downloadURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset/:all/:format/jsonl"/>
                <dcat:accessService rdf:resource="http://localhost/datasets/{data_service.pk}/"/>
                <dct:rights>
                    <dct:RightsStatement>platinimo sąlygos</dct:RightsStatement>
                </dct:rights>
                <dct:license>
                    <dct:LicenseDocument rdf:about="http://publications.europa.eu/resource/authority/licence/CC_BY_4_0"/>
                </dct:license>
                <dcat:mediaType>
                    <dct:MediaType rdf:about=""/>
                </dcat:mediaType>
                <dct:format>
                    <dct:MediaTypeOrExtent rdf:about=""/>
                </dct:format>
            </dcat:Distribution>
        </dcat:distribution>
        <dcat:distribution>
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/resource/{dist.id}/dataset/rdf">
                <dct:type rdf:resource="URL"/>
                <dct:title xml:lang="lt">Duomenys</dct:title>
                <dct:description xml:lang="lt">Duomenys iš spintos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset"/>
                <dcat:downloadURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset/:all/:format/rdf"/>
                <dcat:accessService rdf:resource="http://localhost/datasets/{data_service.pk}/"/>
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
            <dcat:Distribution rdf:about="http://localhost/datasets/{dataset.id}/resource/{dist.id}/TestModel/csv">
                <dct:type rdf:resource="URL"/>
                <dct:title xml:lang="lt">Duomenys</dct:title>
                <dct:description xml:lang="lt">Duomenys iš spintos</dct:description>
                <dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.created.strftime("%Y-%m-%d")}</dct:issued>
                <dct:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">{dist.modified.strftime("%Y-%m-%d")}</dct:modified>
                <dcat:accessURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset"/>
                <dcat:downloadURL rdf:resource="{SPINTA_SERVER_URL}/test/dataset/TestModel/:format/csv"/>
                <dcat:accessService rdf:resource="http://localhost/datasets/{data_service.pk}/"/>
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
    relation = DatasetRelationFactory(part_of=dataset, relation=RelationFactory(name=Relation.SERVICE))
    relation.dataset.part_of.add(relation)

    res = app.get(reverse("dataset-rdf-download", args=[dataset.pk]))

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/rdf+xml"
    assert (
        strip_empty_lines(res.text)
        == f"""\
<?xml version="1.0"?>
<rdf:RDF
    xml:base="http://localhost"
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
    <dcat:DataService rdf:about="http://localhost/datasets/{dataset.id}/">
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
            <dcat:Dataset rdf:about="http://localhost/datasets/{relation.dataset.pk}/" />
        </dcat:servesDataset>
    </dcat:DataService>
</rdf:RDF>"""
    )


class TestRemoveRequestView:
    def test_delete_dataset_comments_and_related_request_object(self, app: DjangoTestApp) -> None:
        user = UserFactory(is_staff=True)
        app.set_user(user)

        dataset = DatasetFactory()
        request = RequestFactory(dataset=dataset)
        comment = CommentFactory(
            rel_content_type=ContentType.objects.get_for_model(request),
            rel_object_id=request.pk,
        )
        request_object = RequestObjectFactory(
            request=request,
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
        )

        app.post(reverse("dataset-request-remove", args=[dataset.pk, request_object.pk]))

        assert Dataset.objects.filter(pk=dataset.pk).exists()
        assert not Comment.objects.filter(pk=comment.pk).exists()
        assert not RequestObject.objects.filter(pk=request_object.pk).exists()


@pytest.mark.django_db
class TestDatasetMemberCreate:
    def test_dataset_coordinator_not_added_to_organization(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        admin = UserFactory(is_staff=True)

        app.set_user(admin)

        # Add new coordinator to dataset
        url = reverse("dataset-representative-create", args=[dataset.pk])
        resp = app.get(url)
        form = resp.forms["representative-form"]
        form["email"] = "new.coordinator@test.com"
        form.submit()

        # Coordinator representative should be created for the DATASET
        coordinator_rep = Representative.objects.get(
            email="new.coordinator@test.com",
            content_type=ContentType.objects.get_for_model(dataset.__class__),
            object_id=dataset.pk,
        )
        assert coordinator_rep.role == Representative.RESOURCE_COORDINATOR

        # User doesn't exist yet (will be created when they register)
        # But if they existed, they should NOT have org assigned
        assert not User.objects.filter(email="new.coordinator@test.com").exists()

    def test_existing_user_assigned_as_coordinator_keeps_no_org(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        existing_user = UserFactory(organization=None)
        admin = UserFactory(is_staff=True)
        app.set_user(admin)

        url = reverse("dataset-representative-create", args=[dataset.pk])
        resp = app.get(url)
        form = resp.forms["representative-form"]
        form["email"] = existing_user.email
        form["role"] = Representative.OPEN_DATA_COORDINATOR
        form.submit()

        existing_user.refresh_from_db()

        # User should still have NO organization
        assert existing_user.organization is None, (
            f"User should not be added to dataset's organization, but has {existing_user.organization}"
        )

    def test_existing_user_from_different_org_not_changed(self, app: DjangoTestApp):
        org_a = OrganizationFactory(title="Org A")
        org_b = OrganizationFactory(title="Org B")
        dataset_in_org_a = DatasetFactory(organization=org_a)

        user_from_org_b = UserFactory(organization=org_b)
        original_org = user_from_org_b.organization

        admin = UserFactory(is_staff=True)
        app.set_user(admin)

        url = reverse("dataset-representative-create", args=[dataset_in_org_a.pk])
        resp = app.get(url)
        form = resp.forms["representative-form"]
        form["email"] = user_from_org_b.email
        form.submit()

        user_from_org_b.refresh_from_db()

        # User should still belong to Org B, NOT Org A
        assert user_from_org_b.organization == original_org, (
            f"User's organization should not be changed from {original_org} to {user_from_org_b.organization}"
        )
        assert user_from_org_b.organization != org_a

    def test_coordinator_has_representative_for_dataset_not_org(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)

        user = UserFactory()
        admin = UserFactory(is_staff=True)
        app.set_user(admin)

        url = reverse("dataset-representative-create", args=[dataset.pk])
        resp = app.get(url)
        form = resp.forms["representative-form"]
        form["email"] = user.email
        form.submit()

        user.refresh_from_db()

        # Should have representative for DATASET
        dataset_reps = Representative.objects.filter(
            user=user, content_type=ContentType.objects.get_for_model(dataset.__class__), object_id=dataset.pk
        )
        assert dataset_reps.exists(), "User should have representative for dataset"

        # Should NOT have representative for ORGANIZATION
        org_reps = Representative.objects.filter(
            user=user, content_type=ContentType.objects.get_for_model(org.__class__), object_id=org.pk
        )
        assert not org_reps.exists(), "User should NOT have representative for organization"

    def test_manager_same_behavior_as_coordinator(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)

        existing_user = UserFactory(organization=None)

        admin = UserFactory(is_staff=True)
        app.set_user(admin)

        url = reverse("dataset-representative-create", args=[dataset.pk])
        resp = app.get(url)
        form = resp.forms["representative-form"]
        form["email"] = existing_user.email
        form["role"] = Representative.OPEN_DATA_MANAGER
        form.submit()

        existing_user.refresh_from_db()

        # Manager should also not be added to org
        assert existing_user.organization is None

    def test_user_with_org_assigned_to_their_own_org_dataset_keeps_org(self, app: DjangoTestApp):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)

        # User already belongs to the dataset's org
        user = UserFactory(organization=org)

        admin = UserFactory(is_staff=True)
        app.set_user(admin)

        url = reverse("dataset-representative-create", args=[dataset.pk])
        resp = app.get(url)
        form = resp.forms["representative-form"]
        form["email"] = user.email
        form.submit()

        user.refresh_from_db()

        assert user.organization == org


class TestDatasetMemberUpdate:
    def test_dataset_member_update_does_not_assign_org(self, app: DjangoTestApp):
        dataset = DatasetFactory()
        ct = ContentType.objects.get_for_model(Dataset)

        user = UserFactory(organization=None)

        representative = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_MANAGER,
            user=user,
        )

        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
        )

        app.set_user(coordinator.user)
        resp = app.get(reverse("dataset-members", kwargs={"pk": dataset.pk}))
        resp = resp.click(linkid=f"update-member-{representative.pk}-btn")

        form = resp.forms["representative-form"]
        form["has_api_access"] = True
        form.submit()

        user.refresh_from_db()
        assert user.organization is None, "User's org should not be assigned during update"

import pytest
import pytz
from datetime import datetime, date
from django.urls import reverse
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory
from vitrina.requests.factories import RequestFactory, RequestStructureFactory
from vitrina.requests.models import Request
from vitrina.datasets.models import Dataset
from vitrina.classifiers.models import Category
from vitrina.classifiers.factories import CategoryFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.users.factories import UserFactory, ManagerFactory
from vitrina.users.factories import UserFactory

timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.fixture
def search_requests():
    request1 = RequestFactory(slug='r1')
    request1.title = 'Poreikis 1'
    request1.created = timezone.localize(datetime(2022, 6, 1))
    request1.save()

    request2 = RequestFactory(slug='r2')
    request2.title = 'Poreikis 2'
    request2.created = timezone.localize(datetime(2022, 8, 1))
    request2.save()

    request3 = RequestFactory(slug='r3')
    request3.title = "Poreikis 3 \"<'>\\"
    request3.created = timezone.localize(datetime(2022, 7, 1))
    request3.save()
    return [request1, request2, request3]


@pytest.mark.haystack
def test_search_without_query(app: DjangoTestApp, search_requests):
    resp = app.get(reverse('request-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_requests[1].pk, search_requests[2].pk, search_requests[0].pk]

@pytest.mark.haystack
def test_search_with_query_that_doesnt_match(app: DjangoTestApp, search_requests):
    resp = app.get("%s?q=%s" % (reverse('request-list'), "doesnt-match"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == []

@pytest.mark.haystack
def test_search_with_query_that_matches_one(app: DjangoTestApp, search_requests):
    resp = app.get("%s?q=%s" % (reverse('request-list'), "Poreikis 3"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_requests[2].pk]

@pytest.mark.haystack
def test_search_with_query_that_matches_all(app: DjangoTestApp, search_requests):
    resp = app.get("%s?q=%s" % (reverse('request-list'), "Poreikis"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_requests[1].pk, search_requests[2].pk, search_requests[0].pk]

@pytest.mark.haystack
def test_search_with_query_containing_special_characters(app: DjangoTestApp, search_requests):
    resp = app.get("%s?q=%s" % (reverse('request-list'), "3 \"<'>\\"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [search_requests[2].pk]

@pytest.fixture
def status_filter_data():
    request1 = RequestFactory()
    dataset = DatasetFactory(status=Dataset.INVENTORED)
    request1.save()
    request2 = RequestFactory(dataset=dataset)
    request2.save()
    return [request1, request2]

@pytest.mark.haystack
def test_status_filter_without_query(app: DjangoTestApp, status_filter_data):
    resp = app.get(reverse('request-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        status_filter_data[1].pk,
        status_filter_data[0].pk
    ]
    assert resp.context['selected_status'] is None

@pytest.mark.haystack
def test_status_filter_inventored(app: DjangoTestApp, status_filter_data):
    resp = app.get("%s?selected_facets=filter_status_exact:%s" % (
        reverse('request-list'),
        Dataset.INVENTORED
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [status_filter_data[1].pk]
    assert resp.context['selected_status'] == Dataset.INVENTORED

@pytest.fixture
def organization_filter_data():
    organization = OrganizationFactory()
    dataset = DatasetFactory(organization=organization, slug='d')
    request1 = RequestFactory(dataset=dataset, slug='r1')
    request2 = RequestFactory(dataset=dataset, slug='r2')

    return {
        "organization": organization,
        "requests": [request1, request2]
    }

@pytest.mark.haystack
def test_organization_filter_without_query(app: DjangoTestApp, organization_filter_data):
    resp = app.get(reverse('request-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        organization_filter_data["requests"][1].pk,
        organization_filter_data['requests'][0].pk
    ]
    assert resp.context['selected_organization'] is None

@pytest.mark.haystack
def test_organization_filter_with_organization(app: DjangoTestApp, organization_filter_data):
    resp = app.get("%s?selected_facets=organization_exact:%s" % (
        reverse("request-list"),
        organization_filter_data["organization"].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        organization_filter_data["requests"][1].pk,
        organization_filter_data['requests'][0].pk
    ]
    assert resp.context['selected_organization'] == organization_filter_data["organization"].pk

@pytest.fixture
def category_filter_data():
    organization = OrganizationFactory()

    category1 = CategoryFactory(title='Cat 1')
    category2 = category1.add_child(
        instance=CategoryFactory.build(title='Cat 1.1'),
    )
    category3 = category1.add_child(
        instance=CategoryFactory.build(title='Cat 1.2'),
    )
    category4 = category2.add_child(
        instance=CategoryFactory.build(title='Cat 2.1'),
    )
    dataset_with_category1 = DatasetFactory(category=category1, slug="ds1", organization=organization)
    dataset_with_category2 = DatasetFactory(category=category2, slug="ds2", organization=organization)
    dataset_with_category3 = DatasetFactory(category=category3, slug="ds3", organization=organization)
    dataset_with_category4 = DatasetFactory(category=category4, slug="ds4", organization=organization)

    request1 = RequestFactory(dataset=dataset_with_category1)
    request2 = RequestFactory(dataset=dataset_with_category2)
    request3 = RequestFactory(dataset=dataset_with_category3)
    request4 = RequestFactory(dataset=dataset_with_category4)

    return {
        "categories": [category1, category2, category3, category4],
        "requests": [
            request1,
            request2,
            request3,
            request4,
        ],
    }

@pytest.mark.haystack
def test_category_filter_without_query(app: DjangoTestApp, category_filter_data):
    resp = app.get(reverse('request-list'))
    assert len(resp.context['object_list']) == 4
    assert resp.context['selected_categories'] == []

@pytest.mark.haystack
def test_category_filter_with_parent_category(app: DjangoTestApp, category_filter_data):
    resp = app.get("%s?selected_facets=category_exact:%s" % (
        reverse("request-list"),
        category_filter_data["categories"][0].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        category_filter_data["requests"][3].pk,
        category_filter_data["requests"][2].pk,
        category_filter_data["requests"][1].pk,
        category_filter_data["requests"][0].pk
    ]
    assert resp.context['selected_categories'] == [str(category_filter_data["categories"][0].pk)]

@pytest.mark.haystack
def test_category_filter_with_middle_category(
    app: DjangoTestApp,
    category_filter_data: dict[str, list[Category]],
):
    resp = app.get("%s?selected_facets=category_exact:%s" % (
        reverse("request-list"),
        category_filter_data["categories"][1].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        category_filter_data["requests"][3].pk,
        category_filter_data["requests"][1].pk,
    ]
    assert resp.context['selected_categories'] == [
        str(category_filter_data["categories"][1].pk),
    ]


@pytest.mark.haystack
def test_category_filter_with_child_category(
    app: DjangoTestApp,
    category_filter_data: dict[str, list[Category]],
):
    resp = app.get("%s?selected_facets=category_exact:%s" % (
        reverse("request-list"),
        category_filter_data["categories"][3].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        category_filter_data["requests"][3].pk,
    ]
    assert resp.context['selected_categories'] == [
        str(category_filter_data["categories"][3].pk),
    ]


@pytest.mark.haystack
def test_category_filter_with_parent_and_child_category(
    app: DjangoTestApp,
    category_filter_data: dict[str, list[Category]],
):
    resp = app.get((
        '%s?'
        'selected_facets=category_exact:%s&'
        'selected_facets=category_exact:%s'
    ) % (
        reverse("request-list"),
        category_filter_data["categories"][0].pk,
        category_filter_data["categories"][3].pk
    ))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        category_filter_data["requests"][3].pk,
    ]
    assert resp.context['selected_categories'] == [
        str(category_filter_data["categories"][0].pk),
        str(category_filter_data["categories"][3].pk)
    ]

@pytest.fixture
def requests():
    dataset1 = DatasetFactory(tags=('tag1', 'tag2', 'tag3'), slug="ds1")
    dataset2 = DatasetFactory(tags=('tag3', 'tag4', 'tag5'), slug="ds2")
    request1 = RequestFactory(dataset=dataset1)
    request2 = RequestFactory(dataset=dataset2)

    return [request1, request2]


@pytest.mark.haystack
def test_tag_filter_without_query(app: DjangoTestApp, requests):
    resp = app.get(reverse('request-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        requests[1].pk, requests[0].pk,
    ]
    assert [int(obj.pk) for obj in resp.context['object_list']] == [requests[1].pk, requests[0].pk]
    assert resp.context['selected_tags'] == []

@pytest.mark.haystack
def test_tag_filter_with_one_tag(app: DjangoTestApp, requests):
    resp = app.get("%s?selected_facets=tags_exact:tag2" % reverse("request-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [requests[0].pk]
    assert resp.context['selected_tags'] == ['tag2']


@pytest.mark.haystack
def test_tag_filter_with_shared_tag(app: DjangoTestApp, requests):
    resp = app.get("%s?selected_facets=tags_exact:tag3" % reverse("request-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [requests[1].pk, requests[0].pk]
    assert resp.context['selected_tags'] == ['tag3']


@pytest.mark.haystack
def test_tag_filter_with_multiple_tags(app: DjangoTestApp, requests):
    resp = app.get("%s?selected_facets=tags_exact:tag4&selected_facets=tags_exact:tag3" % reverse("request-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [requests[1].pk]
    assert resp.context['selected_tags'] == ['tag4', 'tag3']


@pytest.fixture
def date_filter_data():
    org = OrganizationFactory()
    request1 = RequestFactory(organization=org, slug='r1')
    request1.created = timezone.localize(datetime(2022, 3, 1))
    request1.save()
    request2 = RequestFactory(organization=org, slug='r2')
    request2.created = timezone.localize(datetime(2022, 2, 1))
    request2.save()
    request3 = RequestFactory(organization=org, slug='r3')
    request3.created = timezone.localize(datetime(2021, 12, 1))
    request3.save()
    return [request1, request2, request3]


@pytest.mark.haystack
def test_date_filter_without_query(app: DjangoTestApp, date_filter_data):
    resp = app.get(reverse('request-list'))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [
        date_filter_data[0].pk,
        date_filter_data[1].pk,
        date_filter_data[2].pk
    ]
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] is None


@pytest.mark.haystack
def test_date_filter_with_date_from(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-02-10" % reverse("request-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [date_filter_data[0].pk]
    assert resp.context['selected_date_from'] == date(2022, 2, 10)
    assert resp.context['selected_date_to'] is None


@pytest.mark.haystack
def test_date_filter_with_date_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_to=2022-02-10" % reverse("request-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [date_filter_data[1].pk, date_filter_data[2].pk]
    assert resp.context['selected_date_from'] is None
    assert resp.context['selected_date_to'] == date(2022, 2, 10)


@pytest.mark.haystack
def test_date_filter_with_dates_from_and_to(app: DjangoTestApp, date_filter_data):
    resp = app.get("%s?date_from=2022-01-01&date_to=2022-02-10" % reverse("request-list"))
    assert [int(obj.pk) for obj in resp.context['object_list']] == [date_filter_data[1].pk]
    assert resp.context['selected_date_from'] == date(2022, 1, 1)
    assert resp.context['selected_date_to'] == date(2022, 2, 10)


@pytest.mark.haystack
def test_dataset_filter_all(app: DjangoTestApp):
    organization = OrganizationFactory()
    category = CategoryFactory()
    dataset_with_all_filters = DatasetFactory(
        status=Dataset.HAS_DATA,
        tags=('tag1', 'tag2', 'tag3'),
        organization=organization,
        category=category
    )

    dataset_with_all_filters.set_current_language(settings.LANGUAGE_CODE)
    dataset_with_all_filters.slug = 'ds1'
    dataset_with_all_filters.save()
    request = RequestFactory(dataset=dataset_with_all_filters)
    request.created = timezone.localize(datetime(2022, 2, 9))
    request.save()
    
    resp = app.get(
        "%s?selected_facets=filter_status_exact:%s"
        "&selected_facets=organization_exact:%s&"
        "selected_facets=category_exact:%s&"
        "selected_facets=tags_exact:tag1&"
        "selected_facets=tags_exact:tag2&"
        "&date_from=2022-01-01&"
        "date_to=2022-02-10" % (reverse("request-list"), Dataset.HAS_DATA, organization.pk, category.pk))

    assert [int(obj.pk) for obj in resp.context['object_list']] == [request.pk]
    assert resp.context['selected_status'] == Dataset.HAS_DATA
    assert resp.context['selected_organization'] == organization.pk
    assert resp.context['selected_categories'] == [str(category.pk)]
    assert resp.context['selected_tags'] == ["tag1", "tag2"]
    assert resp.context['selected_date_from'] == date(2022, 1, 1)
    assert resp.context['selected_date_to'] == date(2022, 2, 10)


@pytest.mark.haystack
def test_dataset_filter_with_pages(app: DjangoTestApp):
    inventored_dataset = None
    for i in range(25):
        if i == 0:
            inventored_dataset = DatasetFactory(status=Dataset.INVENTORED)
            request = RequestFactory(dataset=inventored_dataset)
        else:
            RequestFactory()

    resp = app.get("%s?page=2" % (reverse('request-list')))
    assert 'page' not in resp.html.find(id="%s_id" % Dataset.INVENTORED).attrs['href']
    resp = resp.click(linkid="%s_id" % Dataset.INVENTORED)
    assert [int(obj.pk) for obj in resp.context['object_list']] == [request.pk]
    assert resp.context['selected_status'] == Dataset.INVENTORED

@pytest.mark.django_db
def test_request_create(app: DjangoTestApp):
    user = UserFactory(is_staff=True)

    app.set_user(user)
    form = app.get(reverse("request-create")).forms['request-form']
    form['title'] = "Request"
    form['description'] = "Description"
    resp = form.submit()
    added_request = Request.objects.filter(title="Request")
    assert added_request.count() == 1
    assert resp.status_code == 302
    assert resp.url == Request.objects.filter(title='Request').first().get_absolute_url()
    assert Version.objects.get_for_object(added_request.first()).count() == 1
    assert Version.objects.get_for_object(added_request.first()).first().revision.comment == Request.CREATED


@pytest.mark.django_db
def test_request_update_with_user_without_permission(app: DjangoTestApp):
    user = UserFactory()
    request = RequestFactory()

    app.set_user(user)
    resp = app.get(reverse("request-update", args=[request.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_request_update_with_permitted_user(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    request = RequestFactory(user=user)

    app.set_user(user)
    form = app.get(reverse("request-update", args=[request.pk])).forms['request-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit()
    request.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == request.get_absolute_url()
    assert request.title == "Updated title"
    assert request.description == "Updated description"
    assert Version.objects.get_for_object(request).count() == 1
    assert Version.objects.get_for_object(request).first().revision.comment == Request.EDITED


@pytest.mark.django_db
def test_request_detail_view(app: DjangoTestApp):
    dataset = DatasetFactory()
    request = RequestFactory(
        dataset_id=dataset.pk,
        is_existing=True,
        status="REJECTED",
        purpose="science,product",
        changes="format",
        format="csv, json, rdf",
    )
    structure1 = RequestStructureFactory(request_id=request.pk)
    structure2 = RequestStructureFactory(request_id=request.pk)

    resp = app.get(reverse('request-detail', args=[request.pk]))

    assert resp.context['status'] == "Atmestas"
    assert resp.context['purposes'] == ['science', 'product']
    assert resp.context['changes'] == ['format']
    assert resp.context['formats'] == ['csv', 'json', 'rdf']
    assert list(resp.context['structure']) == [structure1, structure2]


@pytest.mark.django_db
def test_request_history_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    request = RequestFactory()
    app.set_user(user)
    resp = app.get(reverse('request-history', args=[request.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_request_history_view_with_permission(app: DjangoTestApp):
    user = ManagerFactory(is_staff=True)
    request = RequestFactory(user=user, organization=user.organization)
    app.set_user(user)

    form = app.get(reverse("request-update", args=[request.pk])).forms['request-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit().follow()
    resp = resp.click(linkid="history-tab")
    assert resp.context['detail_url_name'] == 'request-detail'
    assert resp.context['history_url_name'] == 'request-history'
    assert len(resp.context['history']) == 1
    assert resp.context['history'][0]['action'] == "Redaguota"
    assert resp.context['history'][0]['user'] == user

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.requests.factories import RequestFactory, RequestStructureFactory
from vitrina.requests.models import Request
from vitrina.users.models import User


@pytest.mark.django_db
def test_request_create(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")

    app.set_user(user)
    form = app.get(reverse("request-create")).forms['request-form']
    form['title'] = "Request"
    form['description'] = "Description"
    resp = form.submit()
    assert Request.objects.filter(title="Request").count() == 1
    assert resp.status_code == 302
    assert resp.url == Request.objects.filter(title='Request').first().get_absolute_url()


@pytest.mark.django_db
def test_request_update_with_user_without_permission(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    request = RequestFactory()

    app.set_user(user)
    resp = app.get(reverse("request-update", args=[request.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_request_update_with_permitted_user(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
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
    assert resp.context['like_count'] == 0
    assert not resp.context['liked']
    assert list(resp.context['structure']) == [structure1, structure2]

import pytest
from django.contrib.admin.options import get_content_type_for_model
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.messages.models import Subscription
from vitrina.projects.models import Project
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request
from vitrina.users.factories import UserFactory


@pytest.fixture
def subscription_data():
    request = RequestFactory()
    dataset = DatasetFactory()
    project = ProjectFactory()
    user = UserFactory()
    return {
        'request': request,
        'dataset': dataset,
        'project': project,
        'user': user
    }


@pytest.mark.django_db
def test_request_subscribe_without_user(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data['request'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_request_subscribe_url_no_login(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data['request'].get_absolute_url())
    elem = resp.html.find(id='request_subscription')
    form_url = elem.find('a', {'id': 'subscribe-form'})
    assert form_url is None


@pytest.mark.django_db
def test_request_subscribe_form_no_login(app: DjangoTestApp, subscription_data):
    response = app.get(reverse('subscribe-form', kwargs={'content_type_id': get_content_type_for_model(Request).id,
                                                         'obj_id': subscription_data['request'].id,
                                                         'user_id': subscription_data['user'].id}))
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_request_subscribe_form_with_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])
    kwargs = {'content_type_id': get_content_type_for_model(Request).id,
              'obj_id': subscription_data['request'].id,
              'user_id': subscription_data['user'].id}
    form = app.get(reverse('subscribe-form', kwargs=kwargs)).forms['subscribe-form']
    form['email_subscribed'] = True
    form['request_update_sub'] = True
    resp = form.submit()

    assert resp.url == reverse('request-detail', kwargs={'pk': subscription_data['request'].id})
    assert Subscription.objects.count() == 1

    resp = app.get(subscription_data['request'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    elem = resp.html.find(id='request_subscription')
    attr = elem.find('input', {'type': 'submit'}).attrs['value']
    assert attr == "Atsisakyti prenumeratos"

    resp.forms['unsubscribe-form'].submit()
    resp = app.get(subscription_data['request'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_dataset_subscribe_without_user(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data['dataset'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_dataset_subscribe_url_no_login(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data['dataset'].get_absolute_url())
    elem = resp.html.find(id='dataset_subscription')
    form_url = elem.find('a', {'id': 'subscribe-form'})
    assert form_url is None


@pytest.mark.django_db
def test_dataset_subscribe_form_no_login(app: DjangoTestApp, subscription_data):
    response = app.get(reverse('subscribe-form', kwargs={'content_type_id': get_content_type_for_model(Dataset).id,
                                                         'obj_id': subscription_data['dataset'].id,
                                                         'user_id': subscription_data['user'].id}))
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_dataset_subscribe_form_with_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])
    kwargs = {'content_type_id': get_content_type_for_model(Dataset).id,
              'obj_id': subscription_data['dataset'].id,
              'user_id': subscription_data['user'].id}
    form = app.get(reverse('subscribe-form', kwargs=kwargs)).forms['subscribe-form']
    form['email_subscribed'] = True
    form['dataset_update_sub'] = True
    resp = form.submit()

    assert resp.url == reverse('dataset-detail', kwargs={'pk': subscription_data['dataset'].id})
    assert Subscription.objects.count() == 1

    resp = app.get(subscription_data['dataset'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    elem = resp.html.find(id='dataset_subscription')
    attr = elem.find('input', {'type': 'submit'}).attrs['value']
    assert attr == "Atsisakyti prenumeratos"

    resp.forms['unsubscribe-form'].submit()
    resp = app.get(subscription_data['dataset'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_project_subscribe_without_user(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data['project'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_project_subscribe_url_no_login(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data['project'].get_absolute_url())
    elem = resp.html.find(id='project_subscription')
    form_url = elem.find('a', {'id': 'subscribe-form'})
    assert form_url is None


@pytest.mark.django_db
def test_project_subscribe_form_no_login(app: DjangoTestApp, subscription_data):
    response = app.get(reverse('subscribe-form', kwargs={'content_type_id': get_content_type_for_model(Project).id,
                                                         'obj_id': subscription_data['project'].id,
                                                         'user_id': subscription_data['user'].id}))
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_project_subscribe_form_with_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])
    kwargs = {'content_type_id': get_content_type_for_model(Project).id,
              'obj_id': subscription_data['project'].id,
              'user_id': subscription_data['user'].id}
    form = app.get(reverse('subscribe-form', kwargs=kwargs)).forms['subscribe-form']
    form['email_subscribed'] = True
    form['project_update_sub'] = True
    resp = form.submit()

    assert resp.url == reverse('project-detail', kwargs={'pk': subscription_data['project'].id})
    assert Subscription.objects.count() == 1

    resp = app.get(subscription_data['project'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    elem = resp.html.find(id='project_subscription')
    attr = elem.find('input', {'type': 'submit'}).attrs['value']
    assert attr == "Atsisakyti prenumeratos"

    resp.forms['unsubscribe-form'].submit()
    resp = app.get(subscription_data['project'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'

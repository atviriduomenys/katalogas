import pytest
from django.contrib.contenttypes.models import ContentType
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.messages.models import Subscription
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory
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
def test_request_subscribe_with_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])

    resp = app.get(subscription_data['request'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'

    elem = resp.html.find(id='request_subscription')
    attr = elem.find('input', {'type': 'submit'}).attrs['value']
    assert attr == "Prenumeruoti"

    resp.forms['subscribe-form'].submit()
    resp = app.get(subscription_data['request'].get_absolute_url())
    assert Subscription.objects.count() == 1

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    elem = resp.html.find(id='request_subscription')
    attr = elem.find('input', {'type': 'submit'}).attrs['value']
    assert attr == "Atsisakyti prenumeratos"


@pytest.mark.django_db
def test_request_unsubscribe(app: DjangoTestApp, subscription_data):
    Subscription.objects.create(
        content_type=ContentType.objects.get_for_model(subscription_data['request']),
        object_id=subscription_data['request'].pk,
        user=subscription_data['user']
    )
    app.set_user(subscription_data['user'])
    resp = app.get(subscription_data['request'].get_absolute_url())
    assert Subscription.objects.count() == 1

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    assert resp.html.find(id='request_subscription')\
               .find('input', {'type': 'submit'}).attrs['value'] == "Atsisakyti prenumeratos"
    resp.forms['subscribe-form'].submit()
    resp = app.get(subscription_data['request'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'

    assert resp.html.find(id='request_subscription').find('input', {'type': 'submit'}).attrs['value'] == "Prenumeruoti"


@pytest.mark.django_db
def test_dataset_subscribe_without_user(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data['dataset'].get_absolute_url())
    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_dataset_subscribe_with_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])
    resp = app.get(subscription_data['dataset'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'

    assert resp.html.find(id='dataset_subscription')\
               .find('input', {'type': 'submit'}).attrs['value'] == "Prenumeruoti"
    resp.forms['subscribe-form'].submit()
    resp = app.get(subscription_data['dataset'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    assert resp.html.find(id='dataset_subscription')\
               .find('input', {'type': 'submit'}).attrs['value'] == "Atsisakyti prenumeratos"


@pytest.mark.django_db
def test_dataset_unsubscribe(app: DjangoTestApp, subscription_data):
    Subscription.objects.create(
        content_type=ContentType.objects.get_for_model(subscription_data['dataset']),
        object_id=subscription_data['dataset'].pk,
        user=subscription_data['user']
    )
    app.set_user(subscription_data['user'])
    resp = app.get(subscription_data['dataset'].get_absolute_url())
    assert Subscription.objects.count() == 1

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    assert resp.html.find(id='dataset_subscription')\
               .find('input', {'type': 'submit'}).attrs['value'] == "Atsisakyti prenumeratos"
    resp.forms['subscribe-form'].submit()
    resp = app.get(subscription_data['dataset'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'

    assert resp.html.find(id='dataset_subscription').find('input', {'type': 'submit'}).attrs['value'] == "Prenumeruoti"


@pytest.mark.django_db
def test_project_subscribe_without_user(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data['project'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_project_subscribe_with_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])
    resp = app.get(subscription_data['project'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'

    assert resp.html.find(id='project_subscription')\
               .find('input', {'type': 'submit'}).attrs['value'] == "Prenumeruoti"
    resp.forms['subscribe-form'].submit()
    resp = app.get(subscription_data['project'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    assert resp.html.find(id='project_subscription')\
               .find('input', {'type': 'submit'}).attrs['value'] == "Atsisakyti prenumeratos"


@pytest.mark.django_db
def test_project_unsubscribe(app: DjangoTestApp, subscription_data):
    Subscription.objects.create(
        content_type=ContentType.objects.get_for_model(subscription_data['project']),
        object_id=subscription_data['project'].pk,
        user=subscription_data['user']
    )
    app.set_user(subscription_data['user'])
    resp = app.get(subscription_data['project'].get_absolute_url())
    assert Subscription.objects.count() == 1

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    assert resp.html.find(id='project_subscription')\
               .find('input', {'type': 'submit'}).attrs['value'] == "Atsisakyti prenumeratos"
    resp.forms['subscribe-form'].submit()
    resp = app.get(subscription_data['project'].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'

    assert resp.html.find(id='project_subscription').find('input', {'type': 'submit'}).attrs['value'] == "Prenumeruoti"


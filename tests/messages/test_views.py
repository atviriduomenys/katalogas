import pytest
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.projects.models import Project
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request
from vitrina.users.factories import UserFactory


@pytest.fixture
def subscription_data():
    org1 = OrganizationFactory()
    org2 = OrganizationFactory.build()
    org1.add_child(instance=org2)
    request = RequestFactory()
    dataset = DatasetFactory()
    project = ProjectFactory()
    user = UserFactory(organization=org1)
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

    assert len(mail.outbox) == 1

    resp = app.get(subscription_data['request'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    elem = resp.html.find(id='request_subscription')
    attr = elem.find('input', {'type': 'submit'}).attrs['value']
    assert attr == "Atsisakyti prenumeratos"

    resp.forms['unsubscribe-form'].submit()
    resp = app.get(subscription_data['request'].get_absolute_url())
    assert Subscription.objects.count() == 0

    assert len(mail.outbox) == 2

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_request_comment_subscription_email(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])
    kwargs = {'content_type_id': get_content_type_for_model(Request).id,
              'obj_id': subscription_data['request'].id,
              'user_id': subscription_data['user'].id}
    form = app.get(reverse('subscribe-form', kwargs=kwargs)).forms['subscribe-form']
    form['email_subscribed'] = True
    form['request_update_sub'] = True
    form['request_comments_sub'] = True
    resp = form.submit()

    assert resp.url == reverse('request-detail', kwargs={'pk': subscription_data['request'].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    comment_user = UserFactory()
    app.set_user(comment_user)
    ct = ContentType.objects.get_for_model(subscription_data['request'])
    form = app.get(subscription_data['request'].get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['body'] = "Test comment"
    form.submit()
    created_comment = Comment.objects.filter(content_type=ct, object_id=subscription_data['request'].pk)
    assert created_comment.count() == 1
    assert Subscription.objects.count() == 2
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_request_update_subscription_email(app: DjangoTestApp, subscription_data):
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

    assert len(mail.outbox) == 1

    staff_user = UserFactory(is_staff=True)
    app.set_user(staff_user)
    request = subscription_data['request']
    form = app.get(reverse("request-update", args=[request.pk])).forms['request-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit()
    request.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == request.get_absolute_url()
    assert len(mail.outbox) == 2


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

    assert len(mail.outbox) == 1

    resp = app.get(subscription_data['dataset'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    elem = resp.html.find(id='dataset_subscription')
    attr = elem.find('input', {'type': 'submit'}).attrs['value']
    assert attr == "Atsisakyti prenumeratos"

    resp.forms['unsubscribe-form'].submit()
    resp = app.get(subscription_data['dataset'].get_absolute_url())
    assert Subscription.objects.count() == 0

    assert len(mail.outbox) == 2

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_dataset_comment_subscription_email(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])
    kwargs = {'content_type_id': get_content_type_for_model(Dataset).id,
              'obj_id': subscription_data['dataset'].id,
              'user_id': subscription_data['user'].id}
    form = app.get(reverse('subscribe-form', kwargs=kwargs)).forms['subscribe-form']
    form['email_subscribed'] = True
    form['dataset_update_sub'] = True
    form['dataset_comments_sub'] = True
    resp = form.submit()

    assert resp.url == reverse('dataset-detail', kwargs={'pk': subscription_data['dataset'].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    comment_user = UserFactory()
    app.set_user(comment_user)
    ct = ContentType.objects.get_for_model(subscription_data['dataset'])
    form = app.get(subscription_data['dataset'].get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['body'] = "Test comment"
    form.submit()
    created_comment = Comment.objects.filter(content_type=ct, object_id=subscription_data['dataset'].pk)
    assert created_comment.count() == 1
    assert Subscription.objects.count() == 2
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_dataset_update_subscription_email(app: DjangoTestApp, subscription_data):
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

    assert len(mail.outbox) == 1

    staff_user = UserFactory(is_staff=True)
    app.set_user(staff_user)
    dataset = subscription_data['dataset']
    form = app.get(reverse("dataset-change", args=[dataset.pk])).forms['dataset-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert len(mail.outbox) == 3


@pytest.mark.django_db
def test_dataset_update_global_org_subscription_email(app: DjangoTestApp, subscription_data):
    global_sub_user = subscription_data['user']
    app.set_user(global_sub_user)
    Subscription.objects.create(
        user=global_sub_user,
        content_type=ContentType.objects.get_for_model(Organization),
        sub_type=Subscription.ORGANIZATION,
        dataset_update_sub=True
    )
    assert Subscription.objects.count() == 1

    staff_user = UserFactory(is_staff=True)
    app.set_user(staff_user)
    dataset = subscription_data['dataset']
    form = app.get(reverse("dataset-change", args=[dataset.pk])).forms['dataset-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert len(mail.outbox) == 1


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

    assert len(mail.outbox) == 1

    resp = app.get(subscription_data['project'].get_absolute_url())

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '1'

    elem = resp.html.find(id='project_subscription')
    attr = elem.find('input', {'type': 'submit'}).attrs['value']
    assert attr == "Atsisakyti prenumeratos"

    resp.forms['unsubscribe-form'].submit()
    resp = app.get(subscription_data['project'].get_absolute_url())
    assert Subscription.objects.count() == 0

    assert len(mail.outbox) == 2

    elem = resp.html.find(id='number-of-subscribers')
    assert elem.get_text().strip() == '0'


@pytest.mark.django_db
def test_project_comment_subscription_email(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])
    kwargs = {'content_type_id': get_content_type_for_model(Project).id,
              'obj_id': subscription_data['project'].id,
              'user_id': subscription_data['user'].id}
    form = app.get(reverse('subscribe-form', kwargs=kwargs)).forms['subscribe-form']
    form['email_subscribed'] = True
    form['project_update_sub'] = True
    form['project_comments_sub'] = True
    resp = form.submit()

    assert resp.url == reverse('project-detail', kwargs={'pk': subscription_data['project'].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    comment_user = UserFactory()
    app.set_user(comment_user)
    ct = ContentType.objects.get_for_model(subscription_data['project'])
    form = app.get(subscription_data['project'].get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['body'] = "Test comment"
    form.submit()
    created_comment = Comment.objects.filter(content_type=ct, object_id=subscription_data['project'].pk)
    assert created_comment.count() == 1
    assert Subscription.objects.count() == 2
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_project_update_subscription_email(app: DjangoTestApp, subscription_data):
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

    assert len(mail.outbox) == 1

    staff_user = UserFactory(is_staff=True)
    app.set_user(staff_user)
    project = subscription_data['project']

    form = app.get(reverse("project-update", args=[project.pk])).forms['project-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit()

    project.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == project.get_absolute_url()
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_auto_subscribe_for_comment_and_reply_mail(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data['user'])
    ct = ContentType.objects.get_for_model(subscription_data['dataset'])
    form = app.get(subscription_data['dataset'].get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['body'] = "Test comment"
    form.submit()
    created_comment = Comment.objects.filter(content_type=ct, object_id=subscription_data['dataset'].pk)
    assert created_comment.count() == 1
    assert Subscription.objects.count() == 1
    assert len(mail.outbox) == 0

    reply_user = UserFactory()
    comment = created_comment.first()
    app.set_user(reply_user)
    form = app.get(comment.content_object.get_absolute_url()).forms['reply-form']
    form['is_public'] = True
    form['body'] = "Test reply"
    resp = form.submit().follow()
    comments = Comment.objects.filter(content_type=comment.content_type, object_id=comment.object_id)
    reply = Comment.objects.filter(content_type=comment.content_type, parent=comment).first()
    assert comments.count() == 2
    assert comment in list(resp.context['comments'])[0]
    assert [reply] == list(resp.context['comments'])[0][1]
    assert len(mail.outbox) == 1

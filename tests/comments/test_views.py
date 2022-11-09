import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina.classifiers.factories import FrequencyFactory
from vitrina.comments.factories import CommentFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_comment_without_user(app: DjangoTestApp):
    dataset = DatasetFactory()
    url = reverse('comment', kwargs={
        'content_type_id': ContentType.objects.get_for_model(dataset).pk,
        'object_id': dataset.pk
    })
    resp = app.get(url)
    assert resp.status_code == 302
    assert resp.url == "%s?next=%s" % (reverse('login'), url)


@pytest.mark.django_db
def test_comment_is_not_public(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).forms['comment-form']
    form['is_public'] = False
    form['body'] = "Test comment"
    resp = form.submit().follow()
    assert Comment.objects.filter(content_type=ct, object_id=dataset.pk).count() == 1
    assert list(resp.context['comments']) == []


@pytest.mark.django_db
def test_comment_is_public(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['body'] = "Test comment"
    resp = form.submit().follow()
    created_comment = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert created_comment.count() == 1
    assert list(resp.context['comments']) == [created_comment.first()]
    assert created_comment.first().type == Comment.USER


@pytest.mark.django_db
def test_dataset_comment_with_register_request(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    frequency = FrequencyFactory()
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['register_request'] = True
    form['increase_frequency'] = frequency
    form['body'] = "Test comment"
    resp = form.submit().follow()
    created_request = Request.objects.filter(dataset_id=dataset.pk)
    created_comment = Comment.objects.filter(content_type=ct, object_id=dataset.pk)

    assert created_comment.count() == 1
    assert list(resp.context['comments']) == [created_comment.first()]
    assert created_comment.first().type == Comment.REQUEST
    assert created_comment.first().rel_content_type == ContentType.objects.get_for_model(Request)
    assert created_comment.first().rel_object_id == created_request.first().pk

    assert created_request.count() == 1
    assert created_request.first().title == dataset.title
    assert created_request.first().description == created_comment.first().body
    assert created_request.first().organization == dataset.organization
    assert created_request.first().periodicity == frequency.title
    assert Version.objects.get_for_object(created_request.first()).count() == 1
    assert Version.objects.get_for_object(created_request.first()).first().revision.comment == Request.CREATED


@pytest.mark.django_db
def test_request_comment_with_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    request = RequestFactory()
    ct = ContentType.objects.get_for_model(request)
    app.set_user(user)
    form = app.get(request.get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['status'] = Comment.APPROVED
    form['body'] = "Test comment"
    resp = form.submit().follow()
    created_comment = Comment.objects.filter(content_type=ct, object_id=request.pk)
    assert created_comment.count() == 1
    assert list(resp.context['comments']) == [created_comment.first()]
    assert created_comment.first().type == Comment.STATUS
    assert created_comment.first().status == Comment.APPROVED
    assert Version.objects.get_for_object(request).count() == 1
    assert Version.objects.get_for_object(request).first().revision.comment == Request.STATUS_CHANGED


@pytest.mark.django_db
def test_reply_without_user(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk)
    url = reverse('comment', kwargs={
        'content_type_id': comment.content_type.pk,
        'object_id': comment.object_id
    })
    resp = app.get(url)
    assert resp.status_code == 302
    assert resp.url == "%s?next=%s" % (reverse('login'), url)


@pytest.mark.django_db
def test_reply_is_not_public(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk)
    app.set_user(user)
    form = app.get(comment.content_object.get_absolute_url()).forms['reply-form']
    form['is_public'] = False
    form['body'] = "Test comment"
    resp = form.submit().follow()
    comments = Comment.objects.filter(content_type=comment.content_type, object_id=comment.object_id)
    assert comments.count() == 2
    assert list(resp.context['comments']) == [comment]


@pytest.mark.django_db
def test_reply_is_public(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk)
    app.set_user(user)
    form = app.get(comment.content_object.get_absolute_url()).forms['reply-form']
    form['is_public'] = True
    form['body'] = "Test comment"
    resp = form.submit().follow()
    comments = Comment.objects.filter(content_type=comment.content_type, object_id=comment.object_id)
    assert comments.count() == 2
    assert list(resp.context['comments']) == [comment]
    assert list(resp.context['comments'][0].descendants()) == [comments.filter(parent_id__isnull=False).first()]

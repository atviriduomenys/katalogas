import json
from unittest.mock import patch, Mock

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina.classifiers.factories import FrequencyFactory
from vitrina.comments.factories import CommentFactory
from vitrina.comments.models import Comment
from vitrina.requests.models import RequestAssignment
from vitrina.datasets.factories import DatasetFactory
from vitrina.requests.factories import RequestFactory, RequestAssignmentFactory
from vitrina.requests.models import Request
from vitrina.structure.factories import PropertyFactory, ModelFactory, MetadataFactory
from vitrina.users.factories import UserFactory
from vitrina.orgs.factories import OrganizationFactory

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
def test_comment_is_not_public_user_staff(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).forms['comment-form']
    form['is_public'] = False
    form['body'] = "Test comment"
    resp = form.submit().follow()
    created_comment = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert Comment.objects.filter(content_type=ct, object_id=dataset.pk).count() == 1
    assert created_comment.first() in list(resp.context['comments'])[0]


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
    assert created_comment.first() in list(resp.context['comments'])[0]
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
    created_request = Request.objects.filter(requestobject__object_id=dataset.pk, requestobject__content_type=ct)
    created_comment = Comment.objects.filter(content_type=ct, object_id=dataset.pk)

    assert created_comment.count() == 1
    assert created_comment.first() in list(resp.context['comments'])[0]
    assert created_comment.first().type == Comment.REQUEST
    assert created_comment.first().rel_content_type == ContentType.objects.get_for_model(Request)
    assert created_comment.first().rel_object_id == created_request.first().pk

    assert created_request.count() == 1
    assert created_request.first().title == dataset.title
    assert created_request.first().description == created_comment.first().body
    assert created_request.first().requestassignment_set.first().organization == dataset.organization
    assert created_request.first().periodicity == frequency.title
    assert Version.objects.get_for_object(created_request.first()).count() == 1
    assert Version.objects.get_for_object(created_request.first()).first().revision.comment == Request.CREATED


@pytest.mark.django_db
def test_request_comment_with_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    request = RequestFactory(status=Request.CREATED)
    org = OrganizationFactory()
    user.organization = org
    ra = RequestAssignmentFactory(
        organization=org,
        request=request,
        status=Request.CREATED
    )
    app.set_user(user)
    form = app.get(request.get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['status'] = Request.APPROVED
    form['body'] = "Test comment"
    resp = form.submit().follow()
    assert resp.html.find(id='request_status').text == 'Įvertintas' or resp.html.find(id='request_status').text == 'Approved'


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
    assert comment in list(resp.context['comments'])[0]


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
    reply = Comment.objects.filter(content_type=comment.content_type, parent=comment).first()
    assert comments.count() == 2
    assert comment in list(resp.context['comments'])[0]
    assert reply in list(resp.context['comments'])[1]


@pytest.mark.django_db
def test_reply_for_reply(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk)
    reply = CommentFactory(parent=comment, content_type=ct, object_id=dataset.pk)

    app.set_user(user)
    form = app.get(comment.content_object.get_absolute_url()).forms['reply-form']
    form['is_public'] = True
    form['body'] = "Test reply"
    resp = form.submit().follow()
    comments = Comment.objects.filter(content_type=comment.content_type, object_id=comment.object_id)
    new_reply = Comment.objects.filter(content_type=comment.content_type, parent=reply).first()
    assert comments.count() == 3
    assert reply in list(resp.context['comments'])[1]
    assert new_reply in list(resp.context['comments'])[2]


@pytest.mark.django_db
def test_model_comment_with_register_request(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    ct = ContentType.objects.get_for_model(model)
    app.set_user(user)
    form = app.get(model.get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['register_request'] = True
    form['body'] = "Test comment"
    resp = form.submit().follow()
    created_request = Request.objects.filter(requestobject__object_id=model.pk, requestobject__content_type=ct)
    created_comment = Comment.objects.filter(content_type=ct, object_id=model.pk)

    assert created_comment.count() == 1
    assert created_comment.first() in list(resp.context['comments'])[0]
    assert created_comment.first().type == Comment.REQUEST
    assert created_comment.first().rel_content_type == ContentType.objects.get_for_model(Request)
    assert created_comment.first().rel_object_id == created_request.first().pk

    assert created_request.count() == 1
    assert created_request.first().title == model.title
    assert created_request.first().description == created_comment.first().body
    assert Version.objects.get_for_object(created_request.first()).count() == 1
    assert Version.objects.get_for_object(created_request.first()).first().revision.comment == Request.CREATED


@pytest.mark.django_db
def test_property_comment_with_register_request(app: DjangoTestApp):
    user = UserFactory()
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
        title="Test prop"
    )
    ct = ContentType.objects.get_for_model(prop)
    app.set_user(user)
    form = app.get(prop.get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['register_request'] = True
    form['body'] = "Test comment"
    resp = form.submit().follow()
    created_request = Request.objects.filter(requestobject__object_id=prop.pk, requestobject__content_type=ct)
    created_comment = Comment.objects.filter(content_type=ct, object_id=prop.pk)

    assert created_comment.count() == 1
    assert created_comment.first() in list(resp.context['comments'])[0]
    assert created_comment.first().type == Comment.REQUEST
    assert created_comment.first().rel_content_type == ContentType.objects.get_for_model(Request)
    assert created_comment.first().rel_object_id == created_request.first().pk

    assert created_request.count() == 1
    assert created_request.first().title == prop.title
    assert created_request.first().description == created_comment.first().body
    assert Version.objects.get_for_object(created_request.first()).count() == 1
    assert Version.objects.get_for_object(created_request.first()).first().revision.comment == Request.CREATED


@pytest.mark.django_db
def test_object_data_comment_with_register_request(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    model = ModelFactory()
    dataset = model.dataset
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    with patch('vitrina.structure.services.requests.get') as mock_get:
        data = {
            '_id': 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
            'prop': "test 1",
        }
        mock_get.return_value = Mock(content=json.dumps(data))
        form = app.get(reverse('object-data', args=[
            dataset.pk,
            model.name,
            'c7d66fa2-a880-443d-8ab5-2ab7f9c79886'
        ])).forms['comment-form']
        form['is_public'] = True
        form['register_request'] = True
        form['body'] = "Test comment"
        resp = form.submit().follow()
        created_request = Request.objects.filter(requestobject__external_object_id='c7d66fa2-a880-443d-8ab5-2ab7f9c79886')
        created_comment = Comment.objects.filter(external_object_id='c7d66fa2-a880-443d-8ab5-2ab7f9c79886')

        assert created_comment.count() == 1
        assert created_comment.first() in list(resp.context['comments'])[0]
        assert created_comment.first().type == Comment.REQUEST
        assert created_comment.first().rel_content_type == ContentType.objects.get_for_model(Request)
        assert created_comment.first().rel_object_id == created_request.first().pk

        assert created_request.count() == 1
        assert created_request.first().title == 'c7d66fa2-a880-443d-8ab5-2ab7f9c79886'
        assert created_request.first().description == created_comment.first().body
        assert Version.objects.get_for_object(created_request.first()).count() == 1
        assert Version.objects.get_for_object(created_request.first()).first().revision.comment == Request.CREATED


@pytest.mark.django_db
def test_comment_on_non_public_dataset_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    resp = app.post(reverse("comment", args=[ct.pk, dataset.pk]), {
        'is_public': True,
        'body': "Test comment"
    }, expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_reply_on_non_public_dataset_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(
        content_type=ct,
        object_id=dataset.pk
    )
    app.set_user(user)
    resp = app.post(reverse("reply", args=[ct.pk, dataset.pk, comment.pk]), {
        'is_public': True,
        'body': "Test comment"
    }, expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_object_data_comment_on_non_public_dataset_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )

    resp = app.post(reverse('external-comment', args=[
        dataset.pk,
        model.name,
        'c7d66fa2-a880-443d-8ab5-2ab7f9c79886'
    ]), {
        'is_public': True,
        'body': "Test comment"
    }, expect_errors=True)

    assert resp.status_code == 403


@pytest.mark.django_db
def test_object_data_reply_on_non_public_dataset_without_permission(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    dataset = DatasetFactory(is_public=False)
    model = ModelFactory(dataset=dataset)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel"
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset"
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name='prop',
        type='string',
    )
    comment = CommentFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        external_object_id='c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
        external_content_type=model.full_name
    )

    resp = app.post(reverse('external-reply', args=[
        model.name,
        'c7d66fa2-a880-443d-8ab5-2ab7f9c79886',
        comment.pk,
    ]), {
        'is_public': True,
        'body': "Test comment",
        'dataset_id': dataset.pk
    }, expect_errors=True)

    assert resp.status_code == 403

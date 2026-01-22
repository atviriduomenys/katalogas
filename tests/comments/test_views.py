import pytest
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.urls import reverse, resolve
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina.classifiers.factories import FrequencyFactory
from vitrina.comments.factories import CommentFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization, Representative
from vitrina.projects.factories import ProjectFactory
from vitrina.projects.models import Project
from vitrina.requests.factories import RequestFactory, RequestAssignmentFactory
from vitrina.requests.models import Request
from vitrina.structure.factories import PropertyFactory, ModelFactory, MetadataFactory, VersionFactory
from vitrina.users.factories import UserFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.utils import RevisionComment, RevisionSource


@pytest.mark.django_db
def test_comment_without_user(app: DjangoTestApp):
    dataset = DatasetFactory()
    url = reverse(
        "comment", kwargs={"content_type_id": ContentType.objects.get_for_model(dataset).pk, "object_id": dataset.pk}
    )
    resp = app.get(url)
    assert resp.status_code == 302
    assert resp.url == "%s?next=%s" % (reverse("login"), url)


@pytest.mark.django_db
def test_comment_is_not_public_user_staff(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).follow().forms["comment-form"]
    form["is_public"] = False
    form["body"] = "Test comment"
    resp = form.submit().follow().follow()  # comment form → dataset view → versioned dataset view
    created_comment = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert Comment.objects.filter(content_type=ct, object_id=dataset.pk).count() == 1
    assert created_comment.first() in list(resp.context["comments"])[0]


@pytest.mark.django_db
def test_comment_is_public(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).follow().forms["comment-form"]
    form["is_public"] = True
    form["body"] = "Test comment"
    resp = form.submit().follow().follow()  # comment form → dataset view → versioned dataset view
    created_comment = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert created_comment.count() == 1
    assert created_comment.first() in list(resp.context["comments"])[0]
    assert created_comment.first().type == Comment.USER


@pytest.mark.django_db
def test_dataset_comment_with_register_request(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    frequency = FrequencyFactory()
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).follow().forms["comment-form"]
    match = resolve(form.action)
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="comment",
        http_method="POST",
        path=form.action,
        args=list(match.args),
        kwargs=match.kwargs,
    )
    form["is_public"] = True
    form["register_request"] = True
    form["increase_frequency"] = frequency
    form["request_title"] = "Test request title"
    form["body"] = "Test comment"
    resp = form.submit().follow().follow()  # comment form → dataset view → versioned dataset view
    created_request = Request.objects.filter(requestobject__object_id=dataset.pk, requestobject__content_type=ct)
    created_comment = Comment.objects.filter(content_type=ct, object_id=dataset.pk)

    assert created_comment.count() == 1
    assert created_comment.first() in list(resp.context["comments"])[0]
    assert created_comment.first().type == Comment.REQUEST
    assert created_comment.first().rel_content_type == ContentType.objects.get_for_model(Request)
    assert created_comment.first().rel_object_id == created_request.first().pk

    assert created_request.count() == 1
    assert created_request.first().title == "Test request title"
    assert created_request.first().description == created_comment.first().body
    assert created_request.first().requestassignment_set.first().organization == dataset.organization
    assert created_request.first().periodicity == frequency.title
    assert Version.objects.get_for_object(created_request.first()).count() == 1
    assert (
        Version.objects.get_for_object(created_request.first()).first().revision.comment == revision_comment.to_json()
    )


@pytest.mark.django_db
def test_request_comment_with_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    request = RequestFactory(status=Request.CREATED)
    org = OrganizationFactory()
    user.organization = org
    RequestAssignmentFactory(organization=org, request=request, status=Request.CREATED)
    app.set_user(user)
    form = app.get(request.get_absolute_url()).forms["comment-form"]
    form["is_public"] = True
    form["status"] = Request.APPROVED
    form["body"] = "Test comment"
    resp = form.submit().follow()
    assert (
        resp.html.find(id="request_status").text == "Įvertintas"
        or resp.html.find(id="request_status").text == "Approved"
    )


@pytest.mark.django_db
def test_reply_without_user(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk)
    url = reverse("comment", kwargs={"content_type_id": comment.content_type.pk, "object_id": comment.object_id})
    resp = app.get(url)
    assert resp.status_code == 302
    assert resp.url == "%s?next=%s" % (reverse("login"), url)


@pytest.mark.django_db
def test_reply_is_not_public(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk)
    app.set_user(user)
    form = app.get(comment.content_object.get_absolute_url()).follow().forms[f"reply-form-{comment.pk}"]
    form["body"] = "test"
    form["is_public"] = False
    form.submit()

    reply = Comment.objects.filter(parent=comment).first()
    assert reply is not None
    assert reply.is_public is False


@pytest.mark.django_db
def test_reply_is_public(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk)
    app.set_user(user)
    form = app.get(comment.content_object.get_absolute_url()).follow().forms[f"reply-form-{comment.pk}"]
    form["is_public"] = True
    form["body"] = "Test comment"
    resp = form.submit().follow().follow()  # comment form → dataset view → versioned dataset view
    comments = Comment.objects.filter(content_type=comment.content_type, object_id=comment.object_id)
    reply = Comment.objects.filter(content_type=comment.content_type, parent=comment).first()
    assert comments.count() == 2
    assert comment in list(resp.context["comments"])[0]
    assert reply in list(resp.context["comments"])[1]


@pytest.mark.django_db
def test_reply_for_reply(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk)
    reply = CommentFactory(parent=comment, content_type=ct, object_id=dataset.pk)

    app.set_user(user)
    form = app.get(comment.content_object.get_absolute_url()).follow().forms[f"reply-form-{comment.pk}"]
    form.fields["is_public"][0].value = True
    form.fields["body"][0].value = "Test reply"
    form.submit()

    new_reply = Comment.objects.filter(parent=comment).exclude(pk=reply.pk).first()
    assert new_reply is not None
    assert new_reply.body == "Test reply"


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
        name="test/dataset",
    )
    ct = ContentType.objects.get_for_model(model)
    app.set_user(user)
    form = app.get(model.get_absolute_url()).forms["comment-form"]
    match = resolve(form.action)
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="comment",
        http_method="POST",
        path=form.action,
        args=list(match.args),
        kwargs=match.kwargs,
    )
    form["is_public"] = True
    form["register_request"] = True
    form["body"] = "Test comment"
    resp = form.submit().follow()
    created_request = Request.objects.filter(requestobject__object_id=model.pk, requestobject__content_type=ct)
    created_comment = Comment.objects.filter(content_type=ct, object_id=model.pk)

    assert created_comment.count() == 1
    assert created_comment.first() in list(resp.context["comments"])[0]
    assert created_comment.first().type == Comment.REQUEST
    assert created_comment.first().rel_content_type == ContentType.objects.get_for_model(Request)
    assert created_comment.first().rel_object_id == created_request.first().pk

    assert created_request.count() == 1
    assert created_request.first().title == model.title
    assert created_request.first().description == created_comment.first().body
    assert Version.objects.get_for_object(created_request.first()).count() == 1
    assert (
        Version.objects.get_for_object(created_request.first()).first().revision.comment == revision_comment.to_json()
    )


@pytest.mark.django_db
def test_property_comment_with_register_request(app: DjangoTestApp):
    user = UserFactory()
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
        name="test/dataset",
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        title="Test prop",
    )
    ct = ContentType.objects.get_for_model(prop)
    app.set_user(user)
    form = app.get(prop.get_absolute_url()).forms["comment-form"]
    match = resolve(form.action)
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="comment",
        http_method="POST",
        path=form.action,
        args=list(match.args),
        kwargs=match.kwargs,
    )
    form["is_public"] = True
    form["register_request"] = True
    form["body"] = "Test comment"
    resp = form.submit().follow()
    created_request = Request.objects.filter(requestobject__object_id=prop.pk, requestobject__content_type=ct)
    created_comment = Comment.objects.filter(content_type=ct, object_id=prop.pk)

    assert created_comment.count() == 1
    assert created_comment.first() in list(resp.context["comments"])[0]
    assert created_comment.first().type == Comment.REQUEST
    assert created_comment.first().rel_content_type == ContentType.objects.get_for_model(Request)
    assert created_comment.first().rel_object_id == created_request.first().pk

    assert created_request.count() == 1
    assert created_request.first().title == prop.title
    assert created_request.first().description == created_comment.first().body
    assert Version.objects.get_for_object(created_request.first()).count() == 1
    assert (
        Version.objects.get_for_object(created_request.first()).first().revision.comment == revision_comment.to_json()
    )


@pytest.mark.django_db
def test_object_data_comment_with_register_request(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)
    metadata_version = VersionFactory()
    model = ModelFactory(dataset=metadata_version.dataset, metadata_version=metadata_version)
    dataset = metadata_version.dataset
    model_metadata = MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
        metadata_version=metadata_version,
    )
    prop = PropertyFactory(model=model, metadata_version=metadata_version)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        metadata_version=metadata_version,
    )

    form = app.get(
        reverse("object-data", args=[dataset.pk, model_metadata.metadata_version.pk, model.name, model_metadata.uuid])
    ).forms["comment-form"]
    match = resolve(form.action)
    revision_comment = RevisionComment(
        source=RevisionSource.VIEW,
        action="external-comment",
        http_method="POST",
        path=form.action,
        args=list(match.args),
        kwargs=match.kwargs,
    )
    form["is_public"] = True
    form["register_request"] = True
    form["body"] = "Test comment"
    resp = form.submit().follow()
    created_request = Request.objects.filter(requestobject__external_object_id=model_metadata.uuid)
    created_comment = Comment.objects.filter(external_object_id=model_metadata.uuid)

    assert created_comment.count() == 1
    assert created_comment.first() in list(resp.context["comments"])[0]
    assert created_comment.first().type == Comment.REQUEST
    assert created_comment.first().rel_content_type == ContentType.objects.get_for_model(Request)
    assert created_comment.first().rel_object_id == created_request.first().pk

    assert created_request.count() == 1
    assert created_request.first().title == str(model_metadata.uuid)
    assert created_request.first().description == created_comment.first().body
    assert Version.objects.get_for_object(created_request.first()).count() == 1
    assert (
        Version.objects.get_for_object(created_request.first()).first().revision.comment == revision_comment.to_json()
    )


@pytest.mark.django_db
def test_comment_on_non_public_dataset_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    resp = app.post(
        reverse("comment", args=[ct.pk, dataset.pk]), {"is_public": True, "body": "Test comment"}, expect_errors=True
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_reply_on_non_public_dataset_without_permission(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk)
    app.set_user(user)
    resp = app.post(
        reverse("reply", args=[ct.pk, dataset.pk, comment.pk]),
        {"is_public": True, "body": "Test comment"},
        expect_errors=True,
    )
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
        name="test/dataset/TestModel",
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset",
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
    )

    resp = app.post(
        reverse("external-comment", args=[dataset.pk, model.name, "c7d66fa2-a880-443d-8ab5-2ab7f9c79886"]),
        {"is_public": True, "body": "Test comment"},
        expect_errors=True,
    )

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
        name="test/dataset/TestModel",
    )
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset",
    )
    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
    )
    comment = CommentFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        external_object_id="c7d66fa2-a880-443d-8ab5-2ab7f9c79886",
        external_content_type=model.full_name,
    )

    resp = app.post(
        reverse(
            "external-reply",
            args=[
                model.name,
                "c7d66fa2-a880-443d-8ab5-2ab7f9c79886",
                comment.pk,
            ],
        ),
        {"is_public": True, "body": "Test comment", "dataset_id": dataset.pk},
        expect_errors=True,
    )

    assert resp.status_code == 403


@pytest.mark.django_db
def test_view_author_comment_not_public(app: DjangoTestApp):
    user = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).follow().forms["comment-form"]
    form["is_public"] = False
    form["body"] = "Test comment"
    resp = form.submit().follow().follow()  # comment form → dataset view → versioned dataset view
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk, user=user)
    assert comments.count() == 1
    assert [comment for comment, _, _ in resp.context["comments"]] == list(comments)


@pytest.mark.django_db
def test_view_comment_not_public_without_permission(app: DjangoTestApp):
    user = UserFactory()
    user2 = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).follow().forms["comment-form"]
    form["is_public"] = False
    form["body"] = "Test comment"
    form.submit()
    app.set_user(user2)
    resp = app.get(dataset.get_absolute_url()).follow()
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk, user=user)
    assert comments.count() == 1
    assert [comment for comment, _, _ in resp.context["comments"]] == []


@pytest.mark.django_db
def test_view_comment_not_public_with_permission(app: DjangoTestApp):
    user = UserFactory()
    user2 = UserFactory()
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(user=user2, content_type=ct, object_id=dataset.pk)
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).follow().forms["comment-form"]
    form["is_public"] = False
    form["body"] = "Test comment"
    form.submit()
    app.set_user(user2)
    resp = app.get(dataset.get_absolute_url()).follow()
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk, user=user)
    assert comments.count() == 1
    assert [comment for comment, _, _ in resp.context["comments"]] == list(comments)


@pytest.mark.django_db
def test_view_reply_to_author_comment_not_public(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False)
    CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=comment)
    app.set_user(comment.user)
    resp = app.get(dataset.get_absolute_url()).follow()
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert comments.count() == 2
    assert sorted([comment.pk for comment, _, _ in resp.context["comments"]]) == sorted(
        list(comments.values_list("pk", flat=True))
    )


@pytest.mark.django_db
def test_view_reply_to_comment_not_public_without_permission(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False)
    CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=comment)
    resp = app.get(dataset.get_absolute_url()).follow()
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert comments.count() == 2
    assert sorted([comment.pk for comment, _, _ in resp.context["comments"]]) == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        (Representative.OPEN_DATA_MANAGER),
        (Representative.RESOURCE_MANAGER),
    ],
)
def test_view_reply_to_comment_not_public_with_resource_permission(app: DjangoTestApp, role: str):
    dataset = DatasetFactory()
    organization = OrganizationFactory(kind=Organization.GOV)
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False)
    CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=comment)
    representative = RepresentativeFactory(
        content_type=ct, object_id=dataset.pk, user=UserFactory(organization=organization), role=role
    )
    app.set_user(representative.user)
    resp = app.get(dataset.get_absolute_url()).follow()
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert comments.count() == 2
    assert sorted([comment.pk for comment, _, _ in resp.context["comments"]]) == sorted(
        list(comments.values_list("pk", flat=True))
    )


@pytest.mark.django_db
def test_view_reply_to_author_reply_not_public(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=True)
    reply = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=comment)
    CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=reply)
    app.set_user(reply.user)
    resp = app.get(dataset.get_absolute_url()).follow()
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert comments.count() == 3
    assert sorted([comment.pk for comment, _, _ in resp.context["comments"]]) == sorted(
        list(comments.values_list("pk", flat=True))
    )


@pytest.mark.django_db
def test_view_reply_to_author_not_public_without_permission(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=True)
    reply = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=comment)
    CommentFactory(
        content_type=ct,
        object_id=dataset.pk,
        is_public=False,
        parent=comment,
    )
    app.set_user(reply.user)
    resp = app.get(dataset.get_absolute_url()).follow()
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert comments.count() == 3
    assert sorted([comment.pk for comment, _, _ in resp.context["comments"]]) == sorted([comment.pk, reply.pk])


@pytest.mark.django_db
def test_view_reply_to_reply_not_public_without_permission(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=True)
    reply = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=comment)
    CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=reply)
    user = UserFactory()
    app.set_user(user)
    resp = app.get(dataset.get_absolute_url()).follow()
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert comments.count() == 3
    assert [comment for comment, _, _ in resp.context["comments"]] == [comment]


@pytest.mark.django_db
def test_view_reply_to_reply_not_public_with_permission(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    comment = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=True)
    reply = CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=comment)
    CommentFactory(content_type=ct, object_id=dataset.pk, is_public=False, parent=reply)
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
    )
    app.set_user(representative.user)
    resp = app.get(dataset.get_absolute_url()).follow()
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert comments.count() == 3
    assert sorted([comment.pk for comment, _, _ in resp.context["comments"]]) == sorted(
        list(comments.values_list("pk", flat=True))
    )


@pytest.mark.django_db
def test_subscription_about_comment(app: DjangoTestApp):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(content_type=ct, object_id=dataset.pk)
    app.set_user(representative.user)
    form = app.get(
        reverse(
            "subscribe-form", kwargs={"content_type_id": ct.pk, "obj_id": dataset.pk, "user_id": representative.user.pk}
        )
    ).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["dataset_update_sub"] = True
    form["dataset_comments_sub"] = True
    form.submit()

    user = UserFactory()
    app.set_user(user)
    form = app.get(dataset.get_absolute_url()).follow().forms["comment-form"]
    form["is_public"] = False
    form["body"] = "Test comment"
    resp = form.submit().follow().follow()  # comment form → dataset view → versioned dataset view
    comments = Comment.objects.filter(content_type=ct, object_id=dataset.pk)
    assert comments.count() == 1
    assert [comment for comment, _, _ in resp.context["comments"]] == [comments.first()]
    assert len(mail.outbox) == 2
    assert mail.outbox[1].to == [representative.email]
    assert "Test comment" in mail.outbox[1].body


@pytest.mark.django_db
def test_delete_comment_without_login(client):
    comment = CommentFactory()
    url = reverse("delete-comment", kwargs={"pk": comment.pk})

    resp = client.post(url)

    assert resp.status_code == 302
    assert "login" in resp.url
    assert Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
def test_delete_comment_as_non_author(client):
    comment = CommentFactory()
    other_user = UserFactory()
    client.force_login(other_user)
    url = reverse("delete-comment", kwargs={"pk": comment.pk})

    resp = client.post(url)

    assert resp.status_code == 404
    assert Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
def test_delete_comment_as_author(client):
    user = UserFactory()
    comment = CommentFactory(user=user)
    client.force_login(user)
    url = reverse("delete-comment", kwargs={"pk": comment.pk})

    resp = client.post(url)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    comment.refresh_from_db()
    assert comment.deleted is True
    assert comment.deleted_on is not None


@pytest.mark.django_db
def test_delete_comment_as_superuser(client):
    comment = CommentFactory()
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)
    url = reverse("delete-comment", kwargs={"pk": comment.pk})

    resp = client.post(url)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    comment.refresh_from_db()
    assert comment.deleted is True
    assert comment.deleted_on is not None


@pytest.mark.django_db
def test_delete_nonexistent_comment(client):
    user = UserFactory()
    client.force_login(user)
    url = reverse("delete-comment", kwargs={"pk": 99999})

    resp = client.post(url)

    assert resp.status_code == 404


@pytest.mark.django_db
def test_delete_comment_wrong_http_method(client):
    user = UserFactory()
    comment = CommentFactory(user=user)
    client.force_login(user)
    url = reverse("delete-comment", kwargs={"pk": comment.pk})

    resp = client.get(url)

    assert resp.status_code == 405
    assert Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
def test_edit_comment_without_login(client):
    comment = CommentFactory()
    url = reverse("edit-comment", kwargs={"pk": comment.pk})

    resp = client.post(url, data={"body": "edited text"})

    assert resp.status_code == 302
    assert "login" in resp.url
    comment.refresh_from_db()
    assert comment.body != "edited text"


@pytest.mark.django_db
def test_edit_comment_as_non_author(client):
    comment = CommentFactory(body="original text")
    other_user = UserFactory()
    client.force_login(other_user)
    url = reverse("edit-comment", kwargs={"pk": comment.pk})

    resp = client.post(url, data={"body": "edited text"})

    assert resp.status_code == 404
    comment.refresh_from_db()
    assert comment.body == "original text"


@pytest.mark.django_db
def test_edit_comment_as_author(client):
    user = UserFactory()
    comment = CommentFactory(user=user, body="original text")
    client.force_login(user)
    url = reverse("edit-comment", kwargs={"pk": comment.pk})

    resp = client.post(url, data={"body": "edited text"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["body"] == "edited text"
    comment.refresh_from_db()
    assert comment.body == "edited text"


@pytest.mark.django_db
def test_edit_comment_as_superuser(client):
    comment = CommentFactory(body="original text")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)
    url = reverse("edit-comment", kwargs={"pk": comment.pk})

    resp = client.post(url, data={"body": "edited by admin"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    comment.refresh_from_db()
    assert comment.body == "edited by admin"


@pytest.mark.django_db
def test_edit_nonexistent_comment(client):
    user = UserFactory()
    client.force_login(user)
    url = reverse("edit-comment", kwargs={"pk": 99999})

    resp = client.post(url, data={"body": "edited text"})

    assert resp.status_code == 404


@pytest.mark.django_db
def test_edit_comment_empty_body(client):
    user = UserFactory()
    comment = CommentFactory(user=user, body="original text")
    client.force_login(user)
    url = reverse("edit-comment", kwargs={"pk": comment.pk})

    resp = client.post(url, data={"body": ""})

    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    comment.refresh_from_db()
    assert comment.body == "original text"


@pytest.mark.django_db
def test_edit_comment_updates_is_public(client):
    user = UserFactory()
    comment = CommentFactory(user=user, is_public=True)
    client.force_login(user)
    url = reverse("edit-comment", kwargs={"pk": comment.pk})

    # Make comment private
    resp = client.post(url, data={"body": "edited text"})

    assert resp.status_code == 200
    comment.refresh_from_db()
    assert comment.is_public is False

    # Make comment public again
    resp = client.post(url, data={"body": "edited again", "is_public": "on"})

    assert resp.status_code == 200
    comment.refresh_from_db()
    assert comment.is_public is True


@pytest.mark.django_db
def test_edit_comment_sets_edited_at(client):
    user = UserFactory()
    comment = CommentFactory(user=user, body="original text", edited_at=None)
    client.force_login(user)
    url = reverse("edit-comment", kwargs={"pk": comment.pk})

    assert comment.edited_at is None

    resp = client.post(url, data={"body": "edited text"})

    assert resp.status_code == 200
    comment.refresh_from_db()
    assert comment.edited_at is not None


@pytest.mark.django_db
def test_edit_comment_wrong_http_method(client):
    user = UserFactory()
    comment = CommentFactory(user=user)
    client.force_login(user)
    url = reverse("edit-comment", kwargs={"pk": comment.pk})

    resp = client.get(url)

    assert resp.status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights, expected_status_code",
    (
        (Dataset.PUBLIC, 302),  # Allow
        (Dataset.RESTRICTED, 302),  # Allow
        (Dataset.NON_PUBLIC, 403),  # Disallow
        (Dataset.CONFIDENTIAL, 403),  # Disallow
    ),
)
def test_comment_based_on_access_rights(app: DjangoTestApp, access_rights, expected_status_code):
    user1 = UserFactory()
    user2 = UserFactory()

    org2 = OrganizationFactory()
    dataset2 = DatasetFactory(organization=org2, access_rights=access_rights)
    RepresentativeFactory(user=user2, content_type=ContentType.objects.get_for_model(dataset2), object_id=dataset2.pk)

    ct = ContentType.objects.get_for_model(dataset2)

    # User1 (not owner) tries to comment
    app.set_user(user1)
    resp = app.post(
        reverse("comment", args=[ct.pk, dataset2.pk]), {"is_public": True, "body": "Test comment"}, expect_errors=True
    )

    assert resp.status_code == expected_status_code
    assert Comment.objects.filter(object_id=dataset2.pk).count() == (1 if expected_status_code == 302 else 0)


@pytest.mark.django_db
def test_comment_nonexistent_dataset(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)

    ct = ContentType.objects.get_for_model(Dataset)

    resp = app.post(
        reverse("comment", args=[ct.pk, 99999]), {"is_public": True, "body": "IDOR test"}, expect_errors=True
    )

    assert resp.status_code == 404


@pytest.mark.django_db
def test_comment_on_private_dataset_model(app: DjangoTestApp):
    user1 = UserFactory()
    user2 = UserFactory()

    dataset = DatasetFactory(organization=OrganizationFactory(), access_rights=Dataset.NON_PUBLIC)
    RepresentativeFactory(user=user2, content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk)
    model = ModelFactory(dataset=dataset)

    ct = ContentType.objects.get_for_model(model)

    app.set_user(user1)
    resp = app.post(
        reverse("comment", args=[ct.pk, model.pk]), {"is_public": True, "body": "IDOR test"}, expect_errors=True
    )

    assert resp.status_code == 403
    assert Comment.objects.filter(object_id=model.pk).count() == 0


@pytest.mark.django_db
def test_comment_on_non_public_project(app: DjangoTestApp):
    user1 = UserFactory()
    user2 = UserFactory()

    # User2's non-public project
    project = ProjectFactory(is_public=False, user=user2, status=Project.APPROVED)

    ct = ContentType.objects.get_for_model(project)

    # User1 tries to comment
    app.set_user(user1)
    resp = app.post(
        reverse("comment", args=[ct.pk, project.pk]), {"is_public": True, "body": "IDOR test"}, expect_errors=True
    )

    assert resp.status_code == 403
    assert Comment.objects.filter(object_id=project.pk).count() == 0


@pytest.mark.django_db
def test_comment_on_private_dataset_property(app: DjangoTestApp):
    """User tries to comment on Property belonging to private dataset"""
    user1 = UserFactory()
    user2 = UserFactory()

    # Setup private dataset with model and property (same as other tests)
    dataset = DatasetFactory(organization=OrganizationFactory(), access_rights=Dataset.NON_PUBLIC)
    RepresentativeFactory(user=user2, content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk)

    model = ModelFactory(dataset=dataset)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(model),
        object_id=model.pk,
        dataset=dataset,
        name="test/dataset/TestModel",
    )

    prop = PropertyFactory(model=model)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(prop),
        object_id=prop.pk,
        dataset=dataset,
        name="prop",
        type="string",
        title="Test prop",
    )

    ct = ContentType.objects.get_for_model(prop)

    # User1 tries to comment on the property
    app.set_user(user1)
    resp = app.post(
        reverse("comment", args=[ct.pk, prop.pk]), {"is_public": True, "body": "IDOR test"}, expect_errors=True
    )

    assert resp.status_code == 403
    assert Comment.objects.filter(object_id=prop.pk).count() == 0


@pytest.mark.django_db
def test_comment_on_unapproved_project(app: DjangoTestApp):
    user1 = UserFactory()
    user2 = UserFactory()

    project = ProjectFactory(is_public=True, user=user2, status=Project.CREATED)

    ct = ContentType.objects.get_for_model(project)

    app.set_user(user1)
    resp = app.post(
        reverse("comment", args=[ct.pk, project.pk]), {"is_public": True, "body": "Test"}, expect_errors=True
    )

    assert resp.status_code == 403

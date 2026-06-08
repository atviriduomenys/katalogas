import uuid
import pytest
from datetime import timedelta

from django.contrib.admin.options import get_content_type_for_model
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from django.test import Client
from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.messages.models import Subscription, NewsletterSubscriber
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory, ViispRepresentativeFactory
from vitrina.orgs.models import Organization, Representative
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
    return {"request": request, "dataset": dataset, "project": project, "user": user}


@pytest.mark.django_db
def test_request_subscribe_without_user(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data["request"].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id="number-of-subscribers")
    assert elem.get_text().strip() == "0"


@pytest.mark.django_db
def test_request_subscribe_url_no_login(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data["request"].get_absolute_url())
    elem = resp.html.find(id="request_subscription")
    form_url = elem.find("a", {"id": "subscribe-form"})
    assert form_url is None


@pytest.mark.django_db
def test_request_subscribe_form_no_login(app: DjangoTestApp, subscription_data):
    response = app.get(
        reverse(
            "subscribe-form",
            kwargs={
                "content_type_id": get_content_type_for_model(Request).id,
                "obj_id": subscription_data["request"].id,
                "user_id": subscription_data["user"].id,
            },
        )
    )
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_dataset_subscribe_for_other_user(app: DjangoTestApp, subscription_data):
    user = UserFactory()
    app.set_user(user)

    kwargs = {
        "content_type_id": get_content_type_for_model(Dataset).id,
        "obj_id": subscription_data["dataset"].id,
        "user_id": subscription_data["user"].id,
    }
    resp = app.get(reverse("subscribe-form", kwargs=kwargs))
    assert resp.url == reverse("dataset-detail", kwargs={"pk": subscription_data["dataset"].id})


@pytest.mark.django_db
def test_dataset_unsubscribe_for_other_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Dataset).id,
        "obj_id": subscription_data["dataset"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["dataset_update_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("dataset-detail", kwargs={"pk": subscription_data["dataset"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    user = UserFactory()
    app.set_user(user)

    csrf_token = app.cookies["csrftoken"]
    resp = app.post(reverse("unsubscribe", kwargs=kwargs), {"csrfmiddlewaretoken": csrf_token})
    assert resp.url == reverse("dataset-detail", kwargs={"pk": subscription_data["dataset"].id})
    assert Subscription.objects.count() == 1


@pytest.mark.django_db
def test_request_subscribe_form_with_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Request).id,
        "obj_id": subscription_data["request"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["request_update_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("request-detail", kwargs={"pk": subscription_data["request"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    resp = app.get(subscription_data["request"].get_absolute_url())

    elem = resp.html.find(id="number-of-subscribers")
    assert elem.get_text().strip() == "1"

    elem = resp.html.find(id="request_subscription")
    attr = elem.find("input", {"type": "submit"}).attrs["value"]
    assert attr == "Atsisakyti prenumeratos"

    resp.forms["unsubscribe-form"].submit()
    resp = app.get(subscription_data["request"].get_absolute_url())
    assert Subscription.objects.count() == 0

    assert len(mail.outbox) == 2

    elem = resp.html.find(id="number-of-subscribers")
    assert elem.get_text().strip() == "0"


@pytest.mark.django_db
def test_request_comment_subscription_email(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Request).id,
        "obj_id": subscription_data["request"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["request_update_sub"] = True
    form["request_comments_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("request-detail", kwargs={"pk": subscription_data["request"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    comment_user = UserFactory()
    app.set_user(comment_user)
    ct = ContentType.objects.get_for_model(subscription_data["request"])
    form = app.get(subscription_data["request"].get_absolute_url()).forms["comment-form"]
    form["is_public"] = True
    form["body"] = "Test comment"
    form.submit()
    created_comment = Comment.objects.filter(content_type=ct, object_id=subscription_data["request"].pk)
    assert created_comment.count() == 1
    assert Subscription.objects.count() == 2
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_request_update_subscription_email(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Request).id,
        "obj_id": subscription_data["request"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["request_update_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("request-detail", kwargs={"pk": subscription_data["request"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    staff_user = UserFactory(is_staff=True)
    app.set_user(staff_user)
    request = subscription_data["request"]
    form = app.get(reverse("request-update", args=[request.pk])).forms["request-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    resp = form.submit()
    request.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == request.get_absolute_url()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_dataset_subscribe_without_user(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data["dataset"].get_absolute_url()).follow()
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id="number-of-subscribers")
    assert elem.get_text().strip() == "0"


@pytest.mark.django_db
def test_dataset_subscribe_url_no_login(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data["dataset"].get_absolute_url()).follow()
    elem = resp.html.find(id="dataset_subscription")
    form_url = elem.find("a", {"id": "subscribe-form"})
    assert form_url is None


@pytest.mark.django_db
def test_dataset_subscribe_form_no_login(app: DjangoTestApp, subscription_data):
    response = app.get(
        reverse(
            "subscribe-form",
            kwargs={
                "content_type_id": get_content_type_for_model(Dataset).id,
                "obj_id": subscription_data["dataset"].id,
                "user_id": subscription_data["user"].id,
            },
        )
    )
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_dataset_subscribe_form_with_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Dataset).id,
        "obj_id": subscription_data["dataset"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["dataset_update_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("dataset-detail", kwargs={"pk": subscription_data["dataset"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    resp = app.get(subscription_data["dataset"].get_absolute_url()).follow()

    elem = resp.html.find(id="number-of-subscribers")
    assert elem.get_text().strip() == "1"

    elem = resp.html.find(id="dataset_subscription")
    attr = elem.find("input", {"type": "submit"}).attrs["value"]
    assert attr == "Atsisakyti prenumeratos"

    resp.forms["unsubscribe-form"].submit()
    resp = app.get(subscription_data["dataset"].get_absolute_url()).follow()
    assert Subscription.objects.count() == 0

    assert len(mail.outbox) == 2

    elem = resp.html.find(id="number-of-subscribers")
    assert elem.get_text().strip() == "0"


@pytest.mark.django_db
def test_dataset_comment_subscription_email(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Dataset).id,
        "obj_id": subscription_data["dataset"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["dataset_update_sub"] = True
    form["dataset_comments_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("dataset-detail", kwargs={"pk": subscription_data["dataset"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    comment_user = UserFactory()
    app.set_user(comment_user)
    ct = ContentType.objects.get_for_model(subscription_data["dataset"])
    form = app.get(subscription_data["dataset"].get_absolute_url()).follow().forms["comment-form"]
    form["is_public"] = True
    form["body"] = "Test comment"
    form.submit()
    created_comment = Comment.objects.filter(content_type=ct, object_id=subscription_data["dataset"].pk)
    assert created_comment.count() == 1
    assert Subscription.objects.count() == 2
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_dataset_update_subscription_email(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Dataset).id,
        "obj_id": subscription_data["dataset"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["dataset_update_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("dataset-detail", kwargs={"pk": subscription_data["dataset"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    dataset = subscription_data["dataset"]
    representative = ViispRepresentativeFactory(content_object=dataset.organization)
    user = representative.user
    app.set_user(user)
    form = app.get(reverse("dataset-change", args=[dataset.pk])).forms["dataset-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    form["name"] = f"{dataset.organization.name}test"
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_dataset_update_global_org_subscription_email(app: DjangoTestApp, subscription_data):
    global_sub_user = subscription_data["user"]
    app.set_user(global_sub_user)
    Subscription.objects.create(
        user=global_sub_user,
        content_type=ContentType.objects.get_for_model(Organization),
        sub_type=Subscription.ORGANIZATION,
        dataset_update_sub=True,
        email_subscribed=True,
    )
    assert Subscription.objects.count() == 1

    dataset = subscription_data["dataset"]
    representative = ViispRepresentativeFactory(content_object=dataset.organization)
    user = representative.user
    app.set_user(user)
    form = app.get(reverse("dataset-change", args=[dataset.pk])).forms["dataset-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    form["name"] = f"{dataset.organization.name}test"
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_project_subscribe_without_user(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data["project"].get_absolute_url())
    assert Subscription.objects.count() == 0

    elem = resp.html.find(id="number-of-subscribers")
    assert elem.get_text().strip() == "0"


@pytest.mark.django_db
def test_project_subscribe_url_no_login(app: DjangoTestApp, subscription_data):
    resp = app.get(subscription_data["project"].get_absolute_url())
    elem = resp.html.find(id="project_subscription")
    form_url = elem.find("a", {"id": "subscribe-form"})
    assert form_url is None


@pytest.mark.django_db
def test_project_subscribe_form_no_login(app: DjangoTestApp, subscription_data):
    response = app.get(
        reverse(
            "subscribe-form",
            kwargs={
                "content_type_id": get_content_type_for_model(Project).id,
                "obj_id": subscription_data["project"].id,
                "user_id": subscription_data["user"].id,
            },
        )
    )
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_project_subscribe_form_with_user(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Project).id,
        "obj_id": subscription_data["project"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["project_update_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("project-detail", kwargs={"pk": subscription_data["project"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    resp = app.get(subscription_data["project"].get_absolute_url())

    elem = resp.html.find(id="number-of-subscribers")
    assert elem.get_text().strip() == "1"

    elem = resp.html.find(id="project_subscription")
    attr = elem.find("input", {"type": "submit"}).attrs["value"]
    assert attr == "Atsisakyti prenumeratos"

    resp.forms["unsubscribe-form"].submit()
    resp = app.get(subscription_data["project"].get_absolute_url())
    assert Subscription.objects.count() == 0

    assert len(mail.outbox) == 2

    elem = resp.html.find(id="number-of-subscribers")
    assert elem.get_text().strip() == "0"


@pytest.mark.django_db
def test_project_comment_subscription_email(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Project).id,
        "obj_id": subscription_data["project"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["project_update_sub"] = True
    form["project_comments_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("project-detail", kwargs={"pk": subscription_data["project"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    comment_user = UserFactory()
    app.set_user(comment_user)
    ct = ContentType.objects.get_for_model(subscription_data["project"])
    form = app.get(subscription_data["project"].get_absolute_url()).forms["comment-form"]
    form["is_public"] = True
    form["body"] = "Test comment"
    form.submit()
    created_comment = Comment.objects.filter(content_type=ct, object_id=subscription_data["project"].pk)
    assert created_comment.count() == 1
    assert Subscription.objects.count() == 2
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_project_update_subscription_email(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Project).id,
        "obj_id": subscription_data["project"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["project_update_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("project-detail", kwargs={"pk": subscription_data["project"].id})
    assert Subscription.objects.count() == 1

    assert len(mail.outbox) == 1

    staff_user = UserFactory(is_staff=True)
    app.set_user(staff_user)
    project = subscription_data["project"]

    form = app.get(reverse("project-update", args=[project.pk])).forms["project-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    resp = form.submit()

    project.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == project.get_absolute_url()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_auto_subscribe_for_comment_and_reply_mail(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    ct = ContentType.objects.get_for_model(subscription_data["dataset"])
    form = app.get(subscription_data["dataset"].get_absolute_url()).follow().forms["comment-form"]
    form["is_public"] = True
    form["body"] = "Test comment"
    form.submit()
    created_comment = Comment.objects.filter(content_type=ct, object_id=subscription_data["dataset"].pk)
    assert created_comment.count() == 1
    assert Subscription.objects.count() == 1
    assert len(mail.outbox) == 0

    reply_user = UserFactory()
    comment = created_comment.first()
    app.set_user(reply_user)
    form = app.get(comment.content_object.get_absolute_url()).follow().forms[f"reply-form-{comment.pk}"]
    form["is_public"] = True
    form["body"] = "Test reply"
    resp = form.submit().follow().follow()
    comments = Comment.objects.filter(content_type=comment.content_type, object_id=comment.object_id)
    reply = Comment.objects.filter(content_type=comment.content_type, parent=comment).first()
    assert comments.count() == 2
    assert comment in list(resp.context["comments"])[0]
    assert reply in list(resp.context["comments"])[1]
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_dataset_and_org_sub_mail(app: DjangoTestApp, subscription_data):
    app.set_user(subscription_data["user"])
    kwargs = {
        "content_type_id": get_content_type_for_model(Organization).id,
        "obj_id": subscription_data["dataset"].organization.id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["dataset_update_sub"] = True
    form["dataset_comments_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("organization-detail", kwargs={"pk": subscription_data["dataset"].organization.id})
    assert Subscription.objects.count() == 1
    assert len(mail.outbox) == 1

    kwargs = {
        "content_type_id": get_content_type_for_model(Dataset).id,
        "obj_id": subscription_data["dataset"].id,
        "user_id": subscription_data["user"].id,
    }
    form = app.get(reverse("subscribe-form", kwargs=kwargs)).forms["subscribe-form"]
    form["email_subscribed"] = True
    form["dataset_update_sub"] = True
    form["dataset_comments_sub"] = True
    resp = form.submit()

    assert resp.url == reverse("dataset-detail", kwargs={"pk": subscription_data["dataset"].id})
    assert Subscription.objects.count() == 2
    assert len(mail.outbox) == 2

    dataset = subscription_data["dataset"]
    representative = ViispRepresentativeFactory(content_object=dataset.organization)
    user = representative.user
    app.set_user(user)

    form = app.get(reverse("dataset-change", args=[dataset.pk])).forms["dataset-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    form["name"] = f"{dataset.organization.name}test"
    resp = form.submit()

    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == dataset.get_absolute_url()
    assert len(mail.outbox) == 3


@pytest.mark.django_db
def test_subscribe_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    app.set_user(user)
    ct = ContentType.objects.get_for_model(dataset)
    response = app.get(reverse("subscribe-form", args=[ct.pk, dataset.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_subscribe_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=role,
    )
    app.set_user(user)
    response = app.get(reverse("subscribe-form", args=[ct.pk, dataset.pk, user.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_unsubscribe_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    app.set_user(user)
    ct = ContentType.objects.get_for_model(dataset)
    response = app.post(reverse("unsubscribe", args=[ct.pk, dataset.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_unsubscribe_with_non_public_dataset_with_access(app: DjangoTestApp, role: str):
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk, user=user, role=role
    )
    app.set_user(user)
    response = app.post(reverse("unsubscribe", args=[ct.pk, dataset.pk, user.pk]))
    assert response.status_code == 302


@pytest.mark.django_db
def test_subscribe_with_not_approved_project_without_access(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    user = UserFactory()
    app.set_user(user)
    ct = ContentType.objects.get_for_model(project)
    response = app.get(reverse("subscribe-form", args=[ct.pk, project.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_subscribe_with_not_approved_project_with_access(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(status=Project.CREATED, user=user)
    ct = ContentType.objects.get_for_model(project)
    app.set_user(user)
    response = app.get(reverse("subscribe-form", args=[ct.pk, project.pk, user.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_unsubscribe_with_not_approved_project_without_access(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    user = UserFactory()
    app.set_user(user)
    ct = ContentType.objects.get_for_model(project)
    response = app.post(reverse("unsubscribe", args=[ct.pk, project.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_unsubscribe_with_not_approved_project_with_access(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(status=Project.CREATED, user=user)
    ct = ContentType.objects.get_for_model(project)
    app.set_user(user)
    response = app.post(reverse("unsubscribe", args=[ct.pk, project.pk, user.pk]))
    assert response.status_code == 302


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestNewsletterSubscribeView:
    def test_subscribe_new_email_success(self, client):
        response = client.post(reverse("newsletter-subscribe"), {"email": "newuser@example.com"})

        assert response.status_code == 302

        subscriber = NewsletterSubscriber.objects.get(email="newuser@example.com")
        assert subscriber.status == NewsletterSubscriber.PENDING
        assert subscriber.confirmation_token is not None

        # Should send confirmation email
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["newuser@example.com"]
        assert "naujienlaiškio prenumeratos patvirtinimas" in mail.outbox[0].subject.lower()

    def test_subscribe_already_confirmed_email(self, client):
        NewsletterSubscriber.objects.create(
            email="existing@example.com",
            status=NewsletterSubscriber.SUBSCRIBED,
        )

        response = client.post(reverse("newsletter-subscribe"), {"email": "existing@example.com"})

        assert response.status_code == 302

        # Should not create new subscriber
        subscribers = NewsletterSubscriber.objects.filter(email="existing@example.com")
        assert subscribers.count() == 1

        # Should not send email
        assert len(mail.outbox) == 0

    def test_subscribe_empty_email(self, client):
        response = client.post(reverse("newsletter-subscribe"), {"email": ""})

        assert response.status_code == 302

        # Should not create subscriber
        assert NewsletterSubscriber.objects.count() == 0

        # Should not send email
        assert len(mail.outbox) == 0

    def test_subscribe_invalid_email_format(self, client):
        response = client.post(reverse("newsletter-subscribe"), {"email": "invalid-email"})

        # HTML validation should prevent this.
        assert response.status_code == 302


@pytest.mark.django_db
class TestNewsletterConfirmView:
    def test_confirm_expired_token(self, client):
        past_time = timezone.now() - timedelta(hours=25)
        subscriber = NewsletterSubscriber.objects.create(
            email="expired@example.com",
        )
        subscriber.initiate_subscription()
        NewsletterSubscriber.objects.filter(pk=subscriber.pk).update(confirmation_expires_at=past_time)

        response = client.get(reverse("newsletter-confirm", kwargs={"token": subscriber.confirmation_token}))

        assert response.status_code == 302

        # Should not confirm subscription
        subscriber.refresh_from_db()
        assert subscriber.status == NewsletterSubscriber.PENDING

    def test_resubmit_pending_does_not_duplicate(self, client):
        email = "pending@example.com"
        client.post(reverse("newsletter-subscribe"), {"email": email})
        client.post(reverse("newsletter-subscribe"), {"email": email})
        assert NewsletterSubscriber.objects.filter(email=email).count() == 1

    def test_confirm_nonexistent_token(self, client):
        fake_token = uuid.uuid4()

        response = client.get(reverse("newsletter-confirm", kwargs={"token": fake_token}))

        assert response.status_code == 302  # Redirect

    def test_confirm_already_confirmed_token(self, client):
        NewsletterSubscriber.objects.create(
            email="already@example.com", status=NewsletterSubscriber.SUBSCRIBED, confirmation_token=None
        )

        fake_token = uuid.uuid4()
        response = client.get(reverse("newsletter-confirm", kwargs={"token": fake_token}))

        assert response.status_code == 302  # Should redirect


@pytest.mark.django_db
class TestNewsletterUnsubscribeView:
    def test_unsubscribe_get_shows_confirmation_page(self, client):
        subscriber = NewsletterSubscriber.objects.create(
            email="unsubscribe@example.com",
            status=NewsletterSubscriber.SUBSCRIBED,
        )

        response = client.get(
            reverse(
                "newsletter-unsubscribe",
                kwargs={
                    "token": subscriber.unsubscribe_token,
                },
            )
        )

        assert response.status_code == 200
        assert "newsletter/unsubscribe_confirm.html" in [t.name for t in response.templates]
        assert subscriber.email in response.content.decode()

    def test_unsubscribe_post_deactivates_subscription(self, client):
        subscriber = NewsletterSubscriber.objects.create(
            email="unsubscribe@example.com",
            status=NewsletterSubscriber.SUBSCRIBED,
        )

        response = client.post(reverse("newsletter-unsubscribe", kwargs={"token": subscriber.unsubscribe_token}))

        assert response.status_code == 200
        assert "newsletter/unsubscribed.html" in [t.name for t in response.templates]

        subscriber.refresh_from_db()
        assert subscriber.status == NewsletterSubscriber.UNSUBSCRIBED

    def test_unsubscribe_invalid_token(self, client):
        fake_token = uuid.uuid4()

        response = client.get(reverse("newsletter-unsubscribe", kwargs={"token": fake_token}))

        assert response.status_code == 404

    def test_unsubscribe_inactive_subscription(self, client):
        subscriber = NewsletterSubscriber.objects.create(
            email="inactive@example.com",
            status=NewsletterSubscriber.UNSUBSCRIBED,
        )

        response = client.get(reverse("newsletter-unsubscribe", kwargs={"token": subscriber.unsubscribe_token}))

        assert response.status_code == 404


@pytest.mark.django_db
class TestNewsletterWorkflow:
    def test_complete_subscription_workflow(self, client):
        """Test complete workflow: subscribe -> confirm -> unsubscribe"""
        email = "workflow@example.com"

        # Step 1: Subscribe
        response = client.post(reverse("newsletter-subscribe"), {"email": email})
        assert response.status_code == 302

        subscriber = NewsletterSubscriber.objects.get(email=email)
        assert subscriber.status == NewsletterSubscriber.PENDING

        # Step 2: Confirm
        response = client.get(reverse("newsletter-confirm", kwargs={"token": subscriber.confirmation_token}))
        assert response.status_code == 200

        subscriber.refresh_from_db()
        assert subscriber.status == NewsletterSubscriber.SUBSCRIBED

        # Step 3: Unsubscribe
        response = client.post(reverse("newsletter-unsubscribe", kwargs={"token": subscriber.unsubscribe_token}))
        assert response.status_code == 200

        subscriber.refresh_from_db()
        assert subscriber.status == NewsletterSubscriber.UNSUBSCRIBED

    def test_resubscribe_after_unsubscribe(self, client):
        email = "resubscribe@example.com"

        NewsletterSubscriber.objects.create(
            email=email,
            status=NewsletterSubscriber.UNSUBSCRIBED,
        )

        response = client.post(reverse("newsletter-subscribe"), {"email": email})
        assert response.status_code == 302

        subscribers = NewsletterSubscriber.objects.filter(email=email)
        assert subscribers.count() == 1
        assert subscribers[0].status == NewsletterSubscriber.PENDING

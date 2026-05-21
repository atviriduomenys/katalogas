from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import Dataset, Attribution, DatasetAttribution
from vitrina.helpers import get_current_domain, email
from vitrina.messages.models import Subscription
from vitrina.orgs.models import Organization, Representative
from vitrina.tasks.models import Task

if TYPE_CHECKING:
    from vitrina.dcat.forms.dataset_forms import BaseResourceForm


def create_tasks_and_notify_subscribers_about_dataset_creation(request: HttpRequest, dataset: Dataset) -> None:
    if not (organization := dataset.organization):
        return

    subscriptions = Subscription.objects.filter(
        (Q(object_id=organization.pk) | Q(object_id=None)),
        sub_type=Subscription.ORGANIZATION,
        content_type=get_content_type_for_model(Organization),
        dataset_update_sub=True,
    )

    sub_email_list = []
    for sub in subscriptions:
        Task.objects.create(
            title=f"Duomenų rinkinys organizacijai: {dataset.organization}",
            description=f"Sukurtas naujas duomenų rinkinys organizacijai: {dataset.organization}.",
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            organization=dataset.organization,
            status=Task.CREATED,
            type=Task.DATASET,
            user=sub.user,
        )
        if sub.user.email and sub.email_subscribed:
            if sub.user.organization:
                orgs = [sub.user.organization] + list(sub.user.organization.get_descendants())
                sub_email_list = [org.email for org in orgs]
            sub_email_list.append(sub.user.email)

        dataset_url = f"{get_current_domain(request)}{reverse('dataset-detail', args=[dataset.id])}"
        email(
            sub_email_list,
            "dataset-created-sub",
            "vitrina/datasets/emails/sub/created.md",
            {"dataset": dataset.title, "link": dataset_url},
        )


def create_tasks_and_notify_subscribers_about_dataset_update(request: HttpRequest, dataset: Dataset) -> None:
    subscriptions = Subscription.objects.filter(
        sub_type=Subscription.DATASET,
        content_type=get_content_type_for_model(Dataset),
        object_id=dataset.id,
        dataset_update_sub=True,
    )
    if dataset.organization:
        organization_subscriptions = Subscription.objects.filter(
            Q(object_id=dataset.organization.pk) | Q(object_id=None),
            sub_type=Subscription.ORGANIZATION,
            content_type=get_content_type_for_model(Organization),
            dataset_update_sub=True,
        )
        subscriptions = organization_subscriptions | subscriptions

    sorted_subscriptions = sorted(subscriptions, key=lambda x: x.sub_type != Subscription.ORGANIZATION)

    subscription_email_list = []
    for subscription in sorted_subscriptions:
        Task.objects.create(
            title=f"Duomenų rinkinys: {dataset}",
            description=f"Atnaujintas duomenų rinkinys: {dataset}",
            content_type=get_content_type_for_model(Dataset),
            object_id=dataset.pk,
            organization=dataset.organization,
            status=Task.CREATED,
            type=Task.DATASET,
            user=subscription.user,
        )
        if (
            (user_email := subscription.user.email)
            and subscription.email_subscribed
            and user_email not in subscription_email_list
        ):
            subscription_email_list.append(user_email)

    if subscription_email_list:
        dataset_url = f"{get_current_domain(request)}{dataset.get_absolute_url()}"
        email(
            subscription_email_list,
            "dataset-updated",
            "vitrina/datasets/emails/sub/updated.md",
            {"title": dataset, "link": dataset_url},
        )


def create_dataset_representative_and_attribution(dataset: Dataset) -> None:
    if not dataset.organization:
        return

    Representative.objects.create(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        organization=dataset.organization,
        role=Representative.OPEN_DATA_MANAGER,
    )

    if not (attribution := Attribution.objects.filter(name=Attribution.CREATOR).first()):
        return

    if not dataset.name or dataset.name.startswith(dataset.organization.name):
        DatasetAttribution.objects.create(dataset=dataset, attribution=attribution, organization=dataset.organization)
    else:
        creator = Organization.objects.filter(
            name__in=[org.name for org in Organization.objects.all() if org.name and dataset.name.startswith(org.name)]
        ).first()
        if creator:
            DatasetAttribution.objects.create(dataset=dataset, attribution=attribution, organization=creator)


@transaction.atomic
def save_dataset_creator(request: WSGIRequest, dataset: Dataset, form: "BaseResourceForm") -> None:
    if "creator" not in form.cleaned_data or "creator" not in form.changed_data:
        return

    try:
        attribution = Attribution.objects.get(name=Attribution.CREATOR)
    except Attribution.DoesNotExist:
        messages.warning(
            request,
            _(
                "Priskyrimo tipas '{name}' nerastas, todėl priskyrimo reikšmė neišsaugota. "
                "Susisiekite su administratoriumi."
            ).format(name=Attribution.CREATOR),
        )
        return

    DatasetAttribution.objects.filter(dataset=dataset, attribution=attribution).delete()
    if organization := form.cleaned_data["creator"]:
        DatasetAttribution.objects.create(dataset=dataset, attribution=attribution, organization=organization)
    dataset.save()

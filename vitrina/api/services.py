from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone

from vitrina.api.models import ApiKey
from vitrina.api.exceptions import DuplicateAPIKeyException
from vitrina.helpers import get_current_domain
from vitrina.orgs.models import Organization
from vitrina.users.models import User


def get_api_key_organization_and_user(
    request: HttpRequest,
    raise_error: bool = True
) -> (Organization, User):
    organization = user = None
    ct = ContentType.objects.get_for_model(Organization)

    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.lower().startswith('apikey '):
        _, api_key = auth.split(None, 1)
        api_key = api_key.strip()

        if api_key:
            duplicate_key_org, is_duplicate = is_duplicate_key(api_key)
            if is_duplicate and duplicate_key_org:
                if raise_error:
                    url = "%s%s" % (
                        get_current_domain(request),
                        reverse('organization-members', args=[duplicate_key_org.pk])
                    )
                    raise DuplicateAPIKeyException(url=url)
            else:
                api_key_obj = (
                    ApiKey.objects.
                    filter(
                        api_key=api_key,
                        representative__content_type=ct,
                        representative__object_id__isnull=False
                    ).first()
                )
                if api_key_obj and api_key_obj.enabled and (
                    not api_key_obj.expires or
                    api_key_obj.expires > timezone.make_aware(datetime.now())
                ):
                    organization = api_key_obj.representative.content_object
                    user = api_key_obj.representative.user
    return organization, user


def is_duplicate_key(api_key: str) -> (Organization, bool):
    duplicate_keys = (
        ApiKey.objects
        .filter(
            api_key__contains=api_key,
            api_key__startswith=ApiKey.DUPLICATE,
            enabled=False
        )
    )
    if duplicate_keys:
        organization = duplicate_keys.first().representative.content_object
        return organization, True
    return None, False

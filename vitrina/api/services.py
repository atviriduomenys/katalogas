from datetime import datetime

import requests
from django.core.cache import cache
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone

from vitrina.api.models import ApiKey
from vitrina.api.exceptions import DuplicateAPIKeyException
from vitrina.datasets.models import Dataset
from vitrina.helpers import get_current_domain
from vitrina.orgs.models import Organization
from vitrina.orgs.services import hash_api_key
from vitrina.settings import (
    SPINTA_SERVER_CLIENT_SECRET,
    SPINTA_SERVER_CLIENT_ID,
    SPINTA_SERVER_URL,
)
from vitrina.users.models import User


def get_api_key_organization_and_user(request: HttpRequest, raise_error: bool = True) -> (Organization, User):
    organization = user = dataset = organization_role = None
    publisher = False

    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if auth.lower().startswith("apikey "):
        _, api_key = auth.split(None, 1)
        api_key = api_key.strip()

        if api_key:
            duplicate_key_org, is_duplicate = is_duplicate_key(api_key)
            if is_duplicate and duplicate_key_org:
                if raise_error:
                    url = "%s%s" % (
                        get_current_domain(request),
                        reverse("organization-members", args=[duplicate_key_org.pk]),
                    )
                    raise DuplicateAPIKeyException(url=url)
            else:
                hashed_key = hash_api_key(api_key)
                api_key_obj = ApiKey.objects.filter(
                    api_key=hashed_key,
                ).first()
                if (
                    api_key_obj
                    and api_key_obj.enabled
                    and (not api_key_obj.expires or api_key_obj.expires > timezone.make_aware(datetime.now()))
                ):
                    if representative := api_key_obj.representative:
                        content_object = representative.content_object

                        if isinstance(content_object, Organization):
                            organization = content_object
                        elif isinstance(content_object, Dataset):
                            dataset = content_object
                            organization = content_object.organization

                        publisher = bool(representative.organization)

                        if publisher:
                            organization_role = representative.role

                        if not publisher:
                            user = representative.user
    return organization, user, dataset, organization_role, publisher


def is_duplicate_key(api_key: str) -> (Organization, bool):
    duplicate_keys = ApiKey.objects.filter(
        api_key__contains=api_key, api_key__startswith=ApiKey.DUPLICATE, enabled=False
    )
    if duplicate_keys:
        organization = duplicate_keys.first().representative.content_object
        return organization, True
    return None, False


def get_spinta_auth():
    token = cache.get("auth_token")
    if not token:
        data = {"grant_type": "client_credentials", "scope": "spinta_auth_clients"}
        resp = requests.post(
            SPINTA_SERVER_URL + "/auth/token",
            data=data,
            auth=(SPINTA_SERVER_CLIENT_ID, SPINTA_SERVER_CLIENT_SECRET),
        )
        if resp.status_code < 300:
            resp_data = resp.json()
            token = resp_data["access_token"]
            cache.set("auth_token", token, resp_data["expires_in"])
        else:
            return None
    return {"Authorization": "Bearer {}".format(token)}


def get_auth_session():
    with requests.Session() as session:
        if get_spinta_auth():
            session.headers.update(get_spinta_auth())
        return session

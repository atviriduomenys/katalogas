from unittest.mock import ANY
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from vitrina.exceptions import UAPIException
from vitrina.projects.factories import UseCaseClientFactory
from vitrina.projects.models import UseCaseClient
from vitrina.uapi.pagination import UAPIPagination
from vitrina.uapi.serializers.uapi_serializers import BaseUUIDObjectMixin


UUID_1 = "38961059-675e-4946-a2a4-1e1e36a3d06f"
UUID_2 = "4d6a9903-21d5-4b09-90dc-4e53e73f374f"
UUID_3 = "51fe08f2-d99f-4748-adc3-67038dc4b3c6"
UUID_4 = "be61a6fa-27bc-4799-b918-75d096ee668e"


@pytest.fixture
def paginator() -> UAPIPagination:
    return UAPIPagination()


def get_use_case_client_data(paginator: UAPIPagination, query_str: str = "") -> dict:
    request = Request(APIRequestFactory().get(f"/fake-url/{query_str}"))
    serializer = UseCaseClientTestSerializer(
        paginator.paginate_queryset(UseCaseClient.objects.all(), request), many=True
    )

    return {"_data": serializer.data}


class UseCaseClientTestSerializer(BaseUUIDObjectMixin, serializers.ModelSerializer):
    class Meta:
        model = UseCaseClient
        fields = ("name", "client_id") + BaseUUIDObjectMixin.Meta.fields


def test_pagination_disabled_when_limit_query_param_not_given(paginator: UAPIPagination):
    use_case_client1 = UseCaseClientFactory(uuid=UUID_1)
    use_case_client2 = UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator)
    paginated_data = paginator.get_paginated_response(data).data

    assert "_next" not in paginated_data
    assert paginated_data == {
        "_data": [
            {
                "name": use_case_client1.name,
                "client_id": use_case_client1.client_id,
                "_type": "",
                "_id": UUID_1,
                "_revision": "",
                "_txn": "",
                "_created": ANY,
                "_updated": ANY,
                "@context": "",
            },
            {
                "name": use_case_client2.name,
                "client_id": use_case_client2.client_id,
                "_type": "",
                "_id": UUID_2,
                "_revision": "",
                "_txn": "",
                "_created": ANY,
                "_updated": ANY,
                "@context": "",
            },
        ],
    }


def test_limits_results_and_return_next_page_if_limit_query_param_given(paginator: UAPIPagination):
    use_case_client1 = UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?_limit=1")
    paginated_data = paginator.get_paginated_response(data).data

    assert "_next" in paginated_data
    assert paginated_data == {
        "_next": "WyIzODk2MTA1OS02NzVlLTQ5NDYtYTJhNC0xZTFlMzZhM2QwNmYiXQ..",
        "_data": [
            {
                "name": use_case_client1.name,
                "client_id": use_case_client1.client_id,
                "_type": "",
                "_id": UUID_1,
                "_revision": "",
                "_txn": "",
                "_created": ANY,
                "_updated": ANY,
                "@context": "",
            },
        ],
    }


def test_returns_all_results_and_next_page_none_if_limit_is_greater_than_result_count(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?_limit=3")
    paginated_data = paginator.get_paginated_response(data).data

    assert "_next" in paginated_data
    assert paginated_data["_next"] is None
    assert len(paginated_data["_data"]) == 2


@pytest.mark.parametrize(
    "limit, err_message",
    [
        (-1, 'Query parameter "_limit" must be a positive integer.'),
        (0, 'Query parameter "_limit" must be between 0 and 1000.'),
        (1000, 'Query parameter "_limit" must be between 0 and 1000.'),
    ],
)
def test_raise_error_if_limit_is_less_than_zero_or_more_than_max(
    paginator: UAPIPagination, limit: int, err_message: str
):
    with pytest.raises(UAPIException) as exc_info:
        get_use_case_client_data(paginator, query_str=f"?_limit={limit}")

    assert exc_info.value.detail == {
        "code": "incorrect_query_parameters",
        "type": "IncorrectQueryParameters",
        "template": "Given query parameters are incorrect.",
        "message": err_message,
        "context": None,
        "additionalProperties": None,
    }


def test_sort_by__id_asc_if_sort_not_given(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_3)
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?_limit=10")
    paginated_data = paginator.get_paginated_response(data).data

    assert [row["_id"] for row in paginated_data["_data"]] == [UUID_1, UUID_2, UUID_3]


@pytest.mark.parametrize(
    "result, sort_query",
    [
        ([(UUID_1, "C_name"), (UUID_2, "A_name"), (UUID_3, "B_name"), (UUID_4, "B_name")], ""),
        ([(UUID_1, "C_name"), (UUID_2, "A_name"), (UUID_3, "B_name"), (UUID_4, "B_name")], "_sort=_id"),
        ([(UUID_4, "B_name"), (UUID_3, "B_name"), (UUID_2, "A_name"), (UUID_1, "C_name")], "_sort=-_id"),
        ([(UUID_2, "A_name"), (UUID_3, "B_name"), (UUID_4, "B_name"), (UUID_1, "C_name")], "_sort=name,_id"),
        ([(UUID_2, "A_name"), (UUID_4, "B_name"), (UUID_3, "B_name"), (UUID_1, "C_name")], "_sort=name,-_id"),
        ([(UUID_1, "C_name"), (UUID_3, "B_name"), (UUID_4, "B_name"), (UUID_2, "A_name")], "_sort=-name,_id"),
    ],
)
def test_sort_asc_desc(paginator: UAPIPagination, sort_query: str, result: list[tuple[str, str]]):
    UseCaseClientFactory(uuid=UUID_4, name="B_name")
    UseCaseClientFactory(uuid=UUID_2, name="A_name")
    UseCaseClientFactory(uuid=UUID_1, name="C_name")
    UseCaseClientFactory(uuid=UUID_3, name="B_name")

    data = get_use_case_client_data(paginator, query_str=f"?_limit=10&{sort_query}")
    paginated_data = paginator.get_paginated_response(data).data

    assert [(row["_id"], row["name"]) for row in paginated_data["_data"]] == result


def test_raise_error_if_non_existing_sort_field_given(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_1)

    with pytest.raises(UAPIException) as exc_info:
        get_use_case_client_data(paginator, query_str="?_limit=10&_sort=foo")

    assert exc_info.value.detail == {
        "code": "incorrect_query_parameters",
        "type": "IncorrectQueryParameters",
        "template": "Given query parameters are incorrect.",
        "message": 'One of the values of query parameter "_sort" cannot be used in result ordering.',
        "context": None,
        "additionalProperties": None,
    }


def test_sort_by_reserved_fields_maps_to_db_fields(paginator: UAPIPagination):
    use_case_client1 = UseCaseClientFactory(uuid=UUID_1)
    use_case_client2 = UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?_limit=10&_sort=-_created")
    paginated_data = paginator.get_paginated_response(data).data

    timezone = ZoneInfo(settings.TIME_ZONE)
    assert [row["_created"] for row in paginated_data["_data"]] == [
        use_case_client2.created_at.astimezone(timezone).isoformat(),
        use_case_client1.created_at.astimezone(timezone).isoformat(),
    ]


def test_return_elements_from_start_if_no_page_given(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?_limit=1")
    paginated_data = paginator.get_paginated_response(data).data

    assert [row["_id"] for row in paginated_data["_data"]] == [UUID_1]


def test_filter_gt_than_page_element_if_page_given_and_sort_asc(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    page = paginator._encode_uapi_urlsafe_base64(f'["{UUID_1}"]')
    data = get_use_case_client_data(paginator, query_str=f"?_limit=1&_page={page}")
    paginated_data = paginator.get_paginated_response(data).data

    assert [row["_id"] for row in paginated_data["_data"]] == [UUID_2]


def test_filter_lt_page_element_if_page_given_and_sort_desc(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    page = paginator._encode_uapi_urlsafe_base64(f'["{UUID_2}"]')
    data = get_use_case_client_data(paginator, query_str=f"?_limit=1&_sort=-_id&_page={page}")
    paginated_data = paginator.get_paginated_response(data).data

    assert [row["_id"] for row in paginated_data["_data"]] == [UUID_1]


def test_decoded_page_structure(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?_limit=1")
    paginated_data = paginator.get_paginated_response(data).data

    assert paginator._decode_uapi_urlsafe_base64(paginated_data["_next"]) == f'["{UUID_1}"]'


def test_page_encoding_decoding(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?_limit=1")
    paginated_data = paginator.get_paginated_response(data).data

    assert (
        paginator._encode_uapi_urlsafe_base64(paginator._decode_uapi_urlsafe_base64(paginated_data["_next"]))
        == paginated_data["_next"]
    )


@pytest.mark.parametrize("incorrect_page_value", ["test", "dGVzdA..", "-a-d-a-d-s"])
def test_raise_error_if_incorrect_page_value_given_to_query(paginator: UAPIPagination, incorrect_page_value: str):
    with pytest.raises(UAPIException) as exc_info:
        get_use_case_client_data(paginator, query_str=f"?_limit=10&_page={incorrect_page_value}")

    assert exc_info.value.detail == {
        "code": "incorrect_query_parameters",
        "type": "IncorrectQueryParameters",
        "template": "Given query parameters are incorrect.",
        "message": 'Values of query parameter "_page" cannot be decoded.',
        "context": None,
        "additionalProperties": None,
    }


def test_raise_error_if_page_value_count_is_not_equal_to_sort_value_count(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?_limit=1")
    paginated_data = paginator.get_paginated_response(data).data

    page = paginated_data["_next"]
    with pytest.raises(UAPIException) as exc_info:
        get_use_case_client_data(paginator, query_str=f"?_limit=10&_sort=_id,name&_page={page}")

    assert exc_info.value.detail == {
        "code": "incorrect_query_parameters",
        "type": "IncorrectQueryParameters",
        "template": "Given query parameters are incorrect.",
        "message": 'Decoded query parameter "_page" (1) must match number of elements in query parameter "_sort" (2).',
        "context": None,
        "additionalProperties": None,
    }


def test_raise_error_if_cannot_filter_by_page_values(paginator: UAPIPagination):
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?_limit=1")
    paginated_data = paginator.get_paginated_response(data).data

    page = paginated_data["_next"]
    with pytest.raises(UAPIException) as exc_info:
        get_use_case_client_data(paginator, query_str=f"?_limit=1&_sort=foo&_page={page}")

    assert exc_info.value.detail == {
        "code": "incorrect_query_parameters",
        "type": "IncorrectQueryParameters",
        "template": "Given query parameters are incorrect.",
        "message": 'One of the values of query parameter "_sort" cannot be used in result ordering.',
        "context": None,
        "additionalProperties": None,
    }


def test_pagination_allows_changing_query_param_variables():
    class ChildUAPIPagination(UAPIPagination):
        limit_query_param: str = "my_limit"
        sort_query_param: str = "my_sort"
        page_query_param: str = "my_page"

    paginator = ChildUAPIPagination()
    UseCaseClientFactory(uuid=UUID_1)
    UseCaseClientFactory(uuid=UUID_2)

    data = get_use_case_client_data(paginator, query_str="?my_limit=1&my_sort=-_id")
    paginated_data = paginator.get_paginated_response(data).data

    assert "_next" in paginated_data
    assert [row["_id"] for row in paginated_data["_data"]] == [UUID_2]

    page = paginated_data["_next"]
    data = get_use_case_client_data(paginator, query_str=f"?my_limit=1&my_sort=-_id&my_page={page}")
    paginated_data = paginator.get_paginated_response(data).data

    assert [row["_id"] for row in paginated_data["_data"]] == [UUID_1]

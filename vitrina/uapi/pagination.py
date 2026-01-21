import base64
import binascii
import json
from dataclasses import dataclass
from json import JSONDecodeError

from django.core.exceptions import FieldError
from django.db.models import QuerySet, Q
from rest_framework import status
from rest_framework.pagination import BasePagination
from rest_framework.request import Request
from rest_framework.response import Response

from vitrina.exceptions import UAPIException


@dataclass
class OrderAttribute:
    field_name: str
    is_reverse: bool

    @property
    def order_value(self) -> str:
        return f"-{self.field_name}" if self.is_reverse else self.field_name

    @property
    def field_lookup_key(self) -> str:
        return f"{self.field_name}__lt" if self.is_reverse else f"{self.field_name}__gt"


class UAPIPagination(BasePagination):
    """
    Pagination class for UAPI endpoints. Implementation is very similar to CursorPagination, but
    "cursor" is called "_page" and has slightly different encoding and structure.

    Pagination is controlled by 3 query parameters set in variables "limit_query_param", "sort_query_param"
    and "page_query_param". Following list shows default values and explains what each parameter does:
        * _limit - must be integer between 0 and 1000. Controls number of items returned in single page.
                   If not set - pagination is disabled.
        * _sort - comma separated string with fields to sort queryset by. Queryset must always be sorted.
                  Defaults to "_id".
        * _page - base64 encoded JSON string (or list) with all "_sort" field values of the last element of previous
                  page. Result is returned starting with element following _page element. If not given - results are
                  returned from queryset start.
    """

    # Maps reserved fields with model fields. Override if needed
    reserved_field_map = {"_id": "uuid", "_created": "created_at", "_updated": "updated_at"}

    limit_query_param: str = "_limit"
    sort_query_param: str = "_sort"
    page_query_param: str = "_page"
    max_limit = 1000

    _limit: int | None  # Number of items in single page
    _ordering: list[OrderAttribute]  # List of field names to order queryset by
    _page: list  # List of page items
    _has_next_page: bool  # Indicates if next page is needed

    def get_limit(self, request: Request) -> int | None:
        if not (limit_param := request.query_params.get(self.limit_query_param)):
            return None

        if not limit_param.isdigit():
            raise UAPIException(
                code="incorrect_query_parameters",
                type="IncorrectQueryParameters",
                template="Given query parameters are incorrect.",
                message=f'Query parameter "{self.limit_query_param}" must be an positive integer.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        limit = int(limit_param)

        if not (0 < limit < self.max_limit):
            raise UAPIException(
                code="incorrect_query_parameters",
                type="IncorrectQueryParameters",
                template="Given query parameters are incorrect.",
                message=f'Query parameter "{self.limit_query_param}" must be between 0 and {self.max_limit}.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return limit

    @staticmethod
    def _decode_uapi_urlsafe_base64(encoded_value: str) -> str:
        """
        Replaces following symbols in base64 encoded string and then does base64 decoding:
            "-" to "+"
            "_" to "/"
            "." to "="
        urlsafe_base64decode cannot be used because replace values do not match.
        """
        replaced_value = encoded_value.replace("-", "+").replace("_", "/").replace(".", "=")
        return base64.b64decode(replaced_value).decode("ascii")

    @staticmethod
    def _encode_uapi_urlsafe_base64(value: str) -> str:
        """
        Encodes given value using base64 and replaces following symbols:
            "+" to "-"
            "/" to "_"
            "=" to "."
        urlsafe_base64encode cannot be used because replace values do not match.
        """
        encoded_value = base64.b64encode(value.encode("ascii")).decode("ascii")
        return encoded_value.replace("+", "-").replace("/", "+").replace("=", ".")

    def _get_page_positions(self, request: Request) -> list[str] | None:
        if not (page_param := request.query_params.get(self.page_query_param)):
            return None

        try:
            decoded_param_json = self._decode_uapi_urlsafe_base64(page_param)
            decoded_param = json.loads(decoded_param_json)
        except (UnicodeDecodeError, ValueError, binascii.Error, JSONDecodeError):
            raise UAPIException(
                code="incorrect_query_parameters",
                type="IncorrectQueryParameters",
                template="Given query parameters are incorrect.",
                message=f'Values of query parameter "{self.page_query_param}" cannot be decoded.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(decoded_param, list):
            decoded_param = [decoded_param]

        if len(decoded_param) != len(self._ordering):
            raise UAPIException(
                code="incorrect_query_parameters",
                type="IncorrectQueryParameters",
                template="Given query parameters are incorrect.",
                message=(
                    f'Decoded query parameter "{self.page_query_param}" ({len(decoded_param)}) must match '
                    f'number of elements in query parameter "{self.sort_query_param}" ({len(self._ordering)}).'
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return decoded_param

    def _get_order_attributes(self, request: Request) -> list[OrderAttribute]:
        if not (sort_param_string := request.query_params.get(self.sort_query_param)):
            return [OrderAttribute(field_name=self.reserved_field_map.get("_id", "_id"), is_reverse=False)]

        order_attributes = []
        for sort_param in sort_param_string.split(","):
            param_without_order = sort_param.removeprefix("-")
            order_attributes.append(
                OrderAttribute(
                    field_name=self.reserved_field_map.get(param_without_order, param_without_order),
                    is_reverse=sort_param.startswith("-"),
                )
            )

        return order_attributes

    def _get_page_filter(self, page_position_values: list[str]) -> Q:
        page_filter = Q()

        for order_attribute, field_value in zip(self._ordering, page_position_values, strict=True):
            page_filter &= Q(**{order_attribute.field_lookup_key: field_value})

        return page_filter

    def paginate_queryset(self, queryset: QuerySet, request: Request, **kwargs) -> list:
        self._limit = self.get_limit(request)

        # If limit not set - pagination is not applied
        if self._limit is None:
            return list(queryset)

        # Order queryset by self.sort_query_param
        self._ordering = self._get_order_attributes(request)
        order_by = [order_attribute.order_value for order_attribute in self._ordering]
        try:
            queryset = queryset.order_by(*order_by)
        except FieldError:
            raise UAPIException(
                code="incorrect_query_parameters",
                type="IncorrectQueryParameters",
                template="Given query parameters are incorrect.",
                message=(
                    f'One of the values of query parameter "{self.sort_query_param}" cannot be used in result ordering.'
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Filter queryset starting from position given in self.page_query_param
        if page_positions := self._get_page_positions(request):
            page_filter = self._get_page_filter(page_positions)
            try:
                queryset = queryset.filter(page_filter)
            except FieldError:
                raise UAPIException(
                    code="incorrect_query_parameters",
                    type="IncorrectQueryParameters",
                    template="Given query parameters are incorrect.",
                    message=(
                        f'One of the values of query parameter "{self.sort_query_param}" '
                        f"cannot be used in result filtering."
                    ),
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        # Fetch limit + 1 results. Extra item is returned to check if next page position is needed
        results = list(queryset[: self._limit + 1])

        # Save page results to separate variable
        self._page = list(results[: self._limit])

        # Determine if next page is needed
        self._has_next_page = len(results) > self._limit

        return self._page

    def _get_next_page_position(self) -> str | None:
        """Calculates position of last page element"""
        if not self._has_next_page:
            return None

        last_item = self._page[-1]

        next_page_position = []
        for order_attribute in self._ordering:
            next_page_position.append(str(getattr(last_item, order_attribute.field_name)))

        next_page_position_string = json.dumps(next_page_position)
        return self._encode_uapi_urlsafe_base64(next_page_position_string)

    def get_paginated_response(self, data: dict) -> Response:
        # If limit not set - pagination is not applied
        if self._limit is None:
            return Response(data, status=status.HTTP_200_OK)

        data["_next"] = self._get_next_page_position()

        return Response(data)

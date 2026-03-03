from abc import ABC
from typing import TypeVar, Generic, Any

from django.utils.translation import gettext_lazy as _

from vitrina.structure.helpers import is_quoted

T = TypeVar("T")


class TypeCheckerError(Exception):
    pass


class TypeChecker(ABC, Generic[T]):
    def check_enum_item_value(self, value: str) -> None: ...


class StringTypeChecker(TypeChecker[str]):
    def check_enum_item_value(self, value: str) -> None:
        if not is_quoted(value):
            raise TypeCheckerError(_(f'Reikšmė "{value}" turi būti string tipo.'))


class IntegerTypeChecker(TypeChecker[int]):
    def check_enum_item_value(self, value: str) -> None:
        try:
            int(value)
        except (TypeError, ValueError):
            raise TypeCheckerError(_(f'Reikšmė "{value}" turi būti integer tipo.'))


class NotImplementedTypeChecker(TypeChecker[Any]):
    def check_enum_item_value(self, value: str) -> None:
        raise TypeCheckerError(_("Savybės reikšmės tipas nėra palaikomas."))


TYPE_CHECKER_MAP = {
    "string": StringTypeChecker(),
    "integer": IntegerTypeChecker(),
}


def get_type_checker_for_type(type_str: str) -> TypeChecker:
    return TYPE_CHECKER_MAP.get(type_str, NotImplementedTypeChecker())

from abc import ABC
from typing import TypeVar, Generic, Any

from django.utils.translation import gettext_lazy as _

from vitrina.structure.helpers import is_quoted

T = TypeVar("T")


VALID_BOOLEAN_PREPARE_VALUES = ("true", "false")


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


class BooleanTypeChecker(TypeChecker[bool]):
    def check_enum_item_value(self, value: str) -> None:
        if value not in VALID_BOOLEAN_PREPARE_VALUES:
            possible_values = ", ".join(VALID_BOOLEAN_PREPARE_VALUES)
            raise TypeCheckerError(_(f'Reikšmė "{value}" turi būti boolean tipo. Viena iš: {possible_values}'))


class NotImplementedTypeChecker(TypeChecker[Any]):
    def check_enum_item_value(self, value: str) -> None:
        raise TypeCheckerError(_("Savybės reikšmės tipas nėra palaikomas."))


TYPE_CHECKER_MAP = {
    "string": StringTypeChecker(),
    "integer": IntegerTypeChecker(),
    "boolean": BooleanTypeChecker(),
}


def get_type_checker_for_type(type_str: str) -> TypeChecker:
    return TYPE_CHECKER_MAP.get(type_str, NotImplementedTypeChecker())

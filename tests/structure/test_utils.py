import pytest

from vitrina.structure.utils import (
    get_type_checker_for_type,
    TypeChecker,
    StringTypeChecker,
    IntegerTypeChecker,
    NotImplementedTypeChecker,
    TypeCheckerError,
    BooleanTypeChecker,
)


class TestTypeChecker:
    @pytest.mark.parametrize(
        "type_variable, type_checker_class",
        [
            ("string", StringTypeChecker),
            ("integer", IntegerTypeChecker),
            ("boolean", BooleanTypeChecker),
            ("geometry", NotImplementedTypeChecker),
        ],
    )
    def test_type_checker_types(self, type_variable: str, type_checker_class: TypeChecker):
        assert type(get_type_checker_for_type(type_variable)) is type_checker_class

    @pytest.mark.parametrize("value", ['""', '"foo"', '"-1"', '"0"', '"1"', '"1.0"', '"True"', '"False"'])
    def test_check_enum_item_value_for_string_type_checker_success(self, value: str):
        assert get_type_checker_for_type("string").check_enum_item_value(value) is None

    @pytest.mark.parametrize("value", ["", "foo", "-1", "0", "1", "1.0", "True", "False"])
    def test_check_enum_item_value_for_string_type_checker_error(self, value: str):
        with pytest.raises(TypeCheckerError) as exc_info:
            get_type_checker_for_type("string").check_enum_item_value(value)

        assert str(exc_info.value) == f'Reikšmė "{value}" turi būti string tipo.'

    @pytest.mark.parametrize("value", ["-1", "0", "1"])
    def test_check_enum_item_value_for_integer_type_checker_success(self, value: str):
        assert get_type_checker_for_type("integer").check_enum_item_value(value) is None

    @pytest.mark.parametrize("value", ["", "foo", "1.0", "True", "False"])
    def test_check_enum_item_value_for_integer_type_checker_error(self, value: str):
        with pytest.raises(TypeCheckerError) as exc_info:
            get_type_checker_for_type("integer").check_enum_item_value(value)

        assert str(exc_info.value) == f'Reikšmė "{value}" turi būti integer tipo.'

    @pytest.mark.parametrize("value", ["true", "false"])
    def test_check_enum_item_value_for_boolean_type_checker_success(self, value: str):
        assert get_type_checker_for_type("boolean").check_enum_item_value(value) is None

    @pytest.mark.parametrize("value", ["True", "False", "1", "0", "yes", "no"])
    def test_check_enum_item_value_for_boolean_type_checker_error(self, value: str):
        with pytest.raises(TypeCheckerError) as exc_info:
            get_type_checker_for_type("boolean").check_enum_item_value(value)

        assert str(exc_info.value) == f'Reikšmė "{value}" turi būti boolean tipo. Viena iš: true, false'

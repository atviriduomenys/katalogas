import pytest
from unittest.mock import Mock

from vitrina.users.helpers import validate_person_name


@pytest.mark.parametrize(
    "name",
    ["Test", "Test User", "Test-User", "Vardas Pavardė"],
)
@pytest.mark.parametrize("is_last_name", [True, False])
def test_validate_person_name_valid(name, is_last_name):
    form = Mock()

    validate_person_name(form, name, is_last_name)

    form.add_error.assert_not_called()


@pytest.mark.parametrize(
    "name",
    [
        "",
        "T",
        "Test123",
        "Test_User",
        "Test@User",
        "Test--User",
        "Test  User",
        "Test - - User",
        "-Test",
        "Test-",
        " Test",
        "Test ",
    ],
)
@pytest.mark.parametrize(
    "is_last_name, expected_field",
    [
        (True, "last_name"),
        (False, "first_name"),
    ],
)
def test_validate_person_name_invalid(name, is_last_name, expected_field):
    form = Mock()

    validate_person_name(form, name, is_last_name)

    form.add_error.assert_called_once()
    assert form.add_error.call_args.args[0] == expected_field

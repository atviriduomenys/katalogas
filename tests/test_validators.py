import pytest
from django.core.exceptions import ValidationError

from vitrina.validators import phone_validator


@pytest.mark.parametrize(
    "phone",
    [
        "+37061234567",
        "+37051234567",
        "+37041234567",
        "061234567",
        "051234567",
        "041234567",
    ],
)
def test_phone_validator_valid(phone):
    phone_validator(phone)


@pytest.mark.parametrize(
    "phone",
    [
        "",
        "861234567",
        "+3706123456",
        "+370612345678",
        "06123456",
        "0712345678",
        "123456789",
        "+37061234567extra",
    ],
)
def test_phone_validator_invalid(phone):
    with pytest.raises(ValidationError):
        phone_validator(phone)

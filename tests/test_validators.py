import pytest
from django.conf import settings
from django.contrib.auth.password_validation import MinimumLengthValidator
from django.core.exceptions import ValidationError
from django.utils import translation

from vitrina.users.models import User
from vitrina.validators import UniquePasswordValidator, phone_validator, validate_absolute_uri


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


@pytest.mark.parametrize(
    "url",
    [
        "http://ext-db/api",
        "http://localhost:8000/spec.json",
        "http://10.0.0.5/api",
        "https://data.gov.lt/dataset/1",
        "https://get.data.gov.lt/datasets/gov/vmi/imis/:ns",
        "ftp://files.vmi.lt/export.csv",
        "HTTP://EXT-DB:8888/WSDL",
        "http://www.google.",
    ],
)
def test_validate_absolute_uri_valid(url):
    validate_absolute_uri(url)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "invalid",
        "N/A",
        "www.example.com",
        "/datasets/1",
        "data.gov.lt/dataset",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "mailto:info@vmi.lt",
        "http://",
        "http:///path",
        "http://ext db:8888/wsdl",
        "http://example.com/a b",
        "http://[::1",
        "http://ex\x01ample.com/p",
        "http://ex\x7fample.com/",
        "http://example.com/a\x02b",
        "http://example.com/a\u200bb",
        "http://:80/x",
        "http://user@/path",
        "http://host:abc/",
        "http://host:99999/",
    ],
)
def test_validate_absolute_uri_invalid(url):
    with pytest.raises(ValidationError):
        validate_absolute_uri(url)


@pytest.mark.django_db
def test_unique_password_validator_accepts_unsaved_user():
    # Django 5.1+ validates passwords against the unsaved user on sign-up.
    UniquePasswordValidator().validate("Secret-password-123", User(email="new@test.com"))


@pytest.mark.parametrize("min_length, form", [(12, "simbolių"), (21, "simbolis"), (22, "simboliai")])
def test_minimum_length_message_in_lithuanian(min_length, form):
    with translation.override("lt"):
        message = MinimumLengthValidator(min_length).get_error_message()
    assert message == f"Šis slaptažodis yra per trumpas. Jį turi sudaryti bent {min_length} {form}."


def test_lt_catalog_keeps_django_minimum_length_message():
    # The msgid is not in our code, so makemessages marks it obsolete (#~), which drops it from the catalog.
    po = (settings.BASE_DIR / "vitrina/locale/lt/LC_MESSAGES/django.po").read_text(encoding="utf-8")
    lines = po.replace('"\n"', "").splitlines()
    assert 'msgid "This password is too short. It must contain at least %d character."' in lines

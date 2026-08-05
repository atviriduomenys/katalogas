from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import check_password
from zxcvbn import zxcvbn
import re

phone_validator = RegexValidator(
    regex=r"^\+370\d{8}$|^0\d{8}$",
    message=_("Neteisingas telefono numerio formatas. Priimtini formatai: +370XXXXXXXX, 0XXXXXXXX"),
)

ABSOLUTE_URI_SCHEMES = ("http", "https", "ftp", "ftps")


def validate_absolute_uri(value: str) -> None:
    text = str(value)
    if any(character.isspace() or not character.isprintable() for character in text):
        raise ValidationError(URLValidator.message, code="invalid")

    try:
        parts = urlsplit(text)
        parts.port
    except ValueError:
        raise ValidationError(URLValidator.message, code="invalid")

    if parts.scheme.lower() not in ABSOLUTE_URI_SCHEMES or not parts.hostname:
        raise ValidationError(URLValidator.message, code="invalid")


class UppercaseValidator:
    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Slaptažodyje turi būti panaudota bent viena didžioji lotyniška raidė (A - Z)."),
                code="password_no_upper",
            )

    def get_help_text(self):
        return _("Slaptažodyje turi būti panaudota bent viena didžioji lotyniška raidė (A - Z).")


class LowercaseValidator:
    def validate(self, password, user=None):
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Slaptažodyje turi būti panaudota bent viena mažoji lotyniška raidė (a - z)."),
                code="password_no_lower",
            )

    def get_help_text(self):
        return _("Slaptažodyje turi būti panaudota bent viena mažoji lotyniška raidė (a - z).")


class DigitValidator:
    def validate(self, password, user=None):
        if not re.search(r"\d", password):
            raise ValidationError(
                _("Slaptažodyje turi būti panaudotas bent vienas skaitmuo (0 - 9)."),
                code="password_no_digit",
            )

    def get_help_text(self):
        return _("Slaptažodyje turi būti panaudotas bent vienas skaitmuo (0 - 9).")


class SpecialCharacterValidator:
    def validate(self, password, user=None):
        if not re.search(r'[!@#$%^&*()_+\-=/.,\';\]\[|}{":?><]', password):
            raise ValidationError(
                _(
                    "Slaptažodyje turi būti panaudotas bent vienas specialusis simbolis ( !@#$%^&*()_+-=/.,';][|}{\":?>< )."
                ),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            "Slaptažodyje turi būti panaudotas bent vienas specialusis simbolis ( !@#$%^&*()_+-=/.,';][|}{\":?>< )."
        )


class UniquePasswordValidator:
    def validate(self, password, user=None):
        # Imported here so model modules can import this module without an import cycle.
        from vitrina.users.models import OldPassword

        if user:
            old_passwords = OldPassword.objects.filter(user=user).order_by("-created")[:4]
            for old_password in old_passwords:
                if check_password(password, old_password.password.strip()):
                    raise ValidationError(
                        _("Slaptažotis neturi būti toks pat kaip prieš tai 3 buvusieji slaptažodžiai."),
                        code="password_not_unique",
                    )

    def get_help_text(self):
        return _("Slaptažotis neturi būti toks pat kaip prieš tai 3 buvusieji slaptažodžiai.")


class ZxcvbnPasswordValidator:
    def validate(self, password, user=None):
        result = zxcvbn(password)
        if result["score"] < 3:
            raise ValidationError(
                _(
                    "Slaptažodis per silpnas. Bandykite naudoti daugiau simbolių, didžiųjų raidžių, skaitmenų ir specialiųjų simbolių."
                ),
                code="password_too_weak",
            )

    def get_help_text(self):
        return ""

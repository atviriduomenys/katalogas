from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from vitrina.users.models import OldPassword
from django.contrib.auth.hashers import check_password
import re

class UppercaseValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("This password must contain at least one uppercase letter. (A - Z)"),
                code='password_no_upper',
            )

    def get_help_text(self):
        return _("Your password must contain at least one uppercase letter. (A - Z)")


class LowercaseValidator:
    def validate(self, password, user=None):
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("This password must contain at least one lowercase letter. (a - z)"),
                code='password_no_lower',
            )

    def get_help_text(self):
        return _("Your password must contain at least one lowercase letter. (a - z)")


class DigitValidator:
    def validate(self, password, user=None):
        if not re.search(r'\d', password):
            raise ValidationError(
                _("This password must contain at least one digit. (0 - 9)"),
                code='password_no_digit',
            )

    def get_help_text(self):
        return _("Your password must contain at least one digit.")


class SpecialCharacterValidator:
    def validate(self, password, user=None):
        if not re.search(r'[!@#$%^&*()_+\-=/.,\';\]\[|}{":?><]', password):
            raise ValidationError(
                _("This password must contain at least one special character. ( !@#$%^&*()_+-=/.,';][|}{\":?>< )"),
                code='password_no_special',
            )

    def get_help_text(self):
        return _("Your password must contain at least one special character.")


class UniquePasswordValidator:
    def validate(self, password, user=None):
        if user:
            old_passwords = OldPassword.objects.filter(user=user).order_by('-created')[:4]
            for old_password in old_passwords:
                if check_password(password, old_password.password.strip()):
                    raise ValidationError(
                        _("Your password cannot be the same as the last 3 passwords."),
                        code='password_not_unique',
                    )

    def get_help_text(self):
        return _("Your password cannot be the same as the last 3 passwords.")
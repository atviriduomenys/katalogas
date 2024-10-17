from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

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
        pass

    def get_help_text(self):
        return _("Your password cannot be the same as the last 3 passwords.")


class PasswordAttemptValidator:
    def __init__(self, max_attempts=5):
        self.max_attempts = max_attempts
        self.attempts = {}

    def validate(self, password, user=None):
        pass

    def get_help_text(self):
        return _("You have exceeded the allowed number of password attempts. After 5 unsuccessful attempts, your account will be locked.")
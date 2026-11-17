import regex
from django.utils.translation import gettext_lazy as _


NAME_REGEX = regex.compile(r"^\p{L}+(?:[- ]\p{L}+)*$")


def validate_person_name(form, name: str, is_last_name: bool):
    is_valid = name and len(regex.sub(r"[- ]", "", name)) >= 3 and NAME_REGEX.fullmatch(name)

    if not is_valid:
        if is_last_name:
            form.add_error("last_name", _("Pavardė negali būti trumpesnė nei 3 simboliai, negali turėti skaičių"))
        else:
            form.add_error("first_name", _("Vardas negali būti trumpesnis nei 3 simboliai, negali turėti skaičių"))

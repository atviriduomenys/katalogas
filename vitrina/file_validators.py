"""Project-specific django-filer upload validators.

Kept import-light on purpose: django-filer resolves the dotted paths in
FILER_ADD_FILE_VALIDATORS while its app config is being built, so this module
must not pull in Django models (that would risk an early/circular import).
"""

import re
import typing

from django.utils.translation import gettext as _
from filer.validation import FileValidationError

# An ``<?xml-stylesheet ...?>`` processing instruction makes the browser fetch
# and apply the referenced stylesheet (client-side XSLT) when the XML file is
# opened inline. XSLT can emit arbitrary HTML, so a same-origin upload becomes a
# stored-XSS vector -- the same class of risk that makes us scan SVGs and deny
# XHTML. The PI lives in the XML prolog, before the root element, so scanning a
# bounded prefix is enough. Catching the PI breaks the chain: a standalone
# stylesheet is inert unless some XML references it via this PI.
_XML_STYLESHEET_PI = re.compile(rb"<\?xml-stylesheet\b", re.IGNORECASE)

# How much of the head to scan for the PI. The prolog is tiny in practice; this
# is a generous bound that avoids reading large uploads into memory.
_PROLOG_SCAN_BYTES = 8192


def deny_xml_stylesheet(file_name: str, file: typing.IO, owner, mime_type: str) -> None:
    """Reject XML-family uploads carrying an ``<?xml-stylesheet?>`` PI."""
    file.seek(0)
    head = file.read(_PROLOG_SCAN_BYTES)
    file.seek(0)
    if isinstance(head, str):  # defensive: some backends hand back text
        head = head.encode("utf-8", "ignore")
    if _XML_STYLESHEET_PI.search(head):
        raise FileValidationError(
            _('Failas „{file_name}“: XML su stilių aprašu (xml-stylesheet) uždraustas svetainės saugumo politikos')
            .format(file_name=file_name)
        )

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
# XHTML. Such a PI is only honoured in the prolog, *before* the root element.
_XML_STYLESHEET_PI = re.compile(rb"<\?xml-stylesheet\b", re.IGNORECASE)

# Hard cap on how far we walk looking for the root element. A well-formed XML
# prolog is tiny; a prolog larger than this is either malformed or a deliberate
# attempt to push the PI out of view, so we fail closed rather than give up.
_MAX_PROLOG_BYTES = 1024 * 1024  # 1 MiB

_WHITESPACE = frozenset(b" \t\r\n")

# Byte constants (indexing a bytes object yields ints in Python 3).
_LT = 0x3C  # <
_GT = 0x3E  # >
_LBRACKET = 0x5B  # [
_RBRACKET = 0x5D  # ]


def _reject_stylesheet(file_name: str) -> typing.NoReturn:
    raise FileValidationError(
        _('Failas „{file_name}“: XML su stilių aprašu (xml-stylesheet) uždraustas svetainės saugumo politikos')
        .format(file_name=file_name)
    )


def _reject_unparseable(file_name: str) -> typing.NoReturn:
    # Fail closed: we could not reach the root element within the scan budget, so
    # we cannot rule out a stylesheet PI hidden behind an oversized prolog.
    raise FileValidationError(
        _('Failas „{file_name}“: nepavyko saugiai patikrinti XML pradžios.').format(file_name=file_name)
    )


def deny_xml_stylesheet(file_name: str, file: typing.IO, owner, mime_type: str) -> None:
    """Reject XML-family uploads whose prolog carries an ``<?xml-stylesheet?>`` PI.

    We walk the prolog, skipping the constructs allowed there (whitespace, other
    processing instructions, comments and the DOCTYPE), and stop at the root
    element. None of those constructs can be used to smuggle an active PI past
    us: comments and PIs are skipped as whole units, so a ``<?xml-stylesheet?>``
    can only match when it is a real, active PI. A padded/oversized prolog that
    never reaches a root element within the scan budget fails closed.
    """
    file.seek(0)
    head = file.read(_MAX_PROLOG_BYTES + 1)
    file.seek(0)
    if isinstance(head, str):  # defensive: some backends hand back text
        head = head.encode("utf-8", "ignore")

    over_cap = len(head) > _MAX_PROLOG_BYTES
    n = min(len(head), _MAX_PROLOG_BYTES)
    i = 0
    while i < n:
        if head[i] in _WHITESPACE:
            i += 1
            continue
        if head.startswith(b"<?", i):  # processing instruction or XML declaration
            if _XML_STYLESHEET_PI.match(head, i):
                _reject_stylesheet(file_name)
            end = head.find(b"?>", i + 2)
            if end == -1:
                break  # unterminated within budget -> fail closed below
            i = end + 2
            continue
        if head.startswith(b"<!--", i):  # comment
            end = head.find(b"-->", i + 4)
            if end == -1:
                break
            i = end + 3
            continue
        if head[i:i + 2] == b"<!":  # DOCTYPE / markup declaration
            i += 2
            depth = 0
            while i < n:
                b = head[i]
                if b == _LBRACKET:  # internal subset opens: '>' inside it is not the end
                    depth += 1
                elif b == _RBRACKET:
                    depth = max(0, depth - 1)
                elif b == _GT and depth == 0:
                    break
                i += 1
            else:
                break  # unterminated -> fail closed
            i += 1  # step past '>'
            continue
        if head[i] == _LT:  # start of the root element
            return  # reached the document element with no stylesheet PI -> safe
        # Bytes that are not part of a prolog construct (BOM, stray content).
        i += 1

    # Ran out of budget/buffer before reaching the root element.
    if over_cap:
        _reject_unparseable(file_name)
    # A small, fully-scanned file with no root element cannot carry an active
    # stylesheet association, so allow it (sniffing/other checks cover the rest).
    return

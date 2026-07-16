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

# Read granularity. We read incrementally and stop as soon as the root element is
# reached, so a legitimate file (root within the first few bytes) only ever reads
# one small chunk, regardless of how large the file itself is.
_CHUNK_BYTES = 8192

# Bytes needed to decide the stylesheet marker: len("<?xml-stylesheet") plus one
# trailing byte so the ``\b`` boundary can be evaluated.
_PI_MARKER_LEN = len(b"<?xml-stylesheet") + 1

_WHITESPACE = frozenset(b" \t\r\n")

# Byte constants (indexing a bytes object yields ints in Python 3).
_LT = 0x3C  # <
_GT = 0x3E  # >
_LBRACKET = 0x5B  # [
_RBRACKET = 0x5D  # ]


def _reject_stylesheet(file_name: str) -> typing.NoReturn:
    raise FileValidationError(
        _("Failas „{file_name}“: XML su stilių aprašu (xml-stylesheet) uždraustas svetainės saugumo politikos").format(
            file_name=file_name
        )
    )


def _reject_unparseable(file_name: str) -> typing.NoReturn:
    # Fail closed: we could not reach the root element within the scan budget, so
    # we cannot rule out a stylesheet PI hidden behind an oversized prolog.
    raise FileValidationError(
        _("Failas „{file_name}“: nepavyko saugiai patikrinti XML pradžios.").format(file_name=file_name)
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
    try:
        buf = bytearray()
        i = 0
        total = 0
        eof = False

        def ensure(count: int) -> bool:
            # Make at least ``count`` bytes available at position ``i``, reading
            # more chunks as needed. Returns False once EOF is hit first. Fails
            # closed if the prolog grows past the budget without a decision.
            nonlocal total, eof
            while (len(buf) - i) < count and not eof:
                if total >= _MAX_PROLOG_BYTES:
                    _reject_unparseable(file_name)
                chunk = file.read(_CHUNK_BYTES)
                if not chunk:
                    eof = True
                    break
                if isinstance(chunk, str):  # defensive: some backends hand back text
                    chunk = chunk.encode("utf-8", "ignore")
                buf.extend(chunk)
                total += len(chunk)
            return (len(buf) - i) >= count

        def find_from(sub: bytes, start: int) -> int:
            # Locate ``sub`` at or after ``start``, reading more data as needed.
            nonlocal total, eof
            search_pos = start
            while True:
                idx = buf.find(sub, search_pos)
                if idx != -1:
                    return idx
                if eof:
                    return -1
                if total >= _MAX_PROLOG_BYTES:
                    _reject_unparseable(file_name)
                # Resume near the current end so ``sub`` can still straddle the
                # join with the next chunk, without rescanning the whole buffer.
                search_pos = max(start, len(buf) - len(sub) + 1)
                chunk = file.read(_CHUNK_BYTES)
                if not chunk:
                    eof = True
                    return -1
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8", "ignore")
                buf.extend(chunk)
                total += len(chunk)

        while True:
            if not ensure(1):
                return  # EOF within the prolog: no root, no PI -> nothing active
            if buf[i] in _WHITESPACE:
                i += 1
                continue
            if buf[i] != _LT:  # stray byte before the first markup (e.g. a BOM)
                i += 1
                continue
            if not ensure(2):
                return  # a lone trailing '<' is not a real element start
            two = bytes(buf[i : i + 2])
            if two == b"<?":  # processing instruction or XML declaration
                ensure(_PI_MARKER_LEN)  # enough bytes to test the marker + boundary
                if _XML_STYLESHEET_PI.match(buf, i):
                    _reject_stylesheet(file_name)
                end = find_from(b"?>", i + 2)
                if end == -1:
                    return  # unterminated PI at EOF -> inert
                i = end + 2
                continue
            if two == b"<!":
                if not ensure(4):
                    return  # cannot even classify at EOF -> inert
                if bytes(buf[i : i + 4]) == b"<!--":  # comment
                    end = find_from(b"-->", i + 4)
                    if end == -1:
                        return
                    i = end + 3
                    continue
                # DOCTYPE / markup declaration: scan to the top-level '>', keeping
                # track of the internal-subset brackets (a '>' inside [...] is not
                # the end).
                j = i + 2
                depth = 0
                while True:
                    if j >= len(buf) and not ensure((j - i) + 1):
                        return  # unterminated declaration at EOF -> inert
                    c = buf[j]
                    if c == _LBRACKET:
                        depth += 1
                    elif c == _RBRACKET:
                        depth = max(0, depth - 1)
                    elif c == _GT and depth == 0:
                        break
                    j += 1
                i = j + 1
                continue
            # '<' followed by a name char (or '/') -> the document element starts
            # here, so any later PI is not a prolog stylesheet association.
            return
    finally:
        # Best-effort: leave the read cursor at the start for downstream handlers.
        try:
            file.seek(0)
        except Exception:
            pass

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from filer.validation import FileValidationError

from vitrina.fields import FilerFileField
from vitrina.helpers import validate_file

XHTML_XSS = (
    b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"\n'
    b'"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
    b'<html xmlns="http://www.w3.org/1999/xhtml">\n'
    b"<head><title>X</title></head>\n"
    b"<body>\n"
    b"<script>alert(document.domain)</script>\n"
    b"</body>\n"
    b"</html>\n"
)

HTML_XSS = b"<!DOCTYPE html><html><body><script>alert(document.domain)</script></body></html>\n"
SVG_XSS = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>\n'
SVG_CLEAN = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>\n'
PHP_SHELL = b'<?php system($_GET["c"]); ?>\n'
SH_SCRIPT = b"#!/bin/bash\nrm -rf /\n"
PE_BINARY = b"MZ\x90\x00" + b"\x00" * 64


# --- validate_file() helper (used by forms, fields and API serializers) ---


@pytest.mark.parametrize("file_name", ["testfile.xhtml", "evil.html", "evil.htm", "evil.shtml"])
def test_html_family_uploads_are_denied(file_name):
    upload = ContentFile(XHTML_XSS, name=file_name)
    with pytest.raises(FileValidationError):
        validate_file(upload)


@pytest.mark.parametrize(
    "file_name, content",
    [
        ("data.xml", b"<root/>"),
        ("metadata.rdf", b'<?xml version="1.0"?><rdf:RDF xmlns:rdf="x"/>'),
        ("notes.txt", b"hello world"),
        ("table.csv", b"a,b,c\n1,2,3\n"),
        ("payload.json", b'{"a": 1}'),
        ("vocab.ttl", b"@prefix ex: <http://example.org/> .\n"),
        ("image.svg", SVG_CLEAN),
    ],
)
def test_legitimate_uploads_are_allowed(file_name, content):
    # Regression guard: the whitelist must not block formats the portal needs
    # (XML family, plain text, CSV/JSON, RDF/Turtle, clean SVG).
    validate_file(ContentFile(content, name=file_name))


@pytest.mark.parametrize("file_name", ["macro.exe", "lib.so", "archive.rar", "font.woff"])
def test_unknown_types_are_denied_by_whitelist(file_name):
    # Fail-closed: anything not explicitly whitelisted is rejected, even though
    # there is no specific deny rule for it.
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(b"\x00\x01\x02binarydata", name=file_name))


@pytest.mark.parametrize(
    "file_name, content",
    [
        # Active content disguised under a whitelisted extension. The extension
        # gate passes, but content sniffing detects the real type and denies it.
        ("report.csv", HTML_XSS),
        ("data.txt", PHP_SHELL),
        ("notes.txt", SH_SCRIPT),
        ("photo.png", SVG_XSS),
        ("doc.pdf", PE_BINARY),
    ],
)
def test_spoofed_extension_is_caught_by_content_sniffing(file_name, content):
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(content, name=file_name))


def test_sniffing_failure_fails_closed(monkeypatch):
    # If libmagic errors (e.g. missing/misconfigured on the server), the upload
    # must be rejected with a user-visible error, not silently accepted without
    # the content-based check.
    import vitrina.helpers as helpers

    def boom(*args, **kwargs):
        raise RuntimeError("libmagic exploded")

    if helpers.magic is None:
        with pytest.raises(FileValidationError):
            validate_file(ContentFile(b"a,b,c\n1,2,3\n", name="table.csv"))
        return

    monkeypatch.setattr(helpers.magic, "from_buffer", boom)
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(b"a,b,c\n1,2,3\n", name="table.csv"))


# --- real form-field entry point (FilerFileField.clean) ---


def test_filer_file_field_rejects_xhtml():
    field = FilerFileField()
    upload = SimpleUploadedFile("testfile.xhtml", XHTML_XSS, content_type="application/xhtml+xml")
    # Deny happens before any DB write, so no database access is required here.
    with pytest.raises(ValidationError):
        field.clean(upload)

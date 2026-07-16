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


XML_STYLESHEET = b'<?xml version="1.0"?>\n<?xml-stylesheet type="text/xsl" href="evil.xsl"?>\n<root/>\n'


@pytest.mark.parametrize(
    "file_name",
    [
        # Honest .xml/.rdf extension, and the same payload smuggled under a benign
        # extension (caught on the content-sniffing pass).
        "data.xml",
        "metadata.rdf",
        "notes.txt",
    ],
)
def test_xml_with_stylesheet_pi_is_denied(file_name):
    # An <?xml-stylesheet?> PI makes the browser run client-side XSLT when the
    # file is opened inline from the media origin -> stored XSS.
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(XML_STYLESHEET, name=file_name))


def test_xml_stylesheet_pi_past_a_padded_prolog_is_denied():
    # The PI is only honoured before the root element, so padding the prolog with
    # a large comment must not push it out of the scan window (>8 KiB here).
    payload = (
        b'<?xml version="1.0"?>\n'
        b"<!-- " + b"x" * 9000 + b" -->\n"
        b'<?xml-stylesheet type="text/xsl" href="evil.xsl"?>\n'
        b"<root/>\n"
    )
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(payload, name="data.xml"))


def test_xml_stylesheet_pi_hidden_in_comment_is_allowed():
    # A commented-out PI is inert (the browser never applies it), so it must not
    # trip the validator -- confirms we skip comments as whole units.
    payload = b'<?xml version="1.0"?>\n<!-- <?xml-stylesheet href="x.xsl"?> -->\n<root/>\n'
    validate_file(ContentFile(payload, name="data.xml"))


def test_xml_with_oversized_prolog_fails_closed():
    # No root element within the scan budget -> we cannot vet it -> reject.
    payload = b'<?xml version="1.0"?>\n<!-- ' + b"x" * (1024 * 1024 + 16) + b" -->\n<root/>\n"
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(payload, name="data.xml"))


def test_xml_stylesheet_pi_straddling_a_read_chunk_is_denied():
    # The <?xml-stylesheet marker itself starts right around the 8 KiB chunk
    # boundary, so the incremental reader must fetch across the join to match it.
    pad = b" " * (8188 - len(b'<?xml version="1.0"?>\n'))
    payload = b'<?xml version="1.0"?>\n' + pad + b'<?xml-stylesheet type="text/xsl" href="e.xsl"?>\n<root/>\n'
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(payload, name="data.xml"))


def test_xml_with_doctype_then_stylesheet_pi_is_denied():
    # A DOCTYPE (with an internal subset whose ']' precedes the closing '>') must
    # be skipped as a unit, and a stylesheet PI after it still caught.
    payload = (
        b'<?xml version="1.0"?>\n'
        b'<!DOCTYPE root [ <!ENTITY e "v"> ]>\n'
        b'<?xml-stylesheet type="text/xsl" href="e.xsl"?>\n'
        b"<root/>\n"
    )
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(payload, name="data.xml"))


def test_xml_with_doctype_is_allowed_without_stylesheet():
    # Same DOCTYPE shape but no stylesheet PI -> must pass (guards over-blocking).
    payload = b'<?xml version="1.0"?>\n<!DOCTYPE root [ <!ENTITY e "v"> ]>\n<root/>\n'
    validate_file(ContentFile(payload, name="data.xml"))


def test_validate_file_pins_xhtml_to_xhtml_mime():
    # Portability guard: some hosts map .xhtml to a whitelisted type (e.g.
    # application/xml). validate_file must pin it to application/xhtml+xml so the
    # deny rule fires on the declared-type gate, not only via content sniffing.
    import mimetypes as mt

    try:
        mt.init(files=())  # simulate a container without /etc/mime.types
        mt.add_type("application/xml", ".xhtml")  # simulate a loose host mapping
        with pytest.raises(FileValidationError):
            validate_file(ContentFile(XHTML_XSS, name="a.xhtml"))
        # The assertion is what actually guards the fix: without the add_type in
        # validate_file this would still read "application/xml".
        assert mt.guess_type("a.xhtml")[0] == "application/xhtml+xml"
    finally:
        mt.init()  # restore the system-backed table for other tests


def test_sniffing_fails_closed_when_libmagic_unavailable(monkeypatch):
    # libmagic could not be imported at startup -> uploads must be rejected, not
    # silently accepted without the content-based check. Patching helpers.magic
    # makes this independent of whether libmagic is installed in the test env.
    import vitrina.helpers as helpers

    monkeypatch.setattr(helpers, "magic", None)
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(b"a,b,c\n1,2,3\n", name="table.csv"))


def test_sniffing_fails_closed_when_libmagic_errors(monkeypatch):
    # libmagic present but throwing (misconfigured/broken) -> also fail closed
    # with a user-visible error instead of skipping the sniffing defense layer.
    import types

    import vitrina.helpers as helpers

    def boom(*args, **kwargs):
        raise RuntimeError("libmagic exploded")

    monkeypatch.setattr(helpers, "magic", types.SimpleNamespace(from_buffer=boom))
    with pytest.raises(FileValidationError):
        validate_file(ContentFile(b"a,b,c\n1,2,3\n", name="table.csv"))


# --- real form-field entry point (FilerFileField.clean) ---


def test_filer_file_field_rejects_xhtml():
    field = FilerFileField()
    upload = SimpleUploadedFile("testfile.xhtml", XHTML_XSS, content_type="application/xhtml+xml")
    # Deny happens before any DB write, so no database access is required here.
    with pytest.raises(ValidationError):
        field.clean(upload)

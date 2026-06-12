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


# --- validate_file() helper (used by forms, fields and API serializers) ---


@pytest.mark.parametrize("file_name", ["testfile.xhtml", "evil.html", "evil.htm", "evil.shtml"])
def test_html_family_uploads_are_denied(file_name):
    upload = ContentFile(XHTML_XSS, name=file_name)
    with pytest.raises(FileValidationError):
        validate_file(upload)


@pytest.mark.parametrize("file_name", ["data.xml", "metadata.rdf", "notes.txt"])
def test_data_uploads_are_allowed(file_name):
    # Regression guard: blocking .xhtml must not block legitimate XML-family
    # uploads (application/xml, application/rdf+xml), which the portal needs.
    validate_file(ContentFile(b"<root/>", name=file_name))


# --- real form-field entry point (FilerFileField.clean) ---


def test_filer_file_field_rejects_xhtml():
    field = FilerFileField()
    upload = SimpleUploadedFile("testfile.xhtml", XHTML_XSS, content_type="application/xhtml+xml")
    # Deny happens before any DB write, so no database access is required here.
    with pytest.raises(ValidationError):
        field.clean(upload)

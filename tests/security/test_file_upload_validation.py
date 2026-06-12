import pytest
from django.core.files.base import ContentFile
from filer.validation import FileValidationError

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


@pytest.mark.parametrize("file_name", ["testfile.xhtml", "evil.html", "evil.htm", "evil.shtml"])
def test_html_family_uploads_are_denied(file_name):
    upload = ContentFile(XHTML_XSS, name=file_name)
    with pytest.raises(FileValidationError):
        validate_file(upload)


def test_plain_text_upload_is_allowed():
    upload = ContentFile(b"just some text", name="notes.txt")
    validate_file(upload)

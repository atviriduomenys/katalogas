import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from vitrina.smart_contracts.models import SmartContractTemplate
from vitrina.orgs.factories import OrganizationFactory


@pytest.mark.django_db
def test_valid_markdown_file_is_accepted():
    organization = OrganizationFactory()
    content = b"# Sample Markdown"
    md_file = SimpleUploadedFile("template.md", content)

    template = SmartContractTemplate.objects.create(file=md_file, organization=organization)

    assert template.file.name.endswith(".md")
    with open(template.file.path, "rb") as f:
        stored_content = f.read()
    assert stored_content == content

    os.remove(template.file.path)


@pytest.mark.django_db
def test_invalid_file_extension_raises_validation_error():
    organization = OrganizationFactory()
    txt_file = SimpleUploadedFile("template.txt", b"Not a markdown")

    template = SmartContractTemplate(file=txt_file, organization=organization)

    with pytest.raises(ValidationError) as exc_info:
        template.full_clean()
    assert "Failas turi būti Markdown formato (.md)." in str(exc_info.value)

from io import BytesIO
import yaml
import pytest
from vitrina.api_example.models import ApiExample
from vitrina.api_example.views import handle_yaml_file, is_duplicate
from vitrina.datasets.factories import DatasetFactory


def test_valid_yaml():
    valid_yaml_content = b"key: value"
    uploaded_file = BytesIO(valid_yaml_content)
    content, error = handle_yaml_file(uploaded_file)
    assert error is None
    assert content == valid_yaml_content.decode('utf-8')


def test_invalid_yaml():
    invalid_yaml_content = b"key: value\n- list item"
    uploaded_file = BytesIO(invalid_yaml_content)
    content, error = handle_yaml_file(uploaded_file)
    assert content is None
    assert error.startswith("Klaidingas YAML failas")


def test_general_error():
    uploaded_file = BytesIO(b"")
    content, error = handle_yaml_file(uploaded_file)
    assert content is None
    assert error.startswith("Įvyko klaida apdorojant failą")

@pytest.mark.django_db
def test_is_duplicate_no_existing_duplicate():
    dataset = DatasetFactory()
    file_content = "key: value"
    ApiExample.objects.create(file_data=file_content, dataset=dataset.id)
    result = is_duplicate(file_content)

    assert result is False
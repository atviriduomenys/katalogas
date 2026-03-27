import pytest

from vitrina.structure.helpers import is_quoted


@pytest.mark.parametrize(
    "value, result",
    [
        ("", False),
        ('""', True),
        ("''", True),
        ("Hello", False),
        ('"Hello"', True),
        ("'Hello'", True),
    ],
)
def test_is_quoted(value: str, result: bool):
    assert is_quoted(value) is result

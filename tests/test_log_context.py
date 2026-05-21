import logging

import pytest

from vitrina.log_context import (
    LogContextFilter,
    get_log_context,
    reset_log_context,
    set_log_context,
)


@pytest.fixture
def log_record():
    return logging.LogRecord(
        name="django.request",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Internal Server Error: /datasets/1",
        args=(),
        exc_info=None,
    )


def test_filter_uses_default_when_no_context(log_record):
    LogContextFilter().filter(log_record)
    assert log_record.user_id == "anonymous"


def test_filter_attaches_user_id_from_context(log_record):
    token = set_log_context(user_id=1)
    try:
        LogContextFilter().filter(log_record)
    finally:
        reset_log_context(token)
    assert log_record.user_id == 1


def test_set_log_context_merges_fields():
    first = set_log_context(user_id=1)
    second = set_log_context(request_id="abc123")
    try:
        assert get_log_context() == {"user_id": 1, "request_id": "abc123"}
    finally:
        reset_log_context(second)
        reset_log_context(first)


def test_reset_restores_previous_context():
    assert get_log_context() == {}
    token = set_log_context(user_id=1)
    reset_log_context(token)
    assert get_log_context() == {}

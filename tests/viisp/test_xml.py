from unittest import mock

import pytest
import requests
from django_webtest import DjangoTestApp
from vitrina.viisp.xml_utils import (
    create_signed_authentication_request_xml,
    create_signed_authentication_data_request_xml,
    get_response_with_user_data,
    get_response_with_ticket_id,
    _parse_ticket_id,
    _parse_user_data,
)
from base64 import b64decode


@pytest.fixture
def key():
    key_content = open("tests/viisp/resources/fake_rsa_key_b64.txt", "r").read()
    return b64decode(key_content).decode("ascii")


def test_get_response_with_user_data_returns_none_on_http_error(app: DjangoTestApp, key):
    resp = mock.Mock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError()
    with mock.patch("vitrina.viisp.xml_utils.post", return_value=resp):
        result = get_response_with_user_data("0961ca7d-ac07-47d2-98c7-1968db7dba8f", key)
    assert result is None


def test_get_response_with_user_data_returns_none_on_connection_error(app: DjangoTestApp, key):
    with mock.patch("vitrina.viisp.xml_utils.post", side_effect=requests.exceptions.ConnectionError()):
        result = get_response_with_user_data("0961ca7d-ac07-47d2-98c7-1968db7dba8f", key)
    assert result is None


def test_get_response_with_ticket_id_returns_error_data_on_connection_error(app: DjangoTestApp, key):
    with mock.patch("vitrina.viisp.xml_utils.post", side_effect=requests.exceptions.ConnectionError("boom")):
        ticket_id, error_data = get_response_with_ticket_id(key, "example.com")
    assert ticket_id is None
    assert error_data is not None


def test_auth_request_xml_signing(app: DjangoTestApp, key):
    domain = "example.com"
    xml_string = create_signed_authentication_request_xml(key, domain)
    with open("tests/viisp/resources/signed_auth_request.xml", "r") as xmlFile:
        assert xml_string == xmlFile.read()


def test_auth_data_request_xml_signing(app: DjangoTestApp, key):
    xml_string = create_signed_authentication_data_request_xml("0961ca7d-ac07-47d2-98c7-1968db7dba8f", key)
    with open("tests/viisp/resources/signed_auth_data_request.xml", "r") as xmlFile:
        assert xml_string == xmlFile.read()


def test_ticket_id_parsing(app: DjangoTestApp):
    with open("tests/viisp/resources/signed_auth_data_request.xml", "r") as xmlFile:
        assert "0961ca7d-ac07-47d2-98c7-1968db7dba8f" == _parse_ticket_id(xmlFile.read())


def test_user_data_parsing(app: DjangoTestApp):
    with open("tests/viisp/resources/response_with_user_data.xml", "r") as xmlFile:
        expected_user_data = {
            "lt_company_code": "1234-5678",
            "first_name": "VARDENIS",
            "last_name": "PAVARDENIS",
            "phone_number": "+37000000000",
            "company_name": "test company",
            "email": "test@test.lt",
            "personal_code": "30000000000",
        }
        assert expected_user_data == _parse_user_data(xmlFile.read())

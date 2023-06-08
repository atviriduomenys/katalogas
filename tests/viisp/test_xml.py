import pytest
from unittest.mock import patch
from django.urls import reverse
from django_webtest import DjangoTestApp
from vitrina.viisp.xml_utils import create_signed_authentication_request_xml, \
create_signed_authentication_data_request_xml, _parse_ticket_id, _parse_user_data

def test_auth_request_xml_signing(app: DjangoTestApp):
    xml_string = create_signed_authentication_request_xml()
    with open('tests/viisp/resources/signed_auth_request.xml', 'r') as xmlFile:
        assert xml_string == xmlFile.read()

def test_auth_data_request_xml_signing(app: DjangoTestApp):
    xml_string = create_signed_authentication_data_request_xml('0961ca7d-ac07-47d2-98c7-1968db7dba8f')
    with open('tests/viisp/resources/signed_auth_data_request.xml', 'r') as xmlFile:
        assert xml_string == xmlFile.read()

def test_ticket_id_parsing(app: DjangoTestApp):
    with open('tests/viisp/resources/signed_auth_data_request.xml', 'r') as xmlFile:
        assert '0961ca7d-ac07-47d2-98c7-1968db7dba8f' == _parse_ticket_id(xmlFile.read())

def test_user_data_parsing(app: DjangoTestApp):
    with open('tests/viisp/resources/response_with_user_data.xml', 'r') as xmlFile:
        expected_user_data = {
            'lt_personal_code': 'XXXXXXXXXXX',
            'first_name': 'VARDENIS',
            'last_name': 'PAVARDENIS',
            'company_name': ''
        }
        assert expected_user_data == _parse_user_data(xmlFile.read())
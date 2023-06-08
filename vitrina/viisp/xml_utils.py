from signxml import XMLSigner, XMLVerifier, methods
from signxml.algorithms import SignatureMethod, DigestAlgorithm, CanonicalizationMethod
from lxml import etree as ET
from xml.dom import minidom
from bs4 import BeautifulSoup
from stringcase import snakecase
from requests import post
from vitrina.settings import VIISP_PROXY_AUTH, VIISP_AUTH_PRIVATE_KEY

providers = ('auth.lt.identity.card',
             'auth.lt.bank',
             'auth.signatureProvider',
             'auth.login.pass',
             'auth.lt.government.employee.card',
             'auth.tsl.identity.card',)

attributes = ('lt-personal-code',
              'lt-company-code')

user_information = ('firstName',
                    'lastName',
                    'companyName',)

callback_url = 'http://127.0.0.1:8000/accounts/accounts/viisp/complete-login'
PID = 'VIISP-AUTH-SERVICE-01'
CUSTOM_DATA_PARTNER_REGISTRATION = "adp-partner-registration-req"

envelope = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:aut=\"http://www.epaslaugos.lt/services/authentication\" xmlns:xd=\"http://www.w3.org/2000/09/xmldsig#\">\n" \
           "<soapenv:Header/>\n" \
           "<soapenv:Body>\n" \
           "{}" \
           "</soapenv:Body>\n" \
           "</soapenv:Envelope>"
headers = {
    'Content-Type': 'text/xml; charset=utf-8'
}


def _create_base(base_element_name):
    doc = minidom.Document()
    xml = doc.createElement(base_element_name)
    xml.setAttribute('xmlns:authentication', 'http://www.epaslaugos.lt/services/authentication')
    xml.setAttribute('xmlns:dsig', 'http://www.w3.org/2000/09/xmldsig#')
    xml.setAttribute('xmlns:ns3', 'http://www.w3.org/2001/10/xml-exc-c14n#')
    xml.setAttribute('id', 'uniqueNodeId')
    doc.appendChild(xml)
    return doc, xml

def _add_elements(base, xml, elements, element_name=None, element=None):
    for item in elements:
        if element_name:
            element = base.createElement(element_name)
        element.appendChild(base.createTextNode(item))
        xml.appendChild(element)
    return base

def _sign_xml(xml):
    root = ET.fromstring(xml.toxml())
    signer = XMLSigner(
            method=methods.enveloped, 
            signature_algorithm=SignatureMethod.RSA_SHA1,
            digest_algorithm=DigestAlgorithm.SHA1, 
            c14n_algorithm=CanonicalizationMethod.EXCLUSIVE_XML_CANONICALIZATION_1_0
    )
    ns = {None: signer.namespaces['ds']}
    signer.namespaces = ns
    ET.cleanup_namespaces(root)
    signed_root = signer.sign(root, key=VIISP_AUTH_PRIVATE_KEY, reference_uri="uniqueNodeId")
    return ET.tostring(signed_root, encoding='utf-8')

def _generate_xml(base_element_name):
    base, xml = _create_base(base_element_name)
    pid = base.createElement('authentication:pid')
    pid.appendChild(base.createTextNode(PID))
    xml.appendChild(pid)
    return base, xml

def get_response_with_ticket_id():
    signed_xml = create_signed_authentication_request_xml()
    soap_request = envelope.format(signed_xml)
    resp = post(VIISP_PROXY_AUTH, data=soap_request)
    return _parse_ticket_id(resp.text)

def get_response_with_user_data(ticket_id):
    signed_xml = create_signed_authentication_data_request_xml(ticket_id)
    soap_request = envelope.format(signed_xml)
    resp = post(VIISP_PROXY_AUTH, data=soap_request)
    return _parse_user_data(resp.text)

def create_signed_authentication_request_xml():
    base, xml = _generate_xml('authentication:authenticationRequest')
    _add_elements(base, xml, providers, element_name='authentication:authenticationProvider')
    _add_elements(base, xml, attributes, element_name='authentication:authenticationAttribute')
    _add_elements(base, xml, user_information, element_name='authentication:userInformation')
    _add_elements(base, xml, (callback_url,), element_name='authentication:postbackUrl')
    _add_elements(base, xml, ('correlationData',), element_name='authentication:customData')
    signed_xml = _sign_xml(xml).decode('utf-8')
    return signed_xml

def create_signed_authentication_data_request_xml(ticket_id):
    base, xml = _generate_xml('authentication:authenticationDataRequest')
    ticket = base.createElement('authentication:ticket')
    ticket.appendChild(base.createTextNode(ticket_id))
    xml.appendChild(ticket)
    
    include_source_data = base.createElement('authentication:includeSourceData')
    include_source_data.appendChild(base.createTextNode('true'))
    xml.appendChild(include_source_data)
    signed_xml = _sign_xml(xml).decode('utf-8')
    return signed_xml

def _parse_ticket_id(xml_string):
    soup = BeautifulSoup(xml_string, features='xml')
    ticket = soup.find("ticket")
    if ticket:
        ticket_id = ticket.text
        return ticket_id

def _parse_user_data(xml_string):
    soup = BeautifulSoup(xml_string, features='xml')
    user_information_to_find = ['firstName', 'lastName', 'companyName']
    user_data = {}
    authentication_attribute = soup.find('authenticationAttribute')
    attribute = authentication_attribute.find('attribute').text
    value = authentication_attribute.find('value').text
    user_data[snakecase(attribute)] = value
    user_information_data = soup.find_all('userInformation')
    for u_i_data in user_information_data:
        information = u_i_data.find('information').text
        if information in user_information_to_find:
            user_data[snakecase(information)] = u_i_data.find('value').text 
    return user_data
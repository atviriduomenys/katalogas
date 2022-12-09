import os
import xml
import requests
from cryptography.hazmat.primitives import serialization
from xml.dom import minidom
from requests import Session
from zeep import Transport, Client

pem_file = "../resources/prod-auth.pem"
crt_file = "../resources/VIISP_test.crt"

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

callback_url = 'https://localhost'
PID = 'VSID000000000113'
CUSTOM_DATA_PARTNER_REGISTRATION = "adp-partner-registration-req"

proxyAuth = 'https://test.epaslaugos.lt/portal/services/AuthenticationServiceProxy'
proxyWSDL = 'https://test.epaslaugos.lt/portal/services/AuthenticationServiceProxy?wsdl'

envelope = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:aut=\"http://www.epaslaugos.lt/services/authentication\" xmlns:xd=\"http://www.w3.org/2000/09/xmldsig#\">\n" \
           "<soapenv:Header/>\n" \
           "<soapenv:Body>\n" \
           "{}" \
           "</soapenv:Body>\n" \
           "</soapenv:Envelope>"
headers = {
    'Content-Type': 'text/xml; charset=utf-8'
}


def create_base():
    doc = minidom.Document()

    xml = doc.createElement('authentication:authenticationRequest')
    xml.setAttribute('xmlns:authentication', 'http://www.epaslaugos.lt/services/authentication')
    xml.setAttribute('xmlns:dsig', 'http://www.w3.org/2000/09/xmldsig#')
    xml.setAttribute('xmlns:ns3', 'http://www.w3.org/2001/10/xml-exc-c14n#')
    xml.setAttribute('id', 'uniqueNodeId')
    doc.appendChild(xml)
    return doc, xml


def add_elements(base, xml, elements, element_name=None, element=None):
    for item in elements:
        if element_name:
            element = base.createElement(element_name)
        element.appendChild(base.createTextNode(item))
        xml.appendChild(element)
    return base


def generate_rsa():
    with open("../resources/prod-auth.pem", "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )
    # signature = private_key.sign()
    return private_key


def generate_signature(base, xml):
    signature = base.createElement('Signature')
    signature.setAttribute('xmlns', 'http://www.w3.org/2000/09/xmldsig#')
    xml.appendChild(signature)

    signed_info = base.createElement('signedInfo')
    signature.appendChild(signed_info)

    canonicalization_method = base.createElement('CanonicalizationMethod')
    canonicalization_method.setAttribute('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')
    inclusive_namespaces_1 = base.createElement('InclusiveNamespaces')
    inclusive_namespaces_1.setAttribute('xmlns', 'http://www.w3.org/2001/10/xml-exc-c14n#')
    inclusive_namespaces_1.setAttribute('PrefixList', 'authentication')
    canonicalization_method.appendChild(inclusive_namespaces_1)
    signed_info.appendChild(canonicalization_method)
    signature_method = base.createElement('SignatureMethod')
    signature_method.setAttribute('Algorithm', 'http://www.w3.org/2000/09/xmldsig#rsa-sha1')
    signed_info.appendChild(signature_method)

    reference = base.createElement('Reference')
    reference.setAttribute('URI', '#uniqueNodeId')

    transforms = base.createElement('Transforms')
    reference.appendChild(transforms)

    transform_1 = base.createElement('Transform')
    transform_1.setAttribute('Algorithm', 'http://www.w3.org/2000/09/xmldsig#envelopedsignature')
    transforms.appendChild(transform_1)

    transform_2 = base.createElement('Transform')
    transform_2.setAttribute('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')
    transforms.appendChild(transform_2)

    digest_method = base.createElement('DigestMethod')
    digest_method.setAttribute('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
    reference.appendChild(digest_method)

    digest_value = base.createElement('DigestValue')
    digest_value.appendChild(base.createTextNode('tfwNJctev1wsnd/lLq5a0PzZ2GQ='))
    reference.appendChild(digest_value)

    inclusive_namespaces_2 = base.createElement('InclusiveNamespaces')
    inclusive_namespaces_2.setAttribute('xmlns', 'http://www.w3.org/2001/10/xml-excc14n#')
    inclusive_namespaces_2.setAttribute('PrefixList', 'authentication')
    transform_2.appendChild(inclusive_namespaces_2)
    signed_info.appendChild(reference)

    signature_value = base.createElement('SignatureValue')
    signature_value.appendChild(base.createTextNode("I2eCq37Me1LZ3IpbcgrTB+lIzYgjBPVRVdaAZUXrMVdpnrk9BZpxNJ24rhJeKH1CJD"
                                                    "FzqVq8lGHl0nz3ZupzgQ+KI5XKXMD6QvjO9Stm8NQDXbFN3aJ5zfWciMDHt/TisJj3"
                                                    "zLmstlY0QrWFY80EoYigxDrcS9IESNdgq/PtgwC+0AXL5ZMQQKl6m20+l0hkV7NaoE"
                                                    "SZa4NvEO4ad/UW11zSU08RZSpzTKQ749JK5W0AqUweLsCdrHywlFJdCpJcoOLh29wp"
                                                    "dlvDrX/6u4VTqHxz+7QCyDHXcRCBJvicvETd4V6Q3CQqUZgS24IFc2rkIjtxNISdnE"
                                                    "rdSauM6AFpuQ=="))
    signature.appendChild(signature_value)

    key_info = base.createElement('KeyInfo')
    key_value = base.createElement('KeyValue')
    rsa_key_value = base.createElement('RSAKeyValue')
    modulus = base.createElement('Modulus')
    RSAValue = generate_rsa()
    modulus.appendChild(base.createTextNode(RSAValue))
    exponent = base.createElement("Exponent")
    exponent.appendChild(base.createTextNode('AQAB'))
    key_info.appendChild(key_value)
    key_value.appendChild(rsa_key_value)
    rsa_key_value.appendChild(modulus)
    rsa_key_value.appendChild(exponent)
    signature.appendChild(key_info)
    return xml


def generate_xml():
    base, xml = create_base()
    pid = base.createElement('authentication:pid')
    pid.appendChild(base.createTextNode(PID))
    xml.appendChild(pid)

    add_elements(base, xml, providers, element_name='authentication:authenticationProvider')
    add_elements(base, xml, attributes, element_name='authentication:authenticationAttribute')
    add_elements(base, xml, user_information, element_name='authentication:userInformation')
    add_elements(base, xml, (callback_url,), element_name='authentication:postbackUrl')
    add_elements(base, xml, ('correlationData',), element_name='authentication:customData')
    generate_signature(base, xml)
    return xml


def get_response_with_ticketid(xml):
    soap_request = envelope.format(xml.toprettyxml())
    # session = Session()
    # session.verify = pem_file
    # transport = Transport(session=session)
    # client = Client(proxyAuth, transport=transport)
    # resp = client.service.initAuthentication(soap_request)
    resp = requests.post(proxyAuth, data=soap_request)
    return resp


if __name__ == '__main__':
    viisp_request = generate_xml()
    # print(viisp_request.toprettyxml(indent='  '))
    response = get_response_with_ticketid(viisp_request)

    xml_string = xml.dom.minidom.parseString(response.text)
    xml_string = xml_string.toprettyxml()
    xml_string = os.linesep.join([s for s in xml_string.splitlines() if s.strip()])
    print(xml_string)
    print(response)

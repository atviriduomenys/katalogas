from xml.dom import minidom

providers = ('auth.lt.identity.card',
             'auth.lt.bank',
             'auth.signatureProvider',
             'auth.login.pass',
             'auth.lt.government.employee.card',
             'auth.tsl.identity.card',)

user_information = ('firstName',
                    'lastName',
                    'companyName',)

callback_url = 'http://127.0.0.1:8000/'
PID = 'VSID000000000113'


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
    transform_1.setAttribute('Algorithm', 'http://www.w3.org/2000/09/xmldsig#enveloped-signature')
    transforms.appendChild(transform_1)

    transform_2 = base.createElement('Transform')
    transform_2.setAttribute('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')
    transforms.appendChild(transform_2)

    inclusive_namespaces_2 = base.createElement('InclusiveNamespaces')
    inclusive_namespaces_2.setAttribute('xmlns', 'http://www.w3.org/2001/10/xml-exc-c14n#')
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
    rsa_key_value = base.createElement('RASKeyValue')
    modulus = base.createElement('Modulus')
    modulus.appendChild(base.createTextNode("i+rh6NJ7Z6Q8XiMSVK/Z8DYXIyk5j7N9GUX8AOSKONabse4us7/ogR0x7OOf0FsrdxAhQls59W"
                                            "n1vDxujSVOu3v1JhML/v/WK8glcxM433oEEpb0C56XRHlt27Qkbsn6v3njC1z0NGyDFdAtg5Pa"
                                            "Mx7YmjyWR6ezMKj9wR5cK4CRZ7idm2PwzQaLUDFm7wUFXudZNkQ6pb60OvDw4ey1t68EVCPtq4"
                                            "nGdHG+3jlSDTTJc/03qk50pa6Nb/t5+EWsE3jFt/uhHim1rC2pMf5UrT26FL6/DjA0PxQFecc7"
                                            "6zeuv3xbGSP7B7ubpG8fyatGb4oLB4eU0ceCJvqljGMP0w=="))
    exponent = base.createElement("Exponent")
    exponent.appendChild(base.createTextNode('AQAB'))
    key_info.appendChild(rsa_key_value)
    rsa_key_value.appendChild(modulus)
    rsa_key_value.appendChild(exponent)
    signature.appendChild(key_info)
    return base


def generate_xml():
    base, xml = create_base()
    pid = base.createElement('authentication:pid')
    pid.appendChild(base.createTextNode(PID))
    xml.appendChild(pid)

    add_elements(base, xml, providers, element_name='authentication:authenticationProvider')
    add_elements(base, xml, user_information, element_name='authentication:userInformation')
    add_elements(base, xml, (callback_url,), element_name='authentication:postbackUrl')
    add_elements(base, xml, ('correlationData',), element_name='authentication:customData')
    generate_signature(base, xml)
    print(base.toprettyxml(indent='  '))


if __name__ == '__main__':
    generate_xml()

import pytest
from pathlib import Path
from lxml import etree
from cryptography import x509
from base64 import b64decode

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.smart_contracts.models import Agreement
from vitrina.smart_contracts.services import SAFE_PARSER, SIGNATURE_NAMESPACES


AGREEMENT_ONE_SIGNER = "agreement_one_signer.adoc"
AGREEMENT_TWO_SIGNERS = "agreement_two_signers.adoc"
AGREEMENT_NO_MANIFEST = "agreement_no_manifest.adoc"
AGREEMENT_BAD_CERTIFICATE = "agreement_bad_certificate.adoc"
AGREEMENT_MODIFIED = "agreement_modified.adoc"
AGREEMENT_NO_PDF = "agreement_no_pdf.adoc"
AGREEMENT_TWO_FILES = "agreement_two_files.adoc"
AGREEMENT_NOT_SIGNED = "agreement_not_signed.adoc"
AGREEMENT_PDF = "agreement.pdf"
AGREEMENT_NON_ZIP = "agreement_non_zip.adoc"
SIGNATURE1_XML = "signature1.xml"
SIGNATURE2_XML = "signature2.xml"
ODRL_JSON = "odrl_json.json"
ODRL_JSON_WRONG_REPRESENTATIVES = "odrl_json_wrong_representatives.json"
CERTIFICATE_ENCODED = "MIIDmTCCAoGgAwIBAgIUaLdzz3xpaILbhXheDmvmLPQa2oMwDQYJKoZIhvcNAQELBQAwfDELMAkGA1UEBhMCTFQxETAPBgNVBAoMCFRlc3QgT3JnMREwDwYDVQQqDAhWYXJkZW5pczETMBEGA1UEBAwKUGF2YXJkZW5pczEcMBoGA1UEAwwTVmFyZGVuaXMgUGF2YXJkZW5pczEUMBIGA1UEBRMLNTEyMzQ1Njc4OTAwHhcNMjUxMTEwMDkzNDIyWhcNMjYxMTExMDkzNDIyWjB8MQswCQYDVQQGEwJMVDERMA8GA1UECgwIVGVzdCBPcmcxETAPBgNVBCoMCFZhcmRlbmlzMRMwEQYDVQQEDApQYXZhcmRlbmlzMRwwGgYDVQQDDBNWYXJkZW5pcyBQYXZhcmRlbmlzMRQwEgYDVQQFEws1MTIzNDU2Nzg5MDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAPrD+mSs83HlCX0xg7GECwak/xRh7BM0xRIwjodgTEotQRZ67CP5cxevRMmiNUMWnb8kbOFyWLM/32gSt3YKNQ/F7cM0cjf08KaaKOvv1Aufy4xrC8MT5BeLBq9UwvoofL0asB+2+lJqOKXy5+ecmfmzzEgGOKMe5RsZl+Vp8lyO1m9nNe458Ro8W+f1QWJ6slx3u+2NTy+C140YBXK28et7ZYURXOe46Mmwxap0HYy6N2HWWqRCmwjBeLTWHvkAKn2szBZRAOBz3Kb9gem5AbzA9Y05uIpR9S6MsQQxy8TB5C3AP/ipPo+JWE6Zl49YQkCJVRQyoXyaJQFNvB5ZlKMCAwEAAaMTMBEwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAF0J+yC3e63snyxgnAA7PwGWx+enqKbdm2ulKqm5GEIlbTS9TF5zGe3zCnZaHcG1taE6b9CmicUPc1G+MPidBoLCnA5iFEl8mlcVTuF+XsLHXgSlNn3OHrQKYPioW20nUxydPh7TKQbSi2I3lgkdfmBnmJZnWoGyPnBp3rTFvAgxQ7Oy4jDx9vRI/8NEl8+WEUYb9Qz0w+60m+fB9T1uIZwXhF5yg+WnnXfjN80tZaYxf4Z/1gofaLW+/OnVa3aEKVgy8EMHWxfpHdPNxFhhaf0vwBiPFOpDHotd77uDImvdoZIjWLoqPYCkA7KCJixhe3YKXMNMYv6Hc7of8x1z1iQ=="
CERTIFICATE_ENCODED_NO_FIRST_NAME = "MIIDYDCCAkigAwIBAgIUTYRskZt1nD+2Vve33O80oMylCFwwDQYJKoZIhvcNAQELBQAwajELMAkGA1UEBhMCTFQxEDAOBgNVBAgMB1ZpbG5pdXMxEDAOBgNVBAcMB1ZpbG5pdXMxFTATBgNVBAoMDEV4YW1wbGUgQ29ycDELMAkGA1UECwwCSVQxEzARBgNVBAMMClBhdmFyZGVuaXMwHhcNMjUxMTE4MTIyNjAzWhcNMjYxMTE5MTIyNjAzWjBqMQswCQYDVQQGEwJMVDEQMA4GA1UECAwHVmlsbml1czEQMA4GA1UEBwwHVmlsbml1czEVMBMGA1UECgwMRXhhbXBsZSBDb3JwMQswCQYDVQQLDAJJVDETMBEGA1UEAwwKUGF2YXJkZW5pczCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMr8U7k8vRo94KCdPteMjbPe4WTRfgELpEo1zom0Kd3451ZHyBSrAbiL4LUOMMX2vdGmm7km6kgexfkZDy5rWqkSHiCW/ndxK0kCuD4IYe1XH4/kVIUDMuqt6K7KVGrSteRJ4vhU5T4dOXCq/TyELBt7oCHQh6KV4bwtXuchbpV8tctXTVcoi6d2YD+PHTI3+f+CzTG2VCW9V9yLnTLnqlUeoGEwovLiJgqzha6CO4RLkdaQ0gtyYdrDhPzA1TaiherI8CyFWYIVdUiSRMpAop7Xj57/iCPY297j3FsPnLYNjS66XFFrov6ONmCFgPFFztRR9P3qpZmNhxrgtxjQlykCAwEAATANBgkqhkiG9w0BAQsFAAOCAQEAfyN3XAb/2PjbfoB34bzfmQIc9/qx3jyLduy67KnJ0J+i/cbas6mQi/LKOGE4lgKpr2APqZNyA3HBtapdfjW0VvSKKCYZPbr7mlEboKWsXhW5H6g0N/fG3BtAYx94he3tJrH3a7m01pwz0Wz8igN7uQ3SZ3KS9QuU0ziWz/K9srbNZ1rZsSsVqMFUTcXiLfjIXQjkOtfyXs4MwcTKUVpa/0U+a/iHrQUzdeSxXTGhw06Go/o21dLfHy1P0YfMeVmiO+Jx2fUBnEuUEgOQVTMfWLXedUaaJ1z+sl1dWhfPXV1xcZMaL0sgf+sHJwJKfOUBTSYgtOsmpVcqdzcaAxLC7w=="


@pytest.fixture
def organization() -> Organization:
    return OrganizationFactory()


@pytest.fixture
def dataset(organization: Organization) -> Dataset:
    return DatasetFactory(organization=organization, metadata="test/dataset")


@pytest.fixture
def test_files_dir() -> Path:
    return Path(__file__).resolve().parent / "files"


@pytest.fixture
def agreements_dir(test_files_dir: Path) -> Path:
    return test_files_dir / "test_contracts"


@pytest.fixture
def signatures_dir(test_files_dir: Path) -> Path:
    return test_files_dir / "signatures"


@pytest.fixture
def agreement_one_signer(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_ONE_SIGNER


@pytest.fixture
def agreement_two_signers(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_TWO_SIGNERS


@pytest.fixture
def agreement_no_manifest(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_NO_MANIFEST


@pytest.fixture
def agreement_bad_certificate(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_BAD_CERTIFICATE


@pytest.fixture
def agreement_modified(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_MODIFIED


@pytest.fixture
def agreement_no_pdf(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_NO_PDF


@pytest.fixture
def agreement_two_files(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_TWO_FILES


@pytest.fixture
def agreement_not_signed(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_NOT_SIGNED


@pytest.fixture
def agreement_pdf(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_PDF


@pytest.fixture
def agreement_non_zip(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_NON_ZIP


@pytest.fixture
def odrl_json(test_files_dir: Path) -> Path:
    return test_files_dir / ODRL_JSON


@pytest.fixture
def odrl_json_wrong_representatives(test_files_dir: Path) -> Path:
    return test_files_dir / ODRL_JSON_WRONG_REPRESENTATIVES


@pytest.fixture
def agreement_choice(request):
    return request.getfixturevalue(request.param)


@pytest.fixture
def signature1(signatures_dir: Path) -> etree._Element:
    tree = etree.parse(signatures_dir / SIGNATURE1_XML, parser=SAFE_PARSER)
    return tree.xpath("//ds:Signature", namespaces=SIGNATURE_NAMESPACES)[0]


@pytest.fixture
def signature2(signatures_dir: Path) -> etree._Element:
    tree = etree.parse(signatures_dir / SIGNATURE2_XML, parser=SAFE_PARSER)
    return tree.xpath("//ds:Signature", namespaces=SIGNATURE_NAMESPACES)[0]


@pytest.fixture
def certificate() -> x509.Certificate:
    return x509.load_der_x509_certificate(b64decode(CERTIFICATE_ENCODED))


@pytest.fixture
def certificate_no_first_name() -> x509.Certificate:
    return x509.load_der_x509_certificate(b64decode(CERTIFICATE_ENCODED_NO_FIRST_NAME))


@pytest.fixture
def agreement() -> Agreement:
    return AgreementFactory()

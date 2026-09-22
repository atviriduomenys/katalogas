import uuid
from urllib.parse import urlparse

# Spintos instancijos identifikatorius, kurį Spinta naudoja kaip JWT `aud` reikšmę.
AGENT_INSTANCE_URI_PREFIX = "https://data.gov.lt/id/dcat/Agent/"


def extract_type_from_url(url: str) -> str:
    """Method used to extract `_type` (as defined in https://ivpk.github.io/uapi/#section/Concepts/Model) from a URL."""
    path = urlparse(url).path.rstrip("/")

    return path if path.startswith("/uapi/") else ""


def generate_agent_instance_uri() -> str:
    return f"{AGENT_INSTANCE_URI_PREFIX}{uuid.uuid4()}"

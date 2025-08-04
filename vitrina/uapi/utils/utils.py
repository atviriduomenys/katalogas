from urllib.parse import urlparse


def extract_type_from_url(url: str) -> str:
    """Method used to extract `_type` (as defined in https://ivpk.github.io/uapi/#section/Concepts/Model) from a URL."""
    path = urlparse(url).path.rstrip("/")

    return path if path.startswith("/uapi/") else ""

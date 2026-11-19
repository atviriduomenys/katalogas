from dataclasses import dataclass

import requests
from django.conf import settings
from django.utils.translation import gettext as _

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
QUERY_TIMEOUT_SECONDS = 15


class SparqlError(Exception):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class SparqlResponse:
    content_type: str
    body: bytes


def run_query(query: str, accept: str) -> SparqlResponse:
    unavailable = SparqlError(_("SPARQL paslauga šiuo metu nepasiekiama."), status=503)
    if not settings.FUSEKI_URL:
        raise unavailable
    try:
        with requests.post(
            f"{settings.FUSEKI_URL}/sparql",
            data={"query": query},
            headers={"Accept": accept},
            timeout=QUERY_TIMEOUT_SECONDS,
            stream=True,
        ) as response:
            body = response.raw.read(MAX_RESPONSE_BYTES + 1, decode_content=True)
    except requests.RequestException as error:
        raise unavailable from error
    if response.status_code == 503:
        raise SparqlError(
            _("Užklausa vykdoma per ilgai. Supaprastinkite užklausą arba sumažinkite LIMIT reikšmę."), status=503
        )
    if response.status_code >= 400:
        raise SparqlError(body.decode(errors="replace"), status=response.status_code)
    if len(body) > MAX_RESPONSE_BYTES:
        raise SparqlError(_("Užklausos rezultatas per didelis. Sumažinkite LIMIT reikšmę."), status=400)
    return SparqlResponse(response.headers.get("Content-Type", "text/plain"), body)

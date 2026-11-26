import io
import json
from urllib.parse import parse_qs

import pytest
import requests
import urllib3

from vitrina.sparql import services

FUSEKI_URL = "http://fuseki:3030/katalogas"
QUERY_URL = f"{FUSEKI_URL}/sparql"
HTML = {"Accept": "text/html,application/xhtml+xml"}

SELECT_RESULT = {
    "head": {"vars": ["dataset", "title"]},
    "results": {
        "bindings": [
            {
                "dataset": {"type": "uri", "value": "https://data.gov.lt/datasets/1/"},
                "title": {"type": "literal", "value": "Oro uostai", "xml:lang": "lt"},
            },
            {
                "dataset": {"type": "uri", "value": "javascript:alert(1)"},
            },
        ]
    },
}


@pytest.fixture(autouse=True)
def fuseki_url(settings):
    settings.FUSEKI_URL = FUSEKI_URL


def mock_json_result(requests_mock, result: dict):
    return requests_mock.post(
        QUERY_URL,
        content=json.dumps(result).encode(),
        headers={"Content-Type": "application/sparql-results+json; charset=utf-8"},
    )


@pytest.mark.django_db
def test_page_without_query_shows_the_form_and_examples(app, requests_mock):
    response = app.get("/sparql/", headers=HTML)

    assert response.status_code == 200
    assert response.forms["sparql-form"].method.lower() == "get"
    assert response.html.select("a.sparql-example")
    assert not requests_mock.called


@pytest.mark.django_db
def test_select_result_shows_a_table(app, requests_mock):
    mock_json_result(requests_mock, SELECT_RESULT)

    response = app.get("/sparql/", {"query": "SELECT * WHERE { ?s ?p ?o }"}, headers=HTML)

    sent = parse_qs(requests_mock.last_request.text)
    assert sent["query"] == ["SELECT * WHERE { ?s ?p ?o }"]
    assert "application/sparql-results+json" in requests_mock.last_request.headers["Accept"]
    headers = [th.text.strip() for th in response.html.select("table.sparql-result th")]
    assert headers == ["dataset", "title"]
    rows = response.html.select("table.sparql-result tbody tr")
    assert [td.text.strip() for td in rows[0].select("td")] == ["https://data.gov.lt/datasets/1/", "Oro uostai"]
    assert rows[0].select_one("a")["href"] == "https://data.gov.lt/datasets/1/"
    assert [td.text.strip() for td in rows[1].select("td")] == ["javascript:alert(1)", ""]
    assert rows[1].select_one("a") is None


@pytest.mark.django_db
def test_ask_result_shows_the_answer(app, requests_mock):
    mock_json_result(requests_mock, {"head": {}, "boolean": True})

    response = app.get("/sparql/", {"query": "ASK { ?s ?p ?o }"}, headers=HTML)

    assert response.html.select_one(".sparql-boolean").text.strip() == "true"


@pytest.mark.django_db
def test_construct_result_shows_the_graph_as_text(app, requests_mock):
    turtle = "<https://data.gov.lt/datasets/1/> a <http://www.w3.org/ns/dcat#Dataset> ."
    requests_mock.post(QUERY_URL, text=turtle, headers={"Content-Type": "text/turtle"})

    response = app.get("/sparql/", {"query": "CONSTRUCT WHERE { ?s ?p ?o }"}, headers=HTML)

    assert response.html.select_one("pre.sparql-result").text == turtle


@pytest.mark.django_db
def test_query_error_shows_the_fuseki_message(app, requests_mock):
    requests_mock.post(QUERY_URL, status_code=400, text="Parse error: Encountered EOF")

    response = app.get("/sparql/", {"query": "SELECT"}, headers=HTML)

    assert "Parse error: Encountered EOF" in response.html.select_one(".message-body").text


@pytest.mark.django_db
def test_query_timeout_shows_an_error(app, requests_mock):
    requests_mock.post(QUERY_URL, status_code=503, text="Query timed out")

    response = app.get("/sparql/", {"query": "SELECT * WHERE { ?a ?b ?c . ?d ?e ?f }"}, headers=HTML)

    assert response.html.select_one(".message-body").text.strip() == (
        "Užklausa vykdoma per ilgai. Supaprastinkite užklausą arba sumažinkite LIMIT reikšmę."
    )


@pytest.mark.django_db
def test_unreachable_fuseki_shows_an_error(app, requests_mock):
    requests_mock.post(QUERY_URL, exc=requests.ConnectionError)

    response = app.get("/sparql/", {"query": "ASK {}"}, headers=HTML)

    assert response.status_code == 200
    assert response.html.select_one(".message-body").text.strip() == "SPARQL paslauga šiuo metu nepasiekiama."


class BrokenBody(io.BytesIO):
    def read(self, *args, **kwargs):
        raise urllib3.exceptions.ProtocolError("Connection broken")


@pytest.mark.django_db
def test_broken_connection_while_reading_shows_an_error(app, requests_mock):
    requests_mock.post(QUERY_URL, body=BrokenBody(), headers={"Content-Type": "text/turtle"})

    response = app.get("/sparql/", {"query": "CONSTRUCT WHERE { ?s ?p ?o }"}, headers=HTML)

    assert response.html.select_one(".message-body").text.strip() == "SPARQL paslauga šiuo metu nepasiekiama."


@pytest.mark.django_db
def test_missing_fuseki_url_shows_an_error(app, settings, requests_mock):
    settings.FUSEKI_URL = ""

    response = app.get("/sparql/", {"query": "ASK {}"}, headers=HTML)

    assert response.html.select_one(".message-body").text.strip() == "SPARQL paslauga šiuo metu nepasiekiama."
    assert not requests_mock.called


@pytest.mark.django_db
def test_too_large_result_shows_an_error(app, requests_mock, monkeypatch):
    monkeypatch.setattr(services, "MAX_RESPONSE_BYTES", 10)
    requests_mock.post(QUERY_URL, text="x" * 11, headers={"Content-Type": "text/turtle"})

    response = app.get("/sparql/", {"query": "CONSTRUCT WHERE { ?s ?p ?o }"}, headers=HTML)

    assert "per didelis" in response.html.select_one(".message-body").text
    assert response.html.select_one("pre.sparql-result") is None


@pytest.mark.django_db
def test_sparql_client_gets_the_raw_fuseki_response(app, requests_mock):
    mock_json_result(requests_mock, SELECT_RESULT)

    response = app.get(
        "/sparql/",
        {"query": "SELECT * WHERE { ?s ?p ?o }"},
        headers={"Accept": "application/sparql-results+json"},
    )

    assert requests_mock.last_request.headers["Accept"] == "application/sparql-results+json"
    assert response.content_type == "application/sparql-results+json"
    assert response.json == SELECT_RESULT


@pytest.mark.django_db
def test_sparql_client_gets_the_fuseki_status_on_error(app, requests_mock):
    requests_mock.post(QUERY_URL, status_code=400, text="Parse error")

    response = app.get(
        "/sparql/",
        {"query": "SELECT"},
        headers={"Accept": "application/sparql-results+json"},
        expect_errors=True,
    )

    assert response.status_code == 400
    assert response.text == "Parse error"


@pytest.mark.django_db
def test_sparql_client_gets_503_when_fuseki_is_unreachable(app, requests_mock):
    requests_mock.post(QUERY_URL, exc=requests.ConnectionError)

    response = app.get(
        "/sparql/",
        {"query": "ASK {}"},
        headers={"Accept": "application/sparql-results+json"},
        expect_errors=True,
    )

    assert response.status_code == 503

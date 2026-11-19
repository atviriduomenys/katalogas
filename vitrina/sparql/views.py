import json

from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_vary_headers
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from vitrina.sparql.services import SparqlError, SparqlResponse, run_query

SPARQL_RESULTS_JSON = "application/sparql-results+json"
HTML_PAGE_ACCEPT = f"{SPARQL_RESULTS_JSON}, text/turtle;q=0.9, */*;q=0.1"

PREFIXES = """PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
"""

EXAMPLES = [
    (
        _("Duomenų rinkiniai ir jų pavadinimai"),
        PREFIXES
        + """
SELECT ?dataset ?title WHERE {
  ?dataset a dcat:Dataset ;
           dct:title ?title .
  FILTER(LANG(?title) = "lt")
}
LIMIT 100""",
    ),
    (
        _("Transporto duomenų rinkiniai su CC BY 4.0 licencija"),
        PREFIXES
        + """
SELECT DISTINCT ?dataset ?title WHERE {
  ?dataset a dcat:Dataset ;
           dct:title ?title ;
           dcat:theme <http://publications.europa.eu/resource/authority/data-theme/TRAN> ;
           dcat:distribution/dct:license <https://creativecommons.org/licenses/by/4.0/deed.lt> .
  FILTER(LANG(?title) = "lt")
}
LIMIT 100""",
    ),
    (
        _("Organizacijos pagal duomenų rinkinių skaičių"),
        PREFIXES
        + """
SELECT ?publisher (COUNT(DISTINCT ?dataset) AS ?datasets) WHERE {
  ?dataset a dcat:Dataset ;
           dct:publisher/foaf:name ?publisher .
}
GROUP BY ?publisher
ORDER BY DESC(?datasets)
LIMIT 100""",
    ),
]


def _cell(term: dict | None) -> dict:
    if term is None:
        return {"value": "", "link": False}
    value = term["value"]
    return {"value": value, "link": term["type"] == "uri" and value.startswith(("http://", "https://"))}


def _result_context(result: SparqlResponse) -> dict:
    if not result.content_type.startswith(SPARQL_RESULTS_JSON):
        return {"text": result.body.decode(errors="replace")}
    data = json.loads(result.body)
    if "boolean" in data:
        return {"boolean": data["boolean"]}
    columns = data["head"]["vars"]
    rows = [[_cell(binding.get(column)) for column in columns] for binding in data["results"]["bindings"]]
    return {"columns": columns, "rows": rows}


class SparqlView(TemplateView):
    template_name = "vitrina/sparql/sparql.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        query = request.GET.get("query", "").strip()
        accept = request.headers.get("Accept", "")
        if query and "text/html" not in accept and accept not in ("", "*/*"):
            response = self._raw_response(query, accept)
        else:
            response = self.render_to_response(self.get_context_data(**self._page_context(query)))
        patch_vary_headers(response, ["Accept"])
        return response

    def _page_context(self, query: str) -> dict:
        context = {"query": query or EXAMPLES[0][1], "examples": EXAMPLES}
        if query:
            try:
                context.update(_result_context(run_query(query, HTML_PAGE_ACCEPT)))
            except SparqlError as error:
                context["error"] = error.message
        return context

    def _raw_response(self, query: str, accept: str) -> HttpResponse:
        try:
            result = run_query(query, accept)
        except SparqlError as error:
            return HttpResponse(error.message, status=error.status, content_type="text/plain; charset=utf-8")
        return HttpResponse(result.body, content_type=result.content_type)

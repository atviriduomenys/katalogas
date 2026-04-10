from xml.sax import SAXParseException

import requests
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import QuerySet

from django.utils.translation import gettext_lazy as _
from rdflib import Graph, URIRef, SKOS, Node, DC

from vitrina.classifiers.models import ConceptSchema, Concept

EUVOC_START_DATE = URIRef("http://publications.europa.eu/ontology/euvoc#startDate")

DOWNLOAD_LANGUAGES = ("lt", "en")

ErrorType = str | None


class RDFConceptDownloader:
    __processed_concepts: dict
    __errors: dict

    def __init__(self) -> None:
        self.__processed_concepts = {}
        self.__errors = {}

    def __reset_results(self) -> None:
        self.__processed_concepts = {}
        self.__errors = {}

    @staticmethod
    def _is_downloadable(uri: str) -> bool:
        try:
            validator = URLValidator()
            validator(uri)
            return True
        except ValidationError:
            return False

    def _download_rdf(self, uri: str) -> bytes | None:
        try:
            response = requests.get(uri, headers={"Accept": "application/rdf+xml"}, timeout=3)
            response.raise_for_status()
        except requests.RequestException as err:
            self.__errors[uri] = _("Nepavyko gauti uri: {}. Klaida: {}.").format(uri, str(err))
            return None

        return response.content

    def _check_and_download_uri(self, uri: str) -> bytes | None:
        if not self._is_downloadable(uri):
            self.__errors[uri] = _("{} nėra validus URI.").format(uri)
            return None

        if (rdf_data := self._download_rdf(uri)) is None:
            # self.__errors[uri] = _("Nepavyko gauti uri: {}. Uri atsakymas tuščias.").format(uri)
            return None
        elif rdf_data == "":
            self.__errors[uri] = _("Nepavyko gauti uri: {}. Uri atsakymas tuščias.").format(uri)
            return None

        return rdf_data

    def _create_graph(self, uri: str, rdf_data: bytes) -> Graph | None:
        try:
            graph = Graph()
            graph.parse(data=rdf_data, format="xml")
        except SAXParseException:
            self.__errors[uri] = _("Nepavyko gauti uri: {}. Gautas rezultatas nėra RDF formato.").format(uri)
            return None

        return graph

    def _parse_concept_schema_uri(self, schema_uri: str, schema_rdf_data: bytes) -> set[Node] | None:
        """
        Get all concept uri from RDF. Concept URIs have SKOS.hasTopConcept or SKOS.topConceptOf namespace
        """

        if (schema_graph := self._create_graph(schema_uri, schema_rdf_data)) is None:
            return None

        schema_uri_ref = URIRef(schema_uri)
        if not (concept_uris := set(schema_graph.objects(schema_uri_ref, SKOS.hasTopConcept))):
            # Some RDFs might have the relation reversed
            concept_uris = set(schema_graph.subjects(SKOS.topConceptOf, schema_uri_ref))

        if not concept_uris:
            self.__errors[schema_uri] = _('Sąvokų schemoje {} nerasta jokių "{}" elementų.').format(
                schema_uri, SKOS.topConceptOf
            )
            return None

        return concept_uris

    def _parse_concept_uri(self, concept_uri: URIRef, concept_rdf_data: bytes, concept_schema: ConceptSchema) -> None:
        labels = {}
        descriptions = {}

        if (concept_graph := self._create_graph(concept_uri, concept_rdf_data)) is None:
            return

        code = next(concept_graph.objects(concept_uri, DC.identifier), None)
        if not code:
            self.__errors[str(concept_uri)] = _('Sąvokoje {} nerastas "{}" elementas.').format(
                str(concept_uri), DC.identifier
            )
            return

        valid_since = next(concept_graph.objects(concept_uri, EUVOC_START_DATE), None)
        if not valid_since:
            self.__errors[str(concept_uri)] = _('Sąvokoje {} nerastas "{}" elementas.').format(
                str(concept_uri), EUVOC_START_DATE
            )
            return

        for label in concept_graph.objects(concept_uri, SKOS.prefLabel):
            if label.language in DOWNLOAD_LANGUAGES:
                labels[label.language] = str(label)

        for description in concept_graph.objects(concept_uri, SKOS.definition):
            if description.language in DOWNLOAD_LANGUAGES:
                descriptions[description.language] = str(description)

        # Fallback: if en exists but lt does not, copy en to lt
        if "en" in labels and "lt" not in labels:
            labels["lt"] = labels["en"]
        if "en" in descriptions and "lt" not in descriptions:
            descriptions["lt"] = descriptions["en"]

        concept_obj, created = Concept.objects.update_or_create(
            code=str(code),
            defaults={
                "uri": str(concept_uri),
                "valid_since": valid_since.toPython(),
            },
        )

        for lang in DOWNLOAD_LANGUAGES:
            if lang in labels or lang in descriptions:
                concept_obj.set_current_language(lang)
                if lang in labels:
                    concept_obj.label = labels[lang]
                if lang in descriptions:
                    concept_obj.description = descriptions.get(lang, "")

        concept_obj.save()
        concept_obj.concept_schemas.add(concept_schema)

        self.__processed_concepts[str(concept_uri)] = concept_obj

    def from_schemas(self, concept_schema_queryset: QuerySet[ConceptSchema]) -> tuple[list, list]:
        self.__reset_results()

        for concept_schema in concept_schema_queryset.filter(uri__isnull=False):
            if (rdf_data := self._check_and_download_uri(concept_schema.uri)) is None:
                continue

            if (concept_uris := self._parse_concept_schema_uri(concept_schema.uri, rdf_data)) is None:
                continue

            for concept_uri in concept_uris:
                if not isinstance(concept_uri, URIRef):
                    continue

                uri_str = str(concept_uri)
                if uri_str in self.__processed_concepts:
                    concept_obj = self.__processed_concepts[uri_str]
                    concept_obj.concept_schemas.add(concept_schema)
                    continue

                if (rdf_data := self._check_and_download_uri(uri_str)) is None:
                    continue

                self._parse_concept_uri(concept_uri, rdf_data, concept_schema)

        return list(self.__processed_concepts.keys()), list(self.__errors.values())

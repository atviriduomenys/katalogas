from datetime import date
from unittest.mock import patch, Mock

import pytest
import requests

from vitrina.classifiers.factories import ConceptSchemaFactory, ConceptFactory
from vitrina.classifiers.models import ConceptSchema, Concept
from vitrina.classifiers.schema_download import RDFConceptDownloader


pytestmark = pytest.mark.django_db


def test_do_nothing_if_concept_schema_queryset_is_empty():
    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(ConceptSchema.objects.none())

    assert success_uris == []
    assert errors == []


def test_error_if_concept_schema_is_not_valid_url():
    concept_schema = ConceptSchemaFactory(uri="test")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == ["test nėra validus URI."]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_request_to_concept_schema_uri_fails(request_mock: Mock):
    response_mock = Mock()
    response_mock.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    request_mock.return_value = response_mock

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == ["Nepavyko gauti uri: https://www.foo.bar. Klaida: 500 Server Error."]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_request_to_concept_schema_uri_times_out(request_mock: Mock):
    request_mock.side_effect = requests.exceptions.Timeout

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == ["Nepavyko gauti uri: https://www.foo.bar. Klaida: ."]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_request_succeeds_but_is_empty(request_mock: Mock):
    response_mock = Mock()
    response_mock.content = ""
    request_mock.return_value = response_mock

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == ["Nepavyko gauti uri: https://www.foo.bar. Uri atsakymas tuščias."]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_response_data_is_not_rdf_data(request_mock: Mock):
    response_mock = Mock()
    response_mock.content = "test"
    request_mock.return_value = response_mock

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == ["Nepavyko gauti uri: https://www.foo.bar. Gautas rezultatas nėra RDF formato."]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_concept_schema_rdf_does_not_have_any_concept_uris(request_mock: Mock):
    response_mock = Mock()
    response_mock.content = "<rdf></rdf>"
    request_mock.return_value = response_mock

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == [
        'Sąvokų schemoje https://www.foo.bar nerasta jokių "http://www.w3.org/2004/02/skos/core#topConceptOf" elementų.'
    ]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_concept_is_not_uri(request_mock: Mock):
    response_mock = Mock()
    response_mock.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="test2" />
            </rdf:Description>
            <rdf:Description rdf:about="test2">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    request_mock.return_value = response_mock

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == ["test2 nėra validus URI."]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_cannot_download_concept(request_mock: Mock):
    mock_schema_response = Mock()
    mock_schema_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar2" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar2">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    mock_concept_response = Mock()
    mock_concept_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    request_mock.side_effect = [mock_schema_response, mock_concept_response]

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == ["https://www.foo2.bar2 nėra validus URI."]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_concept_data_is_not_rdf_data(request_mock: Mock):
    mock_schema_response = Mock()
    mock_schema_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    mock_concept_response = Mock()
    mock_concept_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    request_mock.side_effect = [mock_schema_response, mock_concept_response]

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == ["Nepavyko gauti uri: https://www.foo2.bar. Klaida: 500 Server Error."]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_identifier_not_found_in_rdf_data(request_mock: Mock):
    mock_schema_response = Mock()
    mock_schema_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    mock_concept_response = Mock()
    mock_concept_response.content = "<RDF></RDF>"
    request_mock.side_effect = [mock_schema_response, mock_concept_response]

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == ['Sąvokoje https://www.foo2.bar nerastas "http://purl.org/dc/elements/1.1/identifier" elementas.']


@patch("vitrina.classifiers.schema_download.requests.get")
def test_error_if_start_date_not_found_in_rdf_data(request_mock: Mock):
    mock_schema_response = Mock()
    mock_schema_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    mock_concept_response = Mock()
    mock_concept_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#" xmlns:dc="http://purl.org/dc/elements/1.1/">
            <rdf:Description rdf:about="https://www.foo2.bar">
                <dc:identifier>IDENTIFY</dc:identifier>
            </rdf:Description>
        </rdf:RDF>
        """
    request_mock.side_effect = [mock_schema_response, mock_concept_response]

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == []
    assert errors == [
        'Sąvokoje https://www.foo2.bar nerastas "http://publications.europa.eu/ontology/euvoc#startDate" elementas.'
    ]


@patch("vitrina.classifiers.schema_download.requests.get")
def test_creates_concept(request_mock: Mock):
    mock_schema_response = Mock()
    mock_schema_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    mock_concept_response = Mock()
    mock_concept_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:ns6="http://publications.europa.eu/ontology/euvoc#">
            <rdf:Description rdf:about="https://www.foo2.bar">
                <dc:identifier>IDENTIFY</dc:identifier>
                <ns6:startDate rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2015-10-23</ns6:startDate>
                <skos:prefLabel xml:lang="en">test_label</skos:prefLabel>
                <skos:definition xml:lang="en">Test description</skos:definition>
                <skos:prefLabel xml:lang="lt">test_pavadinimas</skos:prefLabel>
                <skos:definition xml:lang="lt">Test aprašymas</skos:definition>
            </rdf:Description>
        </rdf:RDF>
        """
    request_mock.side_effect = [mock_schema_response, mock_concept_response]

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == ["https://www.foo2.bar"]
    assert errors == []

    concept = Concept.objects.filter(uri="https://www.foo2.bar").first()
    assert concept is not None
    assert concept.valid_since == date(2015, 10, 23)

    concept.set_current_language("lt")
    assert concept.label == "test_pavadinimas"
    assert concept.description == "Test aprašymas"
    concept.set_current_language("en")
    assert concept.label == "test_label"
    assert concept.description == "Test description"

    assert concept_schema in concept.concept_schemas.all()


@patch("vitrina.classifiers.schema_download.requests.get")
def test_concept_lt_label_and_description_backfills_from_en_language(request_mock: Mock):
    mock_schema_response = Mock()
    mock_schema_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    mock_concept_response = Mock()
    mock_concept_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:ns6="http://publications.europa.eu/ontology/euvoc#">
            <rdf:Description rdf:about="https://www.foo2.bar">
                <dc:identifier>IDENTIFY</dc:identifier>
                <ns6:startDate rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2015-10-23</ns6:startDate>
                <skos:prefLabel xml:lang="en">test_label</skos:prefLabel>
                <skos:definition xml:lang="en">Test description</skos:definition>
            </rdf:Description>
        </rdf:RDF>
        """
    request_mock.side_effect = [mock_schema_response, mock_concept_response]

    concept_schema = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == ["https://www.foo2.bar"]
    assert errors == []

    concept = Concept.objects.filter(uri="https://www.foo2.bar").first()
    assert concept is not None
    concept.set_current_language("lt")
    assert concept.label == "test_label"
    assert concept.description == "Test description"
    concept.set_current_language("en")
    assert concept.label == "test_label"
    assert concept.description == "Test description"


@patch("vitrina.classifiers.schema_download.requests.get")
def test_updates_existing_concept(request_mock: Mock):
    mock_schema_response = Mock()
    mock_schema_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    mock_concept_response = Mock()
    mock_concept_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:ns6="http://publications.europa.eu/ontology/euvoc#">
            <rdf:Description rdf:about="https://www.foo2.bar">
                <dc:identifier>IDENTIFY</dc:identifier>
                <ns6:startDate rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2015-10-23</ns6:startDate>
                <skos:prefLabel xml:lang="en">test_label</skos:prefLabel>
                <skos:definition xml:lang="en">Test description</skos:definition>
            </rdf:Description>
        </rdf:RDF>
        """
    request_mock.side_effect = [mock_schema_response, mock_concept_response]

    concept_schema_old = ConceptSchemaFactory(uri="old-uri")
    concept = ConceptFactory(code="IDENTIFY", concept_schemas=[concept_schema_old])

    concept_schema_new = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri=concept_schema_new.uri)

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == ["https://www.foo2.bar"]
    assert errors == []

    concept.refresh_from_db()
    assert concept.uri == "https://www.foo2.bar"
    assert concept.valid_since == date(2015, 10, 23)

    assert set(concept.concept_schemas.all().values_list("uri", flat=True)) == {
        concept_schema_old.uri,
        concept_schema_new.uri,
    }


@patch("vitrina.classifiers.schema_download.requests.get")
def test_do_not_parse_same_concept_uri_twice(request_mock: Mock):
    mock_schema_response1 = Mock()
    mock_schema_response1.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    mock_concept_response = Mock()
    mock_concept_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:ns6="http://publications.europa.eu/ontology/euvoc#">
            <rdf:Description rdf:about="https://www.foo2.bar">
                <dc:identifier>IDENTIFY</dc:identifier>
                <ns6:startDate rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2015-10-23</ns6:startDate>
                <skos:prefLabel xml:lang="en">test_label</skos:prefLabel>
                <skos:definition xml:lang="en">Test description</skos:definition>
            </rdf:Description>
        </rdf:RDF>
        """
    mock_schema_response2 = Mock()
    mock_schema_response2.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo1-1.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar">
                <skos:inScheme rdf:resource="https://www.foo1-1.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo1-1.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    request_mock.side_effect = [mock_schema_response1, mock_concept_response, mock_schema_response2]

    concept_schema1 = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema2 = ConceptSchemaFactory(uri="https://www.foo1-1.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri__in=(concept_schema1.uri, concept_schema2.uri))

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == ["https://www.foo2.bar"]
    assert errors == []

    concept = Concept.objects.filter(uri="https://www.foo2.bar").first()
    assert concept is not None
    assert set(concept.concept_schemas.values_list("uri", flat=True)) == {
        concept_schema1.uri,
        concept_schema2.uri,
    }

    assert request_mock.call_count == 3


@patch("vitrina.classifiers.schema_download.requests.get")
def test_continue_download_on_error(request_mock: Mock):
    mock_schema_response = Mock()
    mock_schema_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#">
            <rdf:Description rdf:about="https://www.foo.bar">
                <skos:hasTopConcept rdf:resource="https://www.foo2.bar" />
            </rdf:Description>
            <rdf:Description rdf:about="https://www.foo2.bar">
                <skos:inScheme rdf:resource="https://www.foo.bar" />
                <skos:topConceptOf rdf:resource="https://www.foo.bar" />
            </rdf:Description>
        </rdf:RDF>
        """
    mock_concept_response = Mock()
    mock_concept_response.content = """
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:skos="http://www.w3.org/2004/02/skos/core#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:ns6="http://publications.europa.eu/ontology/euvoc#">
            <rdf:Description rdf:about="https://www.foo2.bar">
                <dc:identifier>IDENTIFY</dc:identifier>
                <ns6:startDate rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2015-10-23</ns6:startDate>
                <skos:prefLabel xml:lang="en">test_label</skos:prefLabel>
                <skos:definition xml:lang="en">Test description</skos:definition>
                <skos:prefLabel xml:lang="lt">test_pavadinimas</skos:prefLabel>
                <skos:definition xml:lang="lt">Test aprašymas</skos:definition>
            </rdf:Description>
        </rdf:RDF>
        """
    request_mock.side_effect = [mock_schema_response, mock_concept_response]

    concept_schema1 = ConceptSchemaFactory(uri="not_url")
    concept_schema2 = ConceptSchemaFactory(uri="https://www.foo.bar")
    concept_schema_queryset = ConceptSchema.objects.filter(uri__in=(concept_schema1.uri, concept_schema2.uri))

    concept_downloader = RDFConceptDownloader()
    success_uris, errors = concept_downloader.from_schemas(concept_schema_queryset)

    assert success_uris == ["https://www.foo2.bar"]
    assert errors == ["not_url nėra validus URI."]

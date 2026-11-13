import csv
import io

import pytest
from django.contrib.contenttypes.models import ContentType
from factory.django import FileField

from vitrina.cms.factories import FilerFileFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory, DatasetServiceFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.datasets.structure import HEADER as FULL_HEADER
from vitrina.structure.models import Metadata, Model, Property, Version
from vitrina.structure.dataservice_import import import_dataservice_structure
from vitrina.structure.services import create_structure_objects

SERVICE = "datasets/gov/rc/ar/uapi"
HEADER = "dataset,model,property,type,ref,access\n"

pytestmark = pytest.mark.django_db


def _service() -> Dataset:
    return DatasetServiceFactory(metadata=SERVICE)


def _child(service: Dataset, name: str) -> Dataset:
    dataset = DatasetFactory(metadata=f"{SERVICE}/{name}")
    dataset.move(service, pos="sorted-child")
    return Dataset.objects.get(pk=dataset.pk)


def _full_header(manifest: str) -> str:
    # The parser on devel needs every column, so the short test files are written out with the full header.
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FULL_HEADER, restval="", lineterminator="\n")
    writer.writeheader()
    writer.writerows(csv.DictReader(io.StringIO(manifest)))
    return out.getvalue()


def _structure(dataset: Dataset, manifest: str):
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=_full_header(manifest))), dataset=dataset
    )
    dataset.current_structure = structure
    dataset.save()
    return structure


def _import_dataset(dataset: Dataset, manifest: str):
    return create_structure_objects(_structure(dataset, manifest))


def _import_service(service: Dataset, manifest: str):
    return import_dataservice_structure(_structure(service, manifest))


def _names(dataset: Dataset, model) -> list[str]:
    return sorted(
        Metadata.objects.filter(dataset=dataset, content_type=ContentType.objects.get_for_model(model)).values_list(
            "name", flat=True
        )
    )


def _errors() -> list[str]:
    return list(Comment.objects.filter(type=Comment.STRUCTURE_ERROR).order_by("pk").values_list("body", flat=True))


def test_imports_every_listed_dataset_into_its_own_dataset():
    service = _service()
    locations = _child(service, "locations")
    addresses = _child(service, "addresses")

    result = _import_service(
        service,
        HEADER + f"{SERVICE},,,ns,,\n"
        f"{SERVICE}/locations,,,,,\n"
        ",Location,,,id,\n"
        ",,id,integer,,open\n"
        f"{SERVICE}/addresses,,,,,\n"
        ",Address,,,id,\n"
        ",,id,integer,,open\n",
    )

    assert (result.errors, result.skipped, result.new) == ([], [], [])
    assert _names(locations, Model) == [f"{SERVICE}/locations/Location"]
    assert _names(addresses, Model) == [f"{SERVICE}/addresses/Address"]
    assert _names(service, Model) == []
    assert _errors() == []


def test_skips_other_dataservice_and_links_to_its_existing_model():
    countries = DatasetFactory(metadata="datasets/gov/rc/geo/uapi/countries")
    _import_dataset(
        countries,
        HEADER + "datasets/gov/rc/geo/uapi/countries,,,,,\n,Country,,,id,\n,,id,integer,,open\n,,code,string,,open\n",
    )
    service = _service()
    cities = _child(service, "cities")

    result = _import_service(
        service,
        HEADER + f"{SERVICE}/cities,,,,,\n"
        ",City,,,id,\n"
        ",,id,integer,,open\n"
        ",,country,ref,/datasets/gov/rc/geo/uapi/countries/Country,open\n"
        "datasets/gov/rc/geo/uapi/countries,,,,,\n"
        ",Country,,,id,\n"
        ",,id,integer,,open\n",
    )

    assert result.errors == []
    assert [skipped.name for skipped in result.skipped] == ["datasets/gov/rc/geo/uapi/countries"]
    assert _names(countries, Property) == ["code", "id"]
    country = Property.objects.get(model__dataset=cities, metadata__name="country")
    assert country.ref_model.dataset == countries
    assert _errors() == []


def test_reference_to_missing_model_is_an_error_note():
    service = _service()
    cities = _child(service, "cities")

    result = _import_service(
        service,
        HEADER + f"{SERVICE}/cities,,,,,\n"
        ",City,,,id,\n"
        ",,id,integer,,open\n"
        ",,country,ref,/datasets/gov/rc/geo/uapi/countries/Country,open\n",
    )

    assert result.errors == []
    assert _names(cities, Property) == ["country", "id"]
    assert len(_errors()) == 1 and "/datasets/gov/rc/geo/uapi/countries/Country" in _errors()[0]


def test_datasets_refer_to_each_other_in_any_order():
    service = _service()
    locations = _child(service, "locations")
    addresses = _child(service, "addresses")

    result = _import_service(
        service,
        HEADER + f"{SERVICE}/addresses,,,,,\n"
        ",Address,,,id,\n"
        ",,id,integer,,open\n"
        f",,location,ref,/{SERVICE}/locations/Location,open\n"
        f"{SERVICE}/locations,,,,,\n"
        ",Location,,,id,\n"
        ",,id,integer,,open\n"
        f",,address,ref,/{SERVICE}/addresses/Address,open\n",
    )

    assert result.errors == []
    assert _errors() == []
    location = Property.objects.get(model__dataset=addresses, metadata__name="location")
    address = Property.objects.get(model__dataset=locations, metadata__name="address")
    assert (location.ref_model.dataset, address.ref_model.dataset) == (locations, addresses)


def test_datasets_not_in_file_are_unchanged():
    service = _service()
    locations = _child(service, "locations")
    streets = _child(service, "streets")
    _import_dataset(streets, HEADER + f"{SERVICE}/streets,,,,,\n,Street,,,id,\n,,id,integer,,open\n")

    result = _import_service(service, HEADER + f"{SERVICE}/locations,,,,,\n,Location,,,id,\n,,id,integer,,open\n")

    assert result.errors == []
    assert _names(locations, Model) == [f"{SERVICE}/locations/Location"]
    assert _names(streets, Model) == [f"{SERVICE}/streets/Street"]


def test_existing_dataset_keeps_its_details_and_structure_is_replaced():
    service = _service()
    locations = _child(service, "locations")
    locations.title = "Vietovės"
    locations.save()
    _import_service(
        service,
        HEADER + f"{SERVICE}/locations,,,,,\n,Location,,,id,\n,,id,integer,,open\n,,name,string,,open\n",
    )

    result = _import_service(service, HEADER + f"{SERVICE}/locations,,,,,\n,Location,,,id,\n,,id,integer,,open\n")

    locations.refresh_from_db()
    assert result.errors == []
    assert locations.title == "Vietovės"
    assert _names(locations, Property) == ["id"]


@pytest.mark.parametrize(
    "manifest",
    [
        HEADER + f"{SERVICE},,,ns,,\n",
        HEADER + "datasets/gov/rc/geo/uapi/countries,,,,,\n,Country,,,id,\n,,id,integer,,open\n",
    ],
)
def test_file_without_dataset_of_this_dataservice_is_rejected(manifest: str):
    service = _service()
    _import_dataset(service, HEADER + f"{SERVICE},,,,,\n,Legacy,,,id,\n,,id,integer,,open\n")
    locations = _child(service, "locations")
    versions = Version.objects.count()

    result = _import_service(service, manifest)

    assert len(result.errors) == 1
    assert _names(service, Model) == [f"{SERVICE}/Legacy"]
    assert _names(locations, Model) == []
    assert Version.objects.count() == versions


def test_models_in_dataservice_entry_are_not_imported():
    service = _service()
    _import_dataset(service, HEADER + f"{SERVICE},,,,,\n,Legacy,,,id,\n,,id,integer,,open\n")
    locations = _child(service, "locations")

    result = _import_service(
        service,
        HEADER + f"{SERVICE},,,ns,,\n"
        ",City,,,id,\n"
        ",,id,integer,,open\n"
        f"{SERVICE}/locations,,,,,\n"
        ",Location,,,id,\n"
        ",,id,integer,,open\n",
    )

    assert result.errors == []
    assert _names(service, Model) == [f"{SERVICE}/Legacy"]
    assert _names(locations, Model) == [f"{SERVICE}/locations/Location"]
    assert len(_errors()) == 1 and f"„{SERVICE}“" in _errors()[0]


def test_dataset_name_used_outside_dataservice_is_an_error_note():
    service = _service()
    locations = _child(service, "locations")
    elsewhere = DatasetFactory(metadata=f"{SERVICE}/streets")

    result = _import_service(
        service,
        HEADER + f"{SERVICE}/locations,,,,,\n"
        ",Location,,,id,\n"
        ",,id,integer,,open\n"
        f"{SERVICE}/streets,,,,,\n"
        ",Street,,,id,\n"
        ",,id,integer,,open\n",
    )

    assert result.errors == []
    assert _names(locations, Model) == [f"{SERVICE}/locations/Location"]
    assert _names(elsewhere, Model) == []
    assert len(_errors()) == 1 and f"„{SERVICE}/streets“" in _errors()[0]


def test_new_dataset_is_listed_and_import_is_rejected_until_confirmed():
    service = _service()
    locations = _child(service, "locations")

    result = _import_service(
        service,
        HEADER + f"{SERVICE}/locations,,,,,\n"
        ",Location,,,id,\n"
        ",,id,integer,,open\n"
        f"{SERVICE}/addresses,,,,,\n"
        ",Address,,,id,\n"
        ",,id,integer,,open\n",
    )

    assert result.new == [f"{SERVICE}/addresses"]
    assert len(result.errors) == 1
    assert _names(locations, Model) == []
    assert not service.get_children().filter(metadata__name=f"{SERVICE}/addresses").exists()

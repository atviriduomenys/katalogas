import csv
import io

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from factory.django import FileField
from webtest import Upload

from vitrina.cms.factories import FilerFileFactory
from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory, DatasetServiceFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.datasets.structure import HEADER as FULL_HEADER
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.structure import VersionStatus
from vitrina.structure.models import Metadata, Model, Property, Version
from vitrina.structure.dataservice_import import import_dataservice_structure
from vitrina.structure.services import create_structure_objects
from vitrina.users.factories import UserFactory

SERVICE = "datasets/gov/rc/ar/uapi"
HEADER = "dataset,model,property,type,ref,access\n"

pytestmark = pytest.mark.django_db


def _service() -> Dataset:
    return DatasetServiceFactory(metadata=SERVICE)


def _child(service: Dataset, name: str) -> Dataset:
    dataset = DatasetFactory(metadata=f"{SERVICE}/{name}")
    # Treebeard moves by the parent's in-memory child count, so it must be fresh.
    service.refresh_from_db()
    dataset.move(service, pos="sorted-child")
    service.refresh_from_db()
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
    # Adding a root dataset re-sorts the roots by subclass, so the in-memory tree path may be stale.
    dataset.refresh_from_db()
    dataset.current_structure = structure
    dataset.save()
    return structure


def _import_dataset(dataset: Dataset, manifest: str):
    return create_structure_objects(_structure(dataset, manifest))


def _import_service(service: Dataset, manifest: str, **options):
    return import_dataservice_structure(_structure(service, manifest), **options)


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

    result = _import_service(
        service, HEADER + f"{SERVICE}/locations,,,,,\n,Location,,,id,\n,,id,integer,,open\n", replace_drafts=True
    )

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


LOCATIONS = HEADER + f"{SERVICE}/locations,,,,,\n,Location,,,id,\n,,id,integer,,open\n,,name,string,,open\n"


def _drafts(dataset: Dataset) -> list[Version]:
    return list(dataset.dataset_version.filter(status=VersionStatus.DRAFT).order_by("version"))


def _release(dataset: Dataset) -> Version:
    version = _drafts(dataset)[-1]
    version.status = VersionStatus.STABLE
    version.save()
    return version


def _uuid(dataset: Dataset, model, name: str, version: Version) -> str:
    return Metadata.objects.get(
        dataset=dataset,
        content_type=ContentType.objects.get_for_model(model),
        name=name,
        metadata_version=version,
    ).uuid


def test_empty_draft_from_dataset_creation_is_reused():
    service = _service()
    locations = _child(service, "locations")
    drafts = _drafts(locations)

    result = _import_service(service, LOCATIONS)

    assert result.errors == []
    assert _drafts(locations) == drafts


def test_dataset_without_draft_gets_a_new_draft_and_released_version_is_unchanged():
    service = _service()
    locations = _child(service, "locations")
    _import_service(service, LOCATIONS)
    released = _release(locations)

    result = _import_service(service, HEADER + f"{SERVICE}/locations,,,,,\n,Location,,,id,\n,,id,integer,,open\n")

    assert result.errors == []
    [draft] = _drafts(locations)
    assert draft.version > released.version
    assert sorted(
        Metadata.objects.filter(metadata_version=released, content_type__model="property").values_list(
            "name", flat=True
        )
    ) == ["id", "name"]
    assert list(
        Metadata.objects.filter(metadata_version=draft, content_type__model="property").values_list("name", flat=True)
    ) == ["id"]
    location = f"{SERVICE}/locations/Location"
    assert _uuid(locations, Model, location, draft) == _uuid(locations, Model, location, released)


def test_existing_draft_rejects_import_without_changes():
    service = _service()
    locations = _child(service, "locations")
    _import_service(service, LOCATIONS)
    [draft] = _drafts(locations)

    result = _import_service(service, HEADER + f"{SERVICE}/locations,,,,,\n,Location,,,id,\n,,id,integer,,open\n")

    assert result.drafts == [f"{SERVICE}/locations"]
    assert len(result.errors) == 1
    assert _drafts(locations) == [draft]
    assert _names(locations, Property) == ["id", "name"]


def test_draft_in_one_of_two_datasets_rejects_whole_import():
    service = _service()
    locations = _child(service, "locations")
    addresses = _child(service, "addresses")
    _import_service(service, HEADER + f"{SERVICE}/addresses,,,,,\n,Address,,,id,\n,,id,integer,,open\n")

    result = _import_service(
        service,
        LOCATIONS + f"{SERVICE}/addresses,,,,,\n,Address,,,id,\n,,id,integer,,open\n",
    )

    assert result.drafts == [f"{SERVICE}/addresses"]
    assert _names(locations, Model) == []
    assert _names(addresses, Property) == ["id"]


def test_replacing_drafts_keeps_uuids_and_references_from_other_datasets():
    service = _service()
    locations = _child(service, "locations")
    streets = _child(service, "streets")
    _import_service(service, LOCATIONS)
    [old_draft] = _drafts(locations)
    location = f"{SERVICE}/locations/Location"
    model_uuid = _uuid(locations, Model, location, old_draft)
    _import_service(
        service,
        HEADER + f"{SERVICE}/streets,,,,,\n,Street,,,id,\n,,id,integer,,open\n,,location,ref,/{location},open\n",
    )

    result = _import_service(
        service, HEADER + f"{SERVICE}/locations,,,,,\n,Location,,,id,\n,,id,integer,,open\n", replace_drafts=True
    )

    assert result.errors == []
    [new_draft] = _drafts(locations)
    assert new_draft != old_draft
    assert not Version.objects.filter(pk=old_draft.pk).exists()
    assert _uuid(locations, Model, location, new_draft) == model_uuid
    assert _names(locations, Property) == ["id"]
    street_location = Property.objects.get(model__dataset=streets, metadata__name="location")
    assert street_location.ref_model.metadata_version == new_draft


NEW_DATASETS = (
    "dataset,model,property,type,ref,access,title,description\n"
    f"{SERVICE}/locations,,,,,,Vietovės,Vietovių sąrašas\n"
    ",Location,,,id,,,\n"
    ",,id,integer,,open,,\n"
    f"{SERVICE}/addresses,,,,,,,\n"
    ",Address,,,id,,,\n"
    ",,id,integer,,open,,\n"
)


def _representative(user, dataset: Dataset) -> None:
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        role=Representative.OPEN_DATA_MANAGER,
    )


def test_create_missing_creates_datasets_under_dataservice(rf):
    service = _service()

    result = _import_service(service, NEW_DATASETS, create_missing=True, request=rf.get("/"))

    assert (result.errors, result.new) == ([], [f"{SERVICE}/locations", f"{SERVICE}/addresses"])
    locations = Dataset.objects.get(metadata__name=f"{SERVICE}/locations")
    addresses = Dataset.objects.get(metadata__name=f"{SERVICE}/addresses")
    assert locations.is_child_of(service) and addresses.is_child_of(service)
    assert (locations.subclass.name, locations.organization, locations.is_public) == (
        "dataset",
        service.organization,
        False,
    )
    assert (locations.title, locations.description, addresses.title) == ("Vietovės", "Vietovių sąrašas", "addresses")
    assert _names(locations, Model) == [f"{SERVICE}/locations/Location"]
    assert Representative.objects.filter(
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=locations.pk,
        role=Representative.OPEN_DATA_MANAGER,
    ).exists()


def test_user_without_permission_to_create_datasets_gets_an_error():
    service = _service()

    result = _import_service(service, NEW_DATASETS, create_missing=True, user=UserFactory())

    assert len(result.errors) == 1
    assert not service.get_children().exists()


def test_user_may_change_only_some_of_the_datasets():
    service = _service()
    locations = _child(service, "locations")
    addresses = _child(service, "addresses")
    user = UserFactory()
    _representative(user, addresses)

    result = _import_service(service, NEW_DATASETS, user=user)

    assert result.errors == []
    assert [skipped.name for skipped in result.skipped] == [f"{SERVICE}/locations"]
    assert _names(locations, Model) == []
    assert _names(addresses, Model) == [f"{SERVICE}/addresses/Address"]


def test_user_may_change_none_of_the_datasets_is_rejected():
    service = _service()
    locations = _child(service, "locations")
    _child(service, "addresses")

    result = _import_service(service, NEW_DATASETS, user=UserFactory())

    assert len(result.errors) == 1
    assert _names(locations, Model) == []


def test_agent_organization_may_change_only_its_datasets():
    service = _service()
    locations = _child(service, "locations")
    addresses = _child(service, "addresses")
    Dataset.objects.filter(pk=addresses.pk).update(organization=service.organization)

    result = _import_service(service, NEW_DATASETS, organization=service.organization)

    assert [skipped.name for skipped in result.skipped] == [f"{SERVICE}/locations"]
    assert _names(locations, Model) == []
    assert _names(addresses, Model) == [f"{SERVICE}/addresses/Address"]


def _upload(app, service: Dataset, manifest: str):
    form = app.get(reverse("dataset-structure-import-no-version", args=[service.pk])).forms["dataset-structure-form"]
    form["file"] = Upload("file.csv", _full_header(manifest).encode())
    return form.submit()


def _messages(resp) -> list[str]:
    # The structure page without a version redirects to the latest version.
    while resp.status_code == 302:
        resp = resp.follow()
    return [str(message) for message in resp.context["messages"]]


def test_website_import_into_dataservice_shows_one_result(app, settings):
    # Messages travel in a cookie that is Secure like the session cookie, and the test client uses plain HTTP.
    settings.SESSION_COOKIE_SECURE = False
    service = _service()
    locations = _child(service, "locations")
    app.set_user(UserFactory(is_staff=True))

    resp = _upload(
        app,
        service,
        LOCATIONS + "datasets/gov/rc/geo/uapi/countries,,,,,\n,Country,,,id,\n,,id,integer,,open\n",
    )

    assert resp.location == reverse("dataset-structure-no-version", args=[service.pk])
    messages = _messages(resp)
    assert len(messages) == 2 and "datasets/gov/rc/geo/uapi/countries" in messages[1]
    assert _names(locations, Model) == [f"{SERVICE}/locations/Location"]


def test_website_confirms_new_datasets_and_drafts_before_importing(app):
    service = _service()
    locations = _child(service, "locations")
    app.set_user(UserFactory(is_staff=True))
    _upload(app, service, LOCATIONS)

    resp = _upload(app, service, NEW_DATASETS)

    assert "/confirm/" in resp.location
    page = resp.follow()
    assert f"{SERVICE}/addresses" in page and f"{SERVICE}/locations" in page
    assert not Dataset.objects.filter(metadata__name=f"{SERVICE}/addresses").exists()
    assert _names(locations, Property) == ["id", "name"]

    resp = page.forms["confirm-form"].submit()

    assert resp.location == reverse("dataset-structure-no-version", args=[service.pk])
    addresses = Dataset.objects.get(metadata__name=f"{SERVICE}/addresses")
    assert _names(addresses, Model) == [f"{SERVICE}/addresses/Address"]
    assert _names(locations, Property) == ["id"]


def test_website_import_into_dataset_is_unchanged(app):
    dataset = DatasetFactory(metadata="datasets/gov/example")
    app.set_user(UserFactory(is_staff=True))

    resp = _upload(app, dataset, HEADER + "datasets/gov/example,,,,,\n,City,,,id,\n,,id,integer,,open\n")

    assert "/confirm/" not in resp.location
    assert _names(dataset, Model) == ["datasets/gov/example/City"]


def test_unreadable_file_is_rejected_without_changes():
    service = _service()
    locations = _child(service, "locations")
    versions = Version.objects.count()
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data="dataset;model\n" + f"{SERVICE}/locations;\n")),
        dataset=service,
    )

    result = import_dataservice_structure(structure)

    assert len(result.errors) == 1
    assert _names(locations, Model) == []
    assert Version.objects.count() == versions


def test_invalid_property_gets_an_error_note_and_the_rest_is_imported():
    service = _service()
    locations = _child(service, "locations")
    addresses = _child(service, "addresses")

    result = _import_service(
        service,
        HEADER + f"{SERVICE}/locations,,,,,\n"
        ",Location,,,id,\n"
        ",,id,integer,,open\n"
        ",,code,integer bogus,,open\n"
        f"{SERVICE}/addresses,,,,,\n"
        ",Address,,,id,\n"
        ",,id,integer,,open\n",
    )

    assert result.errors == []
    assert _names(locations, Property) == ["id"]
    assert _names(addresses, Model) == [f"{SERVICE}/addresses/Address"]
    assert len(_errors()) == 1 and "bogus" in _errors()[0]

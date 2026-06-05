from unittest.mock import patch

from django.conf import settings
from factory.django import FileField
from vitrina.structure.factories import UMLDiagramFactory
from vitrina.datasets.factories import DatasetStructureFactory, FilerFileFactory, DatasetFactory
from vitrina.structure.services import create_structure_objects
from vitrina.structure.tasks import update_uml_diagram
from vitrina.structure import UMLDiagramStatus


def test_update_uml_diagram():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "4,,,,Licence,,,,,,,,,,,,,,\n"
        "5,,,,,id,integer,,,,,,,,,,,,\n"
        "6,,,,,catalog,ref,Catalog,,,,,,,,,,,\n"
        ",,,,,,,,,,,,,,,,,,\n"
        "7,,,,Catalog,,,,,,,,,,,,,,\n"
        "8,,,,,id,integer,,,,,,,,,,,,\n"
    )

    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
        dataset=DatasetFactory(title="Title", description="Description", metadata="datasets/gov/ivpk/adp"),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)

    uml_diagram = UMLDiagramFactory(metadata_version=version)

    assert uml_diagram.mermaid is None
    assert uml_diagram.status == UMLDiagramStatus.OUTDATED

    update_uml_diagram(uml_diagram.pk)

    uml_diagram.refresh_from_db()

    assert uml_diagram.status == UMLDiagramStatus.UP_TO_DATE
    assert "classDiagram" in uml_diagram.mermaid
    assert "class Licence" in uml_diagram.mermaid
    assert "class Catalog" in uml_diagram.mermaid
    assert 'Licence --> "[0..1]" Catalog : catalog' in uml_diagram.mermaid

    base_url = f"{settings.META_SITE_PROTOCOL}://{settings.META_SITE_DOMAIN}"
    dataset_pk = structure.dataset.pk
    version_pk = version.pk
    assert (
        f"click `datasets/gov/ivpk/adp/Licence` href "
        f'"{base_url}/datasets/{dataset_pk}/versions/{version_pk}/models/Licence/"'
    ) in uml_diagram.mermaid
    assert (
        f"click `datasets/gov/ivpk/adp/Catalog` href "
        f'"{base_url}/datasets/{dataset_pk}/versions/{version_pk}/models/Catalog/"'
    ) in uml_diagram.mermaid


def test_update_uml_diagram_failure_persists_error():
    manifest = (
        "id,dataset,resource,base,model,property,type,ref,source,prepare,count,level,status,visibility,access,uri,eli,title,description\n"
        "1,datasets/gov/ivpk/adp,,,,,,,,,,,,,,,,,\n"
        "4,,,,Licence,,,,,,,,,,,,,,\n"
        "5,,,,,id,integer,,,,,,,,,,,,\n"
    )
    structure = DatasetStructureFactory(
        file=FilerFileFactory(file=FileField(filename="file.csv", data=manifest)),
    )
    structure.dataset.current_structure = structure
    structure.dataset.save()
    version = create_structure_objects(structure)
    uml_diagram = UMLDiagramFactory(metadata_version=version, status=UMLDiagramStatus.PENDING)

    with patch("vitrina.structure.tasks.generate_mermaid_diagram", side_effect=RuntimeError("klaida")):
        update_uml_diagram(uml_diagram.pk)

    uml_diagram.refresh_from_db()
    assert uml_diagram.status == UMLDiagramStatus.FAILED
    assert uml_diagram.error_message == "klaida"
    assert uml_diagram.mermaid is None

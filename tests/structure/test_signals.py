from vitrina.structure.factories import UMLDiagramFactory, ModelFactory
from vitrina.structure import UMLDiagramStatus


def test_uml_diagram_outdated_if_model_saved():
    uml_diagram = UMLDiagramFactory(status=UMLDiagramStatus.UP_TO_DATE)
    version = uml_diagram.metadata_version

    assert uml_diagram.version_counter == 0
    assert uml_diagram.status == UMLDiagramStatus.UP_TO_DATE

    ModelFactory(metadata_version=version)

    uml_diagram.refresh_from_db()
    assert uml_diagram.version_counter == 1
    assert uml_diagram.status == UMLDiagramStatus.OUTDATED


def test_uml_diagram_outdated_if_model_deleted():
    model = ModelFactory()
    version = model.metadata_version
    uml_diagram = UMLDiagramFactory(metadata_version=version, status=UMLDiagramStatus.UP_TO_DATE)

    assert uml_diagram.status == UMLDiagramStatus.UP_TO_DATE
    assert uml_diagram.version_counter == 0
    model.delete()

    uml_diagram.refresh_from_db()
    assert uml_diagram.version_counter == 1
    assert uml_diagram.status == UMLDiagramStatus.OUTDATED

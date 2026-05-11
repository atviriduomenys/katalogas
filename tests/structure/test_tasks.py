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
        dataset=DatasetFactory(title="Title", description="Description"),
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
    assert (
        """
classDiagram
namespace `datasets/gov/ivpk/adp` {
class `datasets/gov/ivpk/adp/Licence`["Licence"]:::Entity {
«optional»
id : integer [0..1]
}
class `datasets/gov/ivpk/adp/Catalog`["Catalog"]:::Entity {
«optional»
id : integer [0..1]
}
}
`datasets/gov/ivpk/adp/Licence` --> "[0..1]" `datasets/gov/ivpk/adp/Catalog` : catalog<br/>«optional»
"""
        in uml_diagram.mermaid
    )

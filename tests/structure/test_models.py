import uuid
from unittest.mock import patch, MagicMock

from vitrina.structure.models import UMLDiagram
from vitrina.structure.factories import UMLDiagramFactory
from vitrina.structure import UMLDiagramStatus


class TestUMLDiagram:
    def test_initiate_update(self):
        uml_diagram: UMLDiagram = UMLDiagramFactory(status=UMLDiagramStatus.UP_TO_DATE)
        mock_result = MagicMock()
        mock_result.id = uuid.uuid4()

        assert uml_diagram.status == UMLDiagramStatus.UP_TO_DATE
        with patch("vitrina.structure.tasks.update_uml_diagram.delay", return_value=(mock_result)) as mocked_delay:
            uml_diagram.initiate_update()

        mocked_delay.assert_called_once()
        assert uml_diagram.status == UMLDiagramStatus.PENDING

    def test_initiate_update_clears_error_message(self):
        uml_diagram: UMLDiagram = UMLDiagramFactory(status=UMLDiagramStatus.FAILED, error_message="previous failure")
        mock_result = MagicMock()
        mock_result.id = uuid.uuid4()

        with patch("vitrina.structure.tasks.update_uml_diagram.delay", return_value=mock_result):
            uml_diagram.initiate_update()
        uml_diagram.refresh_from_db()

        assert uml_diagram.status == UMLDiagramStatus.PENDING
        assert uml_diagram.error_message is None

    def test_invalidate(self):
        uml_diagram: UMLDiagram = UMLDiagramFactory(status=UMLDiagramStatus.UP_TO_DATE)

        assert uml_diagram.version_counter == 0
        assert uml_diagram.status == UMLDiagramStatus.UP_TO_DATE
        uml_diagram.invalidate()
        uml_diagram.refresh_from_db()

        assert uml_diagram.version_counter == 1
        assert uml_diagram.status == UMLDiagramStatus.OUTDATED

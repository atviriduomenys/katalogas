import reversion
from reversion.models import Version
from vitrina.smart_contracts.factories import AgreementPDFFileFactory
from vitrina.smart_contracts.models import Agreement, AgreementFile
from vitrina.reversion_utils import get_version_ids, VersionRelationSpec


def test_get_version_ids():
    with reversion.create_revision():
        agreement_file = AgreementPDFFileFactory()

    agreement_file_version_ids = Version.objects.get_for_object(agreement_file).values_list("id", flat=True)
    agreement_version_ids = Version.objects.get_for_object(agreement_file.agreement).values_list("id", flat=True)
    project_version_ids = Version.objects.get_for_object(agreement_file.agreement.project).values_list("id", flat=True)

    version_ids = list(agreement_file_version_ids) + list(agreement_version_ids) + list(project_version_ids)

    agreement_children = [
        VersionRelationSpec(target_model=AgreementFile, parent_fk=AgreementFile.agreement),
    ]
    project_children = [
        VersionRelationSpec(target_model=Agreement, parent_fk=Agreement.project, nested=agreement_children)
    ]

    assert len(version_ids) == 3
    assert set(version_ids) == get_version_ids(agreement_file.agreement.project, project_children)

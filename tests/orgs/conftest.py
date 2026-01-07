from pathlib import Path

import pytest
from django.conf import settings

from tests.smart_contracts.conftest import AGREEMENT_PDF, AGREEMENT_TWO_SIGNERS, ODRL_JSON


@pytest.fixture
def test_files_dir() -> Path:
    return settings.BASE_DIR / "tests/smart_contracts/files"


@pytest.fixture
def odrl_json(test_files_dir: Path) -> Path:
    return test_files_dir / ODRL_JSON


@pytest.fixture
def agreement_pdf(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_PDF


@pytest.fixture
def agreements_dir(test_files_dir: Path) -> Path:
    return test_files_dir / "test_contracts"


@pytest.fixture
def agreement_two_signers(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_TWO_SIGNERS

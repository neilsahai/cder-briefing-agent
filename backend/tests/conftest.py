import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.data.audit import get_audit  # noqa: E402
from app.data.store import get_store  # noqa: E402


@pytest.fixture(scope="session")
def store():
    return get_store()


@pytest.fixture(scope="session")
def audit():
    return get_audit()

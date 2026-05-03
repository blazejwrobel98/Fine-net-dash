import os
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["SKIP_SCHEDULER"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///" + Path(_tmp.name).as_posix().lstrip("/")


@pytest.fixture(scope="session")
def client():
    """Import aplikacji dopiero po ustawieniu DATABASE_URL w module powyżej."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c

"""Shared pytest fixtures for the ai-job-pipeline test suite."""

import os
import sys

import pytest

# Make the project root importable so `from app import app` works even when
# pytest is invoked from inside tests/.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Flask test client with OUTPUT_DIR redirected to a tmp path.

    Isolates each test from real user data under ``output/`` and avoids
    accidental writes. ``app`` is re-imported fresh per test so the monkeypatched
    OUTPUT_DIR takes effect.
    """
    from src import config

    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path, raising=False)
    monkeypatch.setattr(config, "OUTPUT_EXCEL", tmp_path / "jobs.xlsx", raising=False)

    # Re-import app so its module-level TAILORED_DIR picks up the patched OUTPUT_DIR
    monkeypatch.delitem(sys.modules, "app", raising=False)
    from app import app as flask_app  # noqa: WPS433 — intentional re-import per-test
    flask_app.config.update(TESTING=True)

    with flask_app.test_client() as c:
        yield c

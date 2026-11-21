"""Shared test fixtures."""

import os
import tempfile

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _env_setup(tmp_path):
    """Set test-safe environment variables and reinitialise settings for each test."""
    db_file = tmp_path / "test.db"
    env_overrides = {
        "LLM_API_KEYS": "test-key-1,test-key-2",
        "DATABASE_URL": f"sqlite:///{db_file}",
        "ENABLE_FAILURE_SIMULATION": "true",
        "DEFAULT_MODEL": "gemini/gemini-2.0-flash",
        "DEFAULT_SYSTEM_PROMPT": "You are a helpful assistant.",
        "ALLOWED_ORIGINS": "*",
    }
    old = {k: os.environ.get(k) for k in env_overrides}
    os.environ.update(env_overrides)

    # Reload settings so they pick up the test env
    from app import config
    config.settings = config.Settings.from_env()

    # Reset db path cache
    from app import database
    database._DB_PATH = None

    # Clear session system prompts
    from app import routes
    routes._session_system_prompts.clear()

    yield

    # Restore
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture
def client():
    """Create a test client with lifespan events."""
    from app.main import app
    with TestClient(app) as c:
        yield c

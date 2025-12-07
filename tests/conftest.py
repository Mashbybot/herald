"""
Pytest configuration and fixtures for Herald bot tests
"""

import pytest
import asyncio
import os
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db_path(tmp_path):
    """Provide a temporary database path for tests"""
    return tmp_path / "test_herald.db"


@pytest.fixture
def mock_env(monkeypatch, test_db_path):
    """Mock environment variables for testing"""
    monkeypatch.setenv("DISCORD_TOKEN", "test_token_" + "x" * 50)
    monkeypatch.setenv("DATABASE_PATH", str(test_db_path))
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEBUG", "true")

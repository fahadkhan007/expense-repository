"""
Shared test fixtures for the expense tracker test suite.

Design decisions:
- `client` is SESSION-scoped: the app (and AsyncMongoClient) starts once for the
  entire test run, avoiding the "AsyncMongoClient in different event loop" error
  that happens when each test creates its own event loop via TestClient.
- `auth` / `auth2` are FUNCTION-scoped: each test gets a *unique* user (via uuid4
  suffix), so there is zero shared state between tests — no "already exists" conflicts
  and no cross-test data pollution (e.g. empty-list assertions are always correct).
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# App client  (session-scoped — one event loop, one MongoDB client)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client() -> TestClient:
    """One TestClient for the whole test session."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def register_and_login(client: TestClient, label: str = "user") -> dict:
    """
    Register a *brand-new* unique user and return:
      - headers  : {"Authorization": "Bearer <token>"}
      - user     : the user payload from the response
      - email    : the generated email
      - password : the plain-text password
    """
    unique = uuid.uuid4().hex[:10]
    email = f"test_{label}_{unique}@example.com"
    password = "testpass123"

    resp = client.post("/auth/register", json={
        "name": f"Test {label.title()} {unique}",
        "email": email,
        "password": password,
    })
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
        "email": email,
        "password": password,
    }


@pytest.fixture(scope="function")
def auth(client: TestClient) -> dict:
    """Primary authenticated user — unique per test."""
    return register_and_login(client, "primary")


@pytest.fixture(scope="function")
def auth2(client: TestClient) -> dict:
    """Secondary authenticated user — unique per test (for isolation checks)."""
    return register_and_login(client, "secondary")

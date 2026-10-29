"""
Tests for the /categories router.

Covers:
  POST   /categories/          – create
  GET    /categories/           – list all (own user)
  GET    /categories/{id}       – get single
  PATCH  /categories/{id}       – update
  DELETE /categories/{id}       – delete

Also tests auth guards and cross-user isolation.
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CATEGORY_PAYLOAD = {
    "name": "Groceries",
    "type": "debit",
    "icon": "🛒",
    "color": "#4CAF50",
}


def create_category(client: TestClient, headers: dict, payload: dict | None = None) -> dict:
    """Create a category and return the response JSON."""
    body = payload or CATEGORY_PAYLOAD
    resp = client.post("/categories/", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST /categories/
# ---------------------------------------------------------------------------

class TestCreateCategory:
    def test_create_success(self, client, auth):
        resp = client.post("/categories/", json=CATEGORY_PAYLOAD, headers=auth["headers"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == CATEGORY_PAYLOAD["name"]
        assert data["type"] == CATEGORY_PAYLOAD["type"]
        assert data["icon"] == CATEGORY_PAYLOAD["icon"]
        assert data["color"] == CATEGORY_PAYLOAD["color"]
        assert "_id" in data
        assert data["user_id"] == auth["user"]["_id"]

    def test_create_no_type(self, client, auth):
        """type is optional – should default to None."""
        payload = {**CATEGORY_PAYLOAD, "type": None}
        del payload["type"]
        resp = client.post("/categories/", json=payload, headers=auth["headers"])
        assert resp.status_code == 201
        assert resp.json()["type"] is None

    def test_create_credit_type(self, client, auth):
        payload = {**CATEGORY_PAYLOAD, "name": "Salary", "type": "credit"}
        resp = client.post("/categories/", json=payload, headers=auth["headers"])
        assert resp.status_code == 201
        assert resp.json()["type"] == "credit"

    def test_create_missing_name_fails(self, client, auth):
        payload = {k: v for k, v in CATEGORY_PAYLOAD.items() if k != "name"}
        resp = client.post("/categories/", json=payload, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_empty_name_fails(self, client, auth):
        resp = client.post("/categories/", json={**CATEGORY_PAYLOAD, "name": "  "}, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_missing_icon_fails(self, client, auth):
        payload = {k: v for k, v in CATEGORY_PAYLOAD.items() if k != "icon"}
        resp = client.post("/categories/", json=payload, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_missing_color_fails(self, client, auth):
        payload = {k: v for k, v in CATEGORY_PAYLOAD.items() if k != "color"}
        resp = client.post("/categories/", json=payload, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_requires_auth(self, client):
        resp = client.post("/categories/", json=CATEGORY_PAYLOAD)
        assert resp.status_code == 401

    def test_create_invalid_token(self, client):
        resp = client.post(
            "/categories/",
            json=CATEGORY_PAYLOAD,
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_create_invalid_type_value(self, client, auth):
        resp = client.post(
            "/categories/",
            json={**CATEGORY_PAYLOAD, "type": "transfer"},
            headers=auth["headers"],
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /categories/
# ---------------------------------------------------------------------------

class TestGetCategories:
    def test_get_empty_list(self, client, auth):
        resp = client.get("/categories/", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_returns_own_categories(self, client, auth):
        create_category(client, auth["headers"])
        create_category(client, auth["headers"], {**CATEGORY_PAYLOAD, "name": "Transport"})
        resp = client.get("/categories/", headers=auth["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_does_not_return_other_users_categories(self, client, auth, auth2):
        """User 1's categories must not appear for User 2."""
        create_category(client, auth["headers"])
        resp = client.get("/categories/", headers=auth2["headers"])
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_requires_auth(self, client):
        resp = client.get("/categories/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /categories/{category_id}
# ---------------------------------------------------------------------------

class TestGetCategory:
    def test_get_single_success(self, client, auth):
        created = create_category(client, auth["headers"])
        resp = client.get(f"/categories/{created['_id']}", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.json()["_id"] == created["_id"]

    def test_get_nonexistent_returns_404(self, client, auth):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.get(f"/categories/{fake_id}", headers=auth["headers"])
        assert resp.status_code == 404

    def test_get_other_users_category_returns_404(self, client, auth, auth2):
        """User 2 must not be able to fetch User 1's category."""
        created = create_category(client, auth["headers"])
        resp = client.get(f"/categories/{created['_id']}", headers=auth2["headers"])
        assert resp.status_code == 404

    def test_get_invalid_uuid_returns_422(self, client, auth):
        resp = client.get("/categories/not-a-uuid", headers=auth["headers"])
        assert resp.status_code == 422

    def test_get_requires_auth(self, client):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.get(f"/categories/{fake_id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /categories/{category_id}
# ---------------------------------------------------------------------------

class TestUpdateCategory:
    def test_update_name(self, client, auth):
        created = create_category(client, auth["headers"])
        resp = client.patch(
            f"/categories/{created['_id']}",
            json={"name": "Food"},
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Food"

    def test_update_icon_and_color(self, client, auth):
        created = create_category(client, auth["headers"])
        resp = client.patch(
            f"/categories/{created['_id']}",
            json={"icon": "🍕", "color": "#FF5722"},
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["icon"] == "🍕"
        assert data["color"] == "#FF5722"

    def test_update_type(self, client, auth):
        created = create_category(client, auth["headers"])
        resp = client.patch(
            f"/categories/{created['_id']}",
            json={"type": "credit"},
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["type"] == "credit"

    def test_update_empty_body_returns_400(self, client, auth):
        created = create_category(client, auth["headers"])
        resp = client.patch(
            f"/categories/{created['_id']}",
            json={},
            headers=auth["headers"],
        )
        assert resp.status_code == 400

    def test_update_nonexistent_returns_404(self, client, auth):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.patch(
            f"/categories/{fake_id}",
            json={"name": "Ghost"},
            headers=auth["headers"],
        )
        assert resp.status_code == 404

    def test_update_other_users_category_returns_404(self, client, auth, auth2):
        created = create_category(client, auth["headers"])
        resp = client.patch(
            f"/categories/{created['_id']}",
            json={"name": "Hacked"},
            headers=auth2["headers"],
        )
        assert resp.status_code == 404

    def test_update_requires_auth(self, client):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.patch(f"/categories/{fake_id}", json={"name": "X"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /categories/{category_id}
# ---------------------------------------------------------------------------

class TestDeleteCategory:
    def test_delete_success(self, client, auth):
        created = create_category(client, auth["headers"])
        resp = client.delete(f"/categories/{created['_id']}", headers=auth["headers"])
        assert resp.status_code == 204

        # Verify it's gone
        resp2 = client.get(f"/categories/{created['_id']}", headers=auth["headers"])
        assert resp2.status_code == 404

    def test_delete_nonexistent_returns_404(self, client, auth):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.delete(f"/categories/{fake_id}", headers=auth["headers"])
        assert resp.status_code == 404

    def test_delete_other_users_category_returns_404(self, client, auth, auth2):
        created = create_category(client, auth["headers"])
        resp = client.delete(f"/categories/{created['_id']}", headers=auth2["headers"])
        assert resp.status_code == 404
        # Original category must still exist for owner
        resp2 = client.get(f"/categories/{created['_id']}", headers=auth["headers"])
        assert resp2.status_code == 200

    def test_delete_requires_auth(self, client):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.delete(f"/categories/{fake_id}")
        assert resp.status_code == 401

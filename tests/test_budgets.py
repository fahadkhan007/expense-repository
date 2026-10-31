"""
Minimal tests for the /budgets router.

Covers:
  POST   /budgets/         – create
  GET    /budgets/         – list
  GET    /budgets/{id}     – get single
  PATCH  /budgets/{id}     – update
  DELETE /budgets/{id}     – delete
  Auth guards + cross-user isolation
"""
import pytest

BUDGET_PAYLOAD = {"month": "2024-06", "limit": 1000.0}


def create_budget(client, headers, **overrides) -> dict:
    body = {**BUDGET_PAYLOAD, **overrides}
    resp = client.post("/budgets/", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST /budgets/
# ---------------------------------------------------------------------------

class TestCreateBudget:
    def test_create_success(self, client, auth):
        resp = client.post("/budgets/", json=BUDGET_PAYLOAD, headers=auth["headers"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["month"] == "2024-06"
        assert data["limit"] == 1000.0
        assert "_id" in data
        assert data["user_id"] == auth["user"]["_id"]

    def test_create_invalid_month_format_fails(self, client, auth):
        resp = client.post("/budgets/", json={"month": "2024-6", "limit": 500.0}, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_zero_limit_fails(self, client, auth):
        resp = client.post("/budgets/", json={"month": "2024-06", "limit": 0}, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_negative_limit_fails(self, client, auth):
        resp = client.post("/budgets/", json={"month": "2024-06", "limit": -100.0}, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_requires_auth(self, client):
        resp = client.post("/budgets/", json=BUDGET_PAYLOAD)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /budgets/
# ---------------------------------------------------------------------------

class TestGetBudgets:
    def test_get_empty_list(self, client, auth):
        resp = client.get("/budgets/", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_returns_own_budgets(self, client, auth):
        create_budget(client, auth["headers"], month="2024-07")
        create_budget(client, auth["headers"], month="2024-08")
        resp = client.get("/budgets/", headers=auth["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_does_not_return_other_users_budgets(self, client, auth, auth2):
        create_budget(client, auth["headers"], month="2024-09")
        resp = client.get("/budgets/", headers=auth2["headers"])
        assert resp.json() == []

    def test_get_requires_auth(self, client):
        assert client.get("/budgets/").status_code == 401


# ---------------------------------------------------------------------------
# GET /budgets/{id}
# ---------------------------------------------------------------------------

class TestGetBudget:
    def test_get_single_success(self, client, auth):
        budget = create_budget(client, auth["headers"], month="2024-10")
        resp = client.get(f"/budgets/{budget['_id']}", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.json()["_id"] == budget["_id"]

    def test_get_nonexistent_returns_404(self, client, auth):
        resp = client.get("/budgets/00000000-0000-0000-0000-000000000001", headers=auth["headers"])
        assert resp.status_code == 404

    def test_get_other_users_budget_returns_404(self, client, auth, auth2):
        budget = create_budget(client, auth["headers"], month="2024-11")
        resp = client.get(f"/budgets/{budget['_id']}", headers=auth2["headers"])
        assert resp.status_code == 404

    def test_get_requires_auth(self, client):
        assert client.get("/budgets/00000000-0000-0000-0000-000000000001").status_code == 401


# ---------------------------------------------------------------------------
# PATCH /budgets/{id}
# ---------------------------------------------------------------------------

class TestUpdateBudget:
    def test_update_limit(self, client, auth):
        budget = create_budget(client, auth["headers"], month="2024-12")
        resp = client.patch(f"/budgets/{budget['_id']}", json={"limit": 2000.0}, headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.json()["limit"] == 2000.0

    def test_update_nonexistent_returns_404(self, client, auth):
        resp = client.patch("/budgets/00000000-0000-0000-0000-000000000001", json={"limit": 500.0}, headers=auth["headers"])
        assert resp.status_code == 404

    def test_update_other_users_budget_returns_404(self, client, auth, auth2):
        budget = create_budget(client, auth["headers"], month="2025-01")
        resp = client.patch(f"/budgets/{budget['_id']}", json={"limit": 999.0}, headers=auth2["headers"])
        assert resp.status_code == 404

    def test_update_requires_auth(self, client):
        assert client.patch("/budgets/00000000-0000-0000-0000-000000000001", json={"limit": 100.0}).status_code == 401


# ---------------------------------------------------------------------------
# DELETE /budgets/{id}
# ---------------------------------------------------------------------------

class TestDeleteBudget:
    def test_delete_success(self, client, auth):
        budget = create_budget(client, auth["headers"], month="2025-02")
        resp = client.delete(f"/budgets/{budget['_id']}", headers=auth["headers"])
        assert resp.status_code == 204
        assert client.get(f"/budgets/{budget['_id']}", headers=auth["headers"]).status_code == 404

    def test_delete_nonexistent_returns_404(self, client, auth):
        resp = client.delete("/budgets/00000000-0000-0000-0000-000000000001", headers=auth["headers"])
        assert resp.status_code == 404

    def test_delete_other_users_budget_returns_404(self, client, auth, auth2):
        budget = create_budget(client, auth["headers"], month="2025-03")
        resp = client.delete(f"/budgets/{budget['_id']}", headers=auth2["headers"])
        assert resp.status_code == 404
        # Owner can still see it
        assert client.get(f"/budgets/{budget['_id']}", headers=auth["headers"]).status_code == 200

    def test_delete_requires_auth(self, client):
        assert client.delete("/budgets/00000000-0000-0000-0000-000000000001").status_code == 401

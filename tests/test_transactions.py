"""
Tests for the /transactions router.

Covers:
  POST   /transactions/           – create
  GET    /transactions/           – list (paginated)
  GET    /transactions/{id}       – get single
  PATCH  /transactions/{id}       – update
  DELETE /transactions/{id}       – delete

Also tests auth guards, cross-user isolation, and category-type validation.
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CATEGORY_DEBIT_PAYLOAD = {
    "name": "Food",
    "type": "debit",
    "icon": "🍔",
    "color": "#FF5722",
}

CATEGORY_CREDIT_PAYLOAD = {
    "name": "Salary",
    "type": "credit",
    "icon": "💰",
    "color": "#4CAF50",
}

CATEGORY_NEUTRAL_PAYLOAD = {
    "name": "Misc",
    "type": None,
    "icon": "📦",
    "color": "#9E9E9E",
}


def create_category(client: TestClient, headers: dict, payload: dict) -> dict:
    resp = client.post("/categories/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_transaction(client: TestClient, headers: dict, category_id: str, **overrides) -> dict:
    body = {
        "type": "debit",
        "amount": 50.0,
        "category_id": category_id,
        "description": "Test purchase",
        **overrides,
    }
    resp = client.post("/transactions/", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST /transactions/
# ---------------------------------------------------------------------------

class TestCreateTransaction:
    def test_create_debit_success(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        resp = client.post("/transactions/", json={
            "type": "debit",
            "amount": 120.5,
            "category_id": cat["_id"],
            "description": "Supermarket run",
        }, headers=auth["headers"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "debit"
        assert data["amount"] == 120.5
        assert data["category_id"] == cat["_id"]
        assert data["user_id"] == auth["user"]["_id"]
        assert "_id" in data
        assert "created_at" in data

    def test_create_credit_success(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_CREDIT_PAYLOAD)
        resp = client.post("/transactions/", json={
            "type": "credit",
            "amount": 3000.0,
            "category_id": cat["_id"],
        }, headers=auth["headers"])
        assert resp.status_code == 201
        assert resp.json()["type"] == "credit"

    def test_create_with_neutral_category(self, client, auth):
        """A category with type=None should accept both debit and credit transactions."""
        cat = create_category(client, auth["headers"], CATEGORY_NEUTRAL_PAYLOAD)
        for txn_type in ("debit", "credit"):
            resp = client.post("/transactions/", json={
                "type": txn_type,
                "amount": 10.0,
                "category_id": cat["_id"],
            }, headers=auth["headers"])
            assert resp.status_code == 201, f"Failed for type={txn_type}: {resp.text}"

    def test_create_without_description(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        resp = client.post("/transactions/", json={
            "type": "debit",
            "amount": 10.0,
            "category_id": cat["_id"],
        }, headers=auth["headers"])
        assert resp.status_code == 201
        assert resp.json()["description"] is None

    def test_create_category_type_mismatch_fails(self, client, auth):
        """Debit category + credit transaction must be rejected."""
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        resp = client.post("/transactions/", json={
            "type": "credit",
            "amount": 50.0,
            "category_id": cat["_id"],
        }, headers=auth["headers"])
        assert resp.status_code == 400

    def test_create_nonexistent_category_fails(self, client, auth):
        fake_cat_id = "00000000-0000-0000-0000-000000000001"
        resp = client.post("/transactions/", json={
            "type": "debit",
            "amount": 50.0,
            "category_id": fake_cat_id,
        }, headers=auth["headers"])
        assert resp.status_code == 404

    def test_create_other_users_category_fails(self, client, auth, auth2):
        """User 2 must not be able to use User 1's category."""
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        resp = client.post("/transactions/", json={
            "type": "debit",
            "amount": 50.0,
            "category_id": cat["_id"],
        }, headers=auth2["headers"])
        assert resp.status_code == 404

    def test_create_zero_amount_fails(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        resp = client.post("/transactions/", json={
            "type": "debit",
            "amount": 0,
            "category_id": cat["_id"],
        }, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_negative_amount_fails(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        resp = client.post("/transactions/", json={
            "type": "debit",
            "amount": -10.0,
            "category_id": cat["_id"],
        }, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_missing_amount_fails(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        resp = client.post("/transactions/", json={
            "type": "debit",
            "category_id": cat["_id"],
        }, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_invalid_type_fails(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        resp = client.post("/transactions/", json={
            "type": "transfer",
            "amount": 50.0,
            "category_id": cat["_id"],
        }, headers=auth["headers"])
        assert resp.status_code == 422

    def test_create_requires_auth(self, client):
        resp = client.post("/transactions/", json={
            "type": "debit",
            "amount": 50.0,
            "category_id": "00000000-0000-0000-0000-000000000001",
        })
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /transactions/
# ---------------------------------------------------------------------------

class TestGetTransactions:
    def test_get_empty_list(self, client, auth):
        resp = client.get("/transactions/", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_returns_own_transactions(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        create_transaction(client, auth["headers"], cat["_id"])
        create_transaction(client, auth["headers"], cat["_id"], amount=200.0)
        resp = client.get("/transactions/", headers=auth["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_sorted_descending_by_created_at(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        t1 = create_transaction(client, auth["headers"], cat["_id"], amount=10.0)
        t2 = create_transaction(client, auth["headers"], cat["_id"], amount=20.0)
        resp = client.get("/transactions/", headers=auth["headers"])
        data = resp.json()
        # Most recent first
        assert data[0]["_id"] == t2["_id"]
        assert data[1]["_id"] == t1["_id"]

    def test_get_does_not_return_other_users_transactions(self, client, auth, auth2):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        create_transaction(client, auth["headers"], cat["_id"])
        resp = client.get("/transactions/", headers=auth2["headers"])
        assert resp.status_code == 200
        assert resp.json() == []

    def test_pagination_page_1(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_NEUTRAL_PAYLOAD)
        for i in range(25):
            create_transaction(client, auth["headers"], cat["_id"], amount=float(i + 1))
        resp = client.get("/transactions/?page=1", headers=auth["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) == 20  # page_size cap

    def test_pagination_page_2(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_NEUTRAL_PAYLOAD)
        for i in range(25):
            create_transaction(client, auth["headers"], cat["_id"], amount=float(i + 1))
        resp = client.get("/transactions/?page=2", headers=auth["headers"])
        assert resp.status_code == 200
        assert len(resp.json()) == 5  # remaining items

    def test_invalid_page_number_fails(self, client, auth):
        resp = client.get("/transactions/?page=0", headers=auth["headers"])
        assert resp.status_code == 422

    def test_get_requires_auth(self, client):
        resp = client.get("/transactions/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /transactions/{transaction_id}
# ---------------------------------------------------------------------------

class TestGetTransaction:
    def test_get_single_success(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        txn = create_transaction(client, auth["headers"], cat["_id"])
        resp = client.get(f"/transactions/{txn['_id']}", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.json()["_id"] == txn["_id"]

    def test_get_nonexistent_returns_404(self, client, auth):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.get(f"/transactions/{fake_id}", headers=auth["headers"])
        assert resp.status_code == 404

    def test_get_other_users_transaction_returns_404(self, client, auth, auth2):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        txn = create_transaction(client, auth["headers"], cat["_id"])
        resp = client.get(f"/transactions/{txn['_id']}", headers=auth2["headers"])
        assert resp.status_code == 404

    def test_get_invalid_uuid_returns_422(self, client, auth):
        resp = client.get("/transactions/not-a-uuid", headers=auth["headers"])
        assert resp.status_code == 422

    def test_get_requires_auth(self, client):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.get(f"/transactions/{fake_id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /transactions/{transaction_id}
# ---------------------------------------------------------------------------

class TestUpdateTransaction:
    def test_update_amount(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        txn = create_transaction(client, auth["headers"], cat["_id"], amount=50.0)
        resp = client.patch(
            f"/transactions/{txn['_id']}",
            json={"amount": 99.99},
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["amount"] == 99.99

    def test_update_description(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        txn = create_transaction(client, auth["headers"], cat["_id"])
        resp = client.patch(
            f"/transactions/{txn['_id']}",
            json={"description": "Updated description"},
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    def test_update_category(self, client, auth):
        cat1 = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        cat2 = create_category(client, auth["headers"], {**CATEGORY_DEBIT_PAYLOAD, "name": "Transport"})
        txn = create_transaction(client, auth["headers"], cat1["_id"])
        resp = client.patch(
            f"/transactions/{txn['_id']}",
            json={"category_id": cat2["_id"]},
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["category_id"] == cat2["_id"]

    def test_update_with_mismatched_category_type_fails(self, client, auth):
        """Swapping to a credit-typed category on a debit transaction should fail."""
        debit_cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        credit_cat = create_category(client, auth["headers"], CATEGORY_CREDIT_PAYLOAD)
        txn = create_transaction(client, auth["headers"], debit_cat["_id"], type="debit")
        resp = client.patch(
            f"/transactions/{txn['_id']}",
            json={"category_id": credit_cat["_id"]},
            headers=auth["headers"],
        )
        assert resp.status_code == 400

    def test_update_empty_body_returns_400(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        txn = create_transaction(client, auth["headers"], cat["_id"])
        resp = client.patch(
            f"/transactions/{txn['_id']}",
            json={},
            headers=auth["headers"],
        )
        assert resp.status_code == 400

    def test_update_nonexistent_returns_404(self, client, auth):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.patch(
            f"/transactions/{fake_id}",
            json={"amount": 10.0},
            headers=auth["headers"],
        )
        assert resp.status_code == 404

    def test_update_other_users_transaction_returns_404(self, client, auth, auth2):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        txn = create_transaction(client, auth["headers"], cat["_id"])
        resp = client.patch(
            f"/transactions/{txn['_id']}",
            json={"amount": 1.0},
            headers=auth2["headers"],
        )
        assert resp.status_code == 404

    def test_update_requires_auth(self, client):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.patch(f"/transactions/{fake_id}", json={"amount": 10.0})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /transactions/{transaction_id}
# ---------------------------------------------------------------------------

class TestDeleteTransaction:
    def test_delete_success(self, client, auth):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        txn = create_transaction(client, auth["headers"], cat["_id"])
        resp = client.delete(f"/transactions/{txn['_id']}", headers=auth["headers"])
        assert resp.status_code == 204

        # Verify it's gone
        resp2 = client.get(f"/transactions/{txn['_id']}", headers=auth["headers"])
        assert resp2.status_code == 404

    def test_delete_nonexistent_returns_404(self, client, auth):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.delete(f"/transactions/{fake_id}", headers=auth["headers"])
        assert resp.status_code == 404

    def test_delete_other_users_transaction_returns_404(self, client, auth, auth2):
        cat = create_category(client, auth["headers"], CATEGORY_DEBIT_PAYLOAD)
        txn = create_transaction(client, auth["headers"], cat["_id"])
        resp = client.delete(f"/transactions/{txn['_id']}", headers=auth2["headers"])
        assert resp.status_code == 404
        # Owner should still see it
        resp2 = client.get(f"/transactions/{txn['_id']}", headers=auth["headers"])
        assert resp2.status_code == 200

    def test_delete_requires_auth(self, client):
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.delete(f"/transactions/{fake_id}")
        assert resp.status_code == 401

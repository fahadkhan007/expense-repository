"""
Tests for the /reports router.

Covers:
  GET /reports/          – all-time report (no date filter)
  GET /reports/?start_date=&end_date=  – date-filtered report
  GET /reports/          – auth guard
  GET /reports/          – user isolation (no cross-user data)

Report structure validated:
  - period
  - summary  (totals, counts, averages, net_cash_flow, savings_rate)
  - expenses_by_category / credits_by_category
  - cash_flow_trend
  - top_expenses / top_credits
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_category(client: TestClient, headers: dict, payload: dict) -> dict:
    resp = client.post("/categories/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_transaction(client: TestClient, headers: dict, category_id: str, **overrides) -> dict:
    body = {
        "type": "debit",
        "amount": 50.0,
        "category_id": category_id,
        **overrides,
    }
    resp = client.post("/transactions/", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def get_report(client: TestClient, headers: dict, **params) -> dict:
    resp = client.get("/reports/", params=params, headers=headers)
    return resp


DEBIT_CAT = {"name": "Food", "type": "debit", "icon": "🍔", "color": "#FF5722"}
CREDIT_CAT = {"name": "Salary", "type": "credit", "icon": "💰", "color": "#4CAF50"}


# ---------------------------------------------------------------------------
# GET /reports/  — auth
# ---------------------------------------------------------------------------

class TestReportAuth:
    def test_requires_auth(self, client):
        resp = client.get("/reports/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /reports/  — empty state (new user, no transactions)
# ---------------------------------------------------------------------------

class TestReportEmpty:
    def test_empty_report_structure(self, client, auth):
        resp = get_report(client, auth["headers"])
        assert resp.status_code == 200
        data = resp.json()

        # Top-level keys must exist
        assert "period" in data
        assert "summary" in data
        assert "expenses_by_category" in data
        assert "credits_by_category" in data
        assert "cash_flow_trend" in data
        assert "top_expenses" in data
        assert "top_credits" in data

    def test_empty_report_period_is_all_time(self, client, auth):
        data = get_report(client, auth["headers"]).json()
        assert data["period"]["type"] == "all_time"
        assert data["period"]["start_date"] is None
        assert data["period"]["end_date"] is None

    def test_empty_report_summary_zeroed(self, client, auth):
        summary = get_report(client, auth["headers"]).json()["summary"]
        assert summary["total_expenses"] == 0.0
        assert summary["total_credits"] == 0.0
        assert summary["expense_count"] == 0
        assert summary["credit_count"] == 0
        assert summary["net_cash_flow"] == 0.0
        assert summary["savings_rate"] is None  # no credits → undefined

    def test_empty_report_lists_are_empty(self, client, auth):
        data = get_report(client, auth["headers"]).json()
        assert data["expenses_by_category"] == []
        assert data["credits_by_category"] == []
        assert data["cash_flow_trend"] == []
        assert data["top_expenses"] == []
        assert data["top_credits"] == []


# ---------------------------------------------------------------------------
# GET /reports/  — with transactions
# ---------------------------------------------------------------------------

class TestReportWithData:
    def test_summary_totals_correct(self, client, auth):
        debit_cat = create_category(client, auth["headers"], DEBIT_CAT)
        credit_cat = create_category(client, auth["headers"], CREDIT_CAT)

        create_transaction(client, auth["headers"], debit_cat["_id"], type="debit", amount=100.0)
        create_transaction(client, auth["headers"], debit_cat["_id"], type="debit", amount=200.0)
        create_transaction(client, auth["headers"], credit_cat["_id"], type="credit", amount=500.0)

        summary = get_report(client, auth["headers"]).json()["summary"]
        assert summary["total_expenses"] == 300.0
        assert summary["total_credits"] == 500.0
        assert summary["expense_count"] == 2
        assert summary["credit_count"] == 1
        assert summary["net_cash_flow"] == 200.0  # 500 - 300

    def test_savings_rate_calculated(self, client, auth):
        debit_cat = create_category(client, auth["headers"], DEBIT_CAT)
        credit_cat = create_category(client, auth["headers"], CREDIT_CAT)
        create_transaction(client, auth["headers"], debit_cat["_id"], type="debit", amount=200.0)
        create_transaction(client, auth["headers"], credit_cat["_id"], type="credit", amount=400.0)

        summary = get_report(client, auth["headers"]).json()["summary"]
        # savings_rate = (net / credits) * 100 = (200/400)*100 = 50.0
        assert summary["savings_rate"] == 50.0

    def test_category_breakdown_present(self, client, auth):
        debit_cat = create_category(client, auth["headers"], DEBIT_CAT)
        create_transaction(client, auth["headers"], debit_cat["_id"], type="debit", amount=80.0)

        data = get_report(client, auth["headers"]).json()
        expenses_by_cat = data["expenses_by_category"]
        assert len(expenses_by_cat) == 1
        entry = expenses_by_cat[0]
        assert entry["total_amount"] == 80.0
        assert entry["category_name"] == "Food"
        assert entry["percentage"] == 100.0
        assert "transaction_count" in entry
        assert "average_amount" in entry

    def test_category_breakdown_percentages_sum_to_100(self, client, auth):
        debit_cat1 = create_category(client, auth["headers"], {**DEBIT_CAT, "name": "Food2"})
        debit_cat2 = create_category(client, auth["headers"], {**DEBIT_CAT, "name": "Transport2"})
        create_transaction(client, auth["headers"], debit_cat1["_id"], type="debit", amount=300.0)
        create_transaction(client, auth["headers"], debit_cat2["_id"], type="debit", amount=700.0)

        expenses_by_cat = get_report(client, auth["headers"]).json()["expenses_by_category"]
        total_pct = sum(e["percentage"] for e in expenses_by_cat)
        assert abs(total_pct - 100.0) < 0.01

    def test_category_breakdown_sorted_descending(self, client, auth):
        debit_cat1 = create_category(client, auth["headers"], {**DEBIT_CAT, "name": "Cheap"})
        debit_cat2 = create_category(client, auth["headers"], {**DEBIT_CAT, "name": "Expensive"})
        create_transaction(client, auth["headers"], debit_cat1["_id"], type="debit", amount=10.0)
        create_transaction(client, auth["headers"], debit_cat2["_id"], type="debit", amount=500.0)

        expenses = get_report(client, auth["headers"]).json()["expenses_by_category"]
        amounts = [e["total_amount"] for e in expenses]
        assert amounts == sorted(amounts, reverse=True)

    def test_cash_flow_trend_has_month_entry(self, client, auth):
        debit_cat = create_category(client, auth["headers"], DEBIT_CAT)
        create_transaction(client, auth["headers"], debit_cat["_id"], type="debit", amount=50.0)

        trend = get_report(client, auth["headers"]).json()["cash_flow_trend"]
        assert len(trend) >= 1
        entry = trend[0]
        assert "month" in entry
        assert "total_expenses" in entry
        assert "total_credits" in entry
        assert "net_cash_flow" in entry
        assert "transaction_count" in entry

    def test_top_expenses_returned(self, client, auth):
        debit_cat = create_category(client, auth["headers"], DEBIT_CAT)
        for amount in [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]:
            create_transaction(client, auth["headers"], debit_cat["_id"], type="debit", amount=amount)

        top = get_report(client, auth["headers"]).json()["top_expenses"]
        assert len(top) == 5  # default limit
        # Should be sorted by amount descending
        amounts = [t["amount"] for t in top]
        assert amounts == sorted(amounts, reverse=True)

    def test_top_credits_returned(self, client, auth):
        credit_cat = create_category(client, auth["headers"], CREDIT_CAT)
        for amount in [100.0, 200.0, 300.0, 400.0, 500.0, 600.0]:
            create_transaction(client, auth["headers"], credit_cat["_id"], type="credit", amount=amount)

        top = get_report(client, auth["headers"]).json()["top_credits"]
        assert len(top) == 5
        amounts = [t["amount"] for t in top]
        assert amounts == sorted(amounts, reverse=True)


# ---------------------------------------------------------------------------
# GET /reports/  — user isolation
# ---------------------------------------------------------------------------

class TestReportIsolation:
    def test_report_only_shows_own_data(self, client, auth, auth2):
        debit_cat = create_category(client, auth["headers"], DEBIT_CAT)
        create_transaction(client, auth["headers"], debit_cat["_id"], type="debit", amount=999.0)

        # auth2 should see empty report, not auth's data
        summary = get_report(client, auth2["headers"]).json()["summary"]
        assert summary["total_expenses"] == 0.0
        assert summary["expense_count"] == 0


# ---------------------------------------------------------------------------
# GET /reports/  — date filtering
# ---------------------------------------------------------------------------

class TestReportDateFilter:
    def test_both_dates_required(self, client, auth):
        # Providing only start_date should return 400
        resp = client.get(
            "/reports/",
            params={"start_date": "2024-01-01T00:00:00Z"},
            headers=auth["headers"],
        )
        assert resp.status_code == 400

    def test_both_dates_required_end_only(self, client, auth):
        # Providing only end_date should return 400
        resp = client.get(
            "/reports/",
            params={"end_date": "2024-12-31T23:59:59Z"},
            headers=auth["headers"],
        )
        assert resp.status_code == 400

    def test_start_after_end_returns_400(self, client, auth):
        resp = client.get(
            "/reports/",
            params={
                "start_date": "2024-12-01T00:00:00Z",
                "end_date": "2024-01-01T00:00:00Z",
            },
            headers=auth["headers"],
        )
        assert resp.status_code == 400

    def test_start_equal_end_returns_400(self, client, auth):
        resp = client.get(
            "/reports/",
            params={
                "start_date": "2024-06-01T00:00:00Z",
                "end_date": "2024-06-01T00:00:00Z",
            },
            headers=auth["headers"],
        )
        assert resp.status_code == 400

    def test_valid_date_range_returns_custom_period(self, client, auth):
        resp = client.get(
            "/reports/",
            params={
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2030-01-01T00:00:00Z",
            },
            headers=auth["headers"],
        )
        assert resp.status_code == 200
        period = resp.json()["period"]
        assert period["type"] == "custom"
        assert period["start_date"] is not None
        assert period["end_date"] is not None

    def test_naive_datetime_returns_400(self, client, auth):
        """Dates without timezone info must be rejected."""
        resp = client.get(
            "/reports/",
            params={
                "start_date": "2024-01-01T00:00:00",   # no tz
                "end_date": "2024-12-31T23:59:59",      # no tz
            },
            headers=auth["headers"],
        )
        assert resp.status_code == 400

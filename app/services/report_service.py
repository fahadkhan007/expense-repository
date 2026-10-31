
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.database.connectdb import db


def build_match_stage(
    user_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    match = {"user_id": user_id}

    if start_date is not None and end_date is not None:
        match["created_at"] = {
            "$gte": start_date,
            "$lt": end_date,
        }

    return match


async def get_financial_summary(match: dict) -> dict:
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$type",
                "total_amount": {"$sum": "$amount"},
                "transaction_count": {"$sum": 1},
                "average_amount": {"$avg": "$amount"},
            }
        },
    ]

    cursor = await db.transactions.aggregate(pipeline)
    results = await cursor.to_list(length=None)

    summary = {
        "total_expenses": 0.0,
        "total_credits": 0.0,
        "expense_count": 0,
        "credit_count": 0,
        "average_expense": 0.0,
        "average_credit": 0.0,
    }

    for result in results:
        if result["_id"] == "debit":
            summary["total_expenses"] = result["total_amount"]
            summary["expense_count"] = result["transaction_count"]
            summary["average_expense"] = result["average_amount"]

        elif result["_id"] == "credit":
            summary["total_credits"] = result["total_amount"]
            summary["credit_count"] = result["transaction_count"]
            summary["average_credit"] = result["average_amount"]

    summary["net_cash_flow"] = (
        summary["total_credits"] - summary["total_expenses"]
    )

    summary["transaction_count"] = (
        summary["expense_count"] + summary["credit_count"]
    )

    if summary["total_credits"] > 0:
        summary["savings_rate"] = round(
            (summary["net_cash_flow"] / summary["total_credits"]) * 100,
            2,
        )
    else:
        summary["savings_rate"] = None

    return summary


async def get_category_breakdown(
    user_id: UUID,
    match: dict,
) -> dict:
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {
                    "category_id": "$category_id",
                    "type": "$type",
                },
                "total_amount": {"$sum": "$amount"},
                "transaction_count": {"$sum": 1},
                "average_amount": {"$avg": "$amount"},
            }
        },
    ]

    cursor = await db.transactions.aggregate(pipeline)
    results = await cursor.to_list(length=None)

    category_ids = list({
        result["_id"]["category_id"] for result in results
    })

    categories = await db.categories.find(
        {
            "_id": {"$in": category_ids},
            "user_id": user_id,
        },
        {
            "_id": 1,
            "name": 1,
            "icon": 1,
            "color": 1,
        },
    ).to_list(length=None)

    category_map = {
        category["_id"]: category for category in categories
    }

    total_expenses = sum(
        result["total_amount"]
        for result in results
        if result["_id"]["type"] == "debit"
    )

    total_credits = sum(
        result["total_amount"]
        for result in results
        if result["_id"]["type"] == "credit"
    )

    expenses = []
    credits = []

    for result in results:
        category_id = result["_id"]["category_id"]
        transaction_type = result["_id"]["type"]

        category = category_map.get(category_id, {})

        amount = result["total_amount"]

        if transaction_type == "debit":
            percentage = (
                (amount / total_expenses) * 100
                if total_expenses > 0 else 0
            )
            expenses.append({
                "category_id": category_id,
                "category_name": category.get("name", "Unknown"),
                "icon": category.get("icon"),
                "color": category.get("color"),
                "total_amount": amount,
                "transaction_count": result["transaction_count"],
                "average_amount": result["average_amount"],
                "percentage": round(percentage, 2),
            })

        elif transaction_type == "credit":
            percentage = (
                (amount / total_credits) * 100
                if total_credits > 0 else 0
            )
            credits.append({
                "category_id": category_id,
                "category_name": category.get("name", "Unknown"),
                "icon": category.get("icon"),
                "color": category.get("color"),
                "total_amount": amount,
                "transaction_count": result["transaction_count"],
                "average_amount": result["average_amount"],
                "percentage": round(percentage, 2),
            })

    expenses.sort(key=lambda item: item["total_amount"], reverse=True)
    credits.sort(key=lambda item: item["total_amount"], reverse=True)

    return {
        "expenses_by_category": expenses,
        "credits_by_category": credits,
    }


async def get_cash_flow_trend(match: dict) -> list:
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m",
                        "date": "$created_at",
                        "timezone": "UTC",
                    }
                },
                "total_expenses": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$type", "debit"]},
                            "$amount",
                            0,
                        ]
                    }
                },
                "total_credits": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$type", "credit"]},
                            "$amount",
                            0,
                        ]
                    }
                },
                "transaction_count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    cursor = await db.transactions.aggregate(pipeline)
    results = await cursor.to_list(length=None)

    trends = []

    for result in results:
        expenses = result["total_expenses"]
        credits = result["total_credits"]

        trends.append({
            "month": result["_id"],
            "total_expenses": expenses,
            "total_credits": credits,
            "net_cash_flow": credits - expenses,
            "transaction_count": result["transaction_count"],
        })

    return trends


async def get_top_transactions(match: dict, limit: int = 5) -> dict:
    expenses = await db.transactions.find(
        {**match, "type": "debit"}
    ).sort("amount", -1).limit(limit).to_list(length=limit)

    credits = await db.transactions.find(
        {**match, "type": "credit"}
    ).sort("amount", -1).limit(limit).to_list(length=limit)

    return {
        "top_expenses": expenses,
        "top_credits": credits,
    }


async def generate_financial_report(
    user_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    if (start_date is None) != (end_date is None):
        raise ValueError("Both start_date and end_date must be provided.")

    if start_date is not None:
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError("Dates must be timezone-aware.")

        if start_date >= end_date:
            raise ValueError("start_date must be before end_date.")

    match = build_match_stage(user_id, start_date, end_date)

    summary = await get_financial_summary(match)

    category_breakdown = await get_category_breakdown(
        user_id,
        match,
    )

    cash_flow_trend = await get_cash_flow_trend(match)

    top_transactions = await get_top_transactions(match)

    report = {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "type": "custom" if start_date else "all_time",
        },
        "summary": summary,
        **category_breakdown,
        "cash_flow_trend": cash_flow_trend,
        **top_transactions,
    }

    return report
 
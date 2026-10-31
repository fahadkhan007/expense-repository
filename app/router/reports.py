
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user
from app.services.report_service import generate_financial_report

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.get("/")
async def get_report(
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    user: dict = Depends(get_current_user),
):
    try:
        report = await generate_financial_report(
            user_id=user["_id"],
            start_date=start_date,
            end_date=end_date,
        )

        return report

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

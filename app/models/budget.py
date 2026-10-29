
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.base import Base


class BudgetCreate(BaseModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    limit: float = Field(gt=0, allow_inf_nan=False)


class BudgetUpdate(BaseModel):
    limit: float = Field(gt=0, allow_inf_nan=False)


class BudgetResponse(Base):
    user_id: UUID
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    limit: float

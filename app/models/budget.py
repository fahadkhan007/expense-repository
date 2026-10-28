from uuid import UUID

from pydantic import BaseModel, Field

from app.models.base import Base


class CategoryBudget(BaseModel):
    category_id: UUID
    limit: float = Field(gt=0, allow_inf_nan=False)


class BudgetCreate(BaseModel):
    user_id: UUID
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    category_budgets: list[CategoryBudget] = Field(min_length=1)
    
    


class BudgetResponse(Base):
    user_id: UUID
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    category_budgets: list[CategoryBudget]
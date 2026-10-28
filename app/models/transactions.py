from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.base import Base


class TransactionCreate(BaseModel):
    type: Literal["debit", "credit"]
    amount: float = Field(gt=0, allow_inf_nan=False)
    category_id: UUID
    description: str | None = Field(default=None, max_length=300)


class TransactionResponse(Base):
    
    user_id: UUID
    type: Literal["debit", "credit"]
    amount: float
    category_id: UUID
    description: str | None = None
    created_at: datetime
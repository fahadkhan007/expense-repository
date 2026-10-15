
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    user_id: UUID
    type: Literal["debit", "credit"]
    amount: float = Field(gt=0, description="The amount of the transaction. Must be greater than 0.")
    category_id: UUID
    description: str
    


class TransactionResponse(BaseModel):
    id: UUID
    user_id: UUID
    type: Literal["debit", "credit"]
    amount: float
    category_id: UUID
    description: str
    dateTime: datetime
    

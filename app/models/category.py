from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from app.models.base import Base

catName = Annotated[str, StringConstraints(min_length=1, max_length=50, strip_whitespace=True)]

class CategoryCreate(BaseModel):
    name: catName
    type: Literal["debit", "credit"] | None = None
    icon: str
    color: str


class CategoryResponse(Base):
    user_id: UUID
    name: str
    type: Literal["debit", "credit"] | None = None
    icon: str
    color: str
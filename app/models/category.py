from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints

catName = Annotated[str, StringConstraints(min_length=1, max_length=50, strip_whitespace=True)]

class CategoryCreate(BaseModel):
    user_id: UUID
    name: catName
    type: Literal["debit", "credit"] | None = None
    icon: str
    color: str


class CategoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    type: Literal["debit", "credit"] | None = None
    icon: str
    color: str
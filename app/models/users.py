
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

userName = Annotated[str, StringConstraints(min_length=3, max_length=50, strip_whitespace=True)]


class UserCreate(BaseModel):
    name: userName
    email: str 
    password_hash: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    created_at: datetime

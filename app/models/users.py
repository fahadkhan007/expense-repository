from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints

userName = Annotated[str, StringConstraints(min_length=3, max_length=50, strip_whitespace=True)]


class UserCreate(BaseModel):
    name: userName
    email: EmailStr
    password: str = Field(
            ..., min_length=6, 
            max_length=32,
            description="Password must be between 6 and 32 characters long."
        )
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    created_at: datetime

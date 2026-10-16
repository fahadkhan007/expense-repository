from app.models.users import UserResponse

from pydantic import BaseModel

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    
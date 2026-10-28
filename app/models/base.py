from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Base(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)
    
    id: UUID = Field(..., alias="_id")
    
    
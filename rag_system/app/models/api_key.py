from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class APIKey(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    key_hash: str = Field(..., description="Bcrypt hash of the API key")
    agent_id: str = Field(..., description="Reference to agent ID")
    name: str = Field(..., description="Human-readable key name")
    is_active: bool = Field(default=True, description="Whether key is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = Field(default=None, description="Last usage timestamp")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class APIKeyCreate(BaseModel):
    agent_id: str
    name: str


class APIKeyResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None
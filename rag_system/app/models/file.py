from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class File(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    agent_id: str = Field(..., description="Reference to agent ID")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    chunk_count: int = Field(default=0, description="Number of chunks created")
    is_deleted: bool = Field(default=False, description="Soft delete flag")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class FileCreate(BaseModel):
    agent_id: str
    filename: str
    content_type: str
    size: int


class FileResponse(BaseModel):
    id: str
    agent_id: str
    filename: str
    content_type: str
    size: int
    chunk_count: int
    is_deleted: bool
    created_at: datetime
    deleted_at: Optional[datetime] = None
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId


class Agent(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: str = Field(..., description="Unique agent name")
    description: Optional[str] = None
    system_prompt: str = Field(..., description="System prompt defining agent behavior")
    chat_model: str = Field(default="llama3.1", description="Ollama chat model name")
    embedding_model: str = Field(default="nomic-embed-text", description="Embedding model name")
    is_active: bool = Field(default=True, description="Whether agent is active")
    max_chat_history: int = Field(default=10, description="Maximum chat history length")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    chat_model: str = "llama3.1"
    embedding_model: str = "nomic-embed-text"
    max_chat_history: int = 10


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    chat_model: Optional[str] = None
    embedding_model: Optional[str] = None
    is_active: Optional[bool] = None
    max_chat_history: Optional[int] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    system_prompt: str
    chat_model: str
    embedding_model: str
    is_active: bool
    max_chat_history: int
    created_at: datetime
    updated_at: datetime
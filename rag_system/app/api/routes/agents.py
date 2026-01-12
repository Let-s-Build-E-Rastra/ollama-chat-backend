from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from app.db.mongodb import mongodb
from app.db.qdrant import qdrant_db
from app.models.agent import Agent, AgentCreate, AgentUpdate, AgentResponse
from app.models.api_key import APIKeyCreate, APIKeyResponse
from app.core.security import security_manager
from app.core.config import settings


router = APIRouter()


@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,
    current_agent: Agent = Depends(None)  # Will be injected by middleware
):
    """Create a new agent"""
    # Check if agent with same name exists
    existing_agent = await mongodb.get_agent_by_name(agent_data.name)
    if existing_agent:
        raise HTTPException(
            status_code=400,
            detail=f"Agent with name '{agent_data.name}' already exists"
        )
    
    # Validate chat model
    if agent_data.chat_model not in settings.approved_chat_models:
        raise HTTPException(
            status_code=400,
            detail=f"Chat model '{agent_data.chat_model}' is not approved"
        )
    
    # Validate embedding model
    if agent_data.embedding_model not in settings.approved_embedding_models:
        raise HTTPException(
            status_code=400,
            detail=f"Embedding model '{agent_data.embedding_model}' is not approved"
        )
    
    # Create agent
    agent = await mongodb.create_agent(agent_data)
    
    # Create Qdrant collection
    from app.rag.embedder import embedder
    vector_size = await embedder.get_embedding_dimension(agent_data.embedding_model)
    if vector_size:
        await qdrant_db.create_collection(agent.id, vector_size)
    
    return AgentResponse(**agent.model_dump())


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    skip: int = Query(0, ge=0, description="Number of agents to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of agents to return"),
    current_agent: Agent = Depends(None)
):
    """List all agents"""
    agents = await mongodb.list_agents(skip=skip, limit=limit)
    return [AgentResponse(**agent.model_dump()) for agent in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_agent: Agent = Depends(None)
):
    """Get agent by ID"""
    agent = await mongodb.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )
    
    return AgentResponse(**agent.model_dump())


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    update_data: AgentUpdate,
    current_agent: Agent = Depends(None)
):
    """Update agent"""
    # Validate models if being updated
    if update_data.chat_model and update_data.chat_model not in settings.approved_chat_models:
        raise HTTPException(
            status_code=400,
            detail=f"Chat model '{update_data.chat_model}' is not approved"
        )
    
    if update_data.embedding_model and update_data.embedding_model not in settings.approved_embedding_models:
        raise HTTPException(
            status_code=400,
            detail=f"Embedding model '{update_data.embedding_model}' is not approved"
        )
    
    agent = await mongodb.update_agent(agent_id, update_data)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )
    
    return AgentResponse(**agent.model_dump())


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_agent: Agent = Depends(None)
):
    """Delete agent (soft delete)"""
    agent = await mongodb.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )
    
    # Soft delete by setting inactive
    await mongodb.update_agent(agent_id, {"is_active": False})
    
    # Optionally delete Qdrant collection
    # await qdrant_db.delete_collection(agent_id)
    
    return {"message": "Agent deleted successfully"}


@router.post("/{agent_id}/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    agent_id: str,
    key_data: APIKeyCreate,
    current_agent: Agent = Depends(None)
):
    """Create a new API key for an agent"""
    # Verify agent exists
    agent = await mongodb.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )
    
    # Generate API key
    import secrets
    api_key = f"rag_{secrets.token_urlsafe(32)}"
    
    # Hash API key
    key_hash = security_manager.hash_api_key(api_key)
    
    # Create API key record
    api_key_record = await mongodb.create_api_key(key_data, key_hash)
    
    return APIKeyResponse(**api_key_record.model_dump())


@router.get("/{agent_id}/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    agent_id: str,
    current_agent: Agent = Depends(None)
):
    """List API keys for an agent"""
    keys = await mongodb.list_api_keys_by_agent(agent_id)
    return [APIKeyResponse(**key.model_dump()) for key in keys]


@router.get("/{agent_id}/stats")
async def get_agent_stats(
    agent_id: str,
    current_agent: Agent = Depends(None)
):
    """Get agent statistics"""
    agent = await mongodb.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )
    
    # Get file count
    file_count = await mongodb.get_file_count_by_agent(agent_id)
    
    # Get API key count
    api_keys = await mongodb.list_api_keys_by_agent(agent_id)
    
    return {
        "agent": AgentResponse(**agent.model_dump()),
        "stats": {
            "file_count": file_count,
            "api_key_count": len(api_keys),
            "is_active": agent.is_active
        }
    }
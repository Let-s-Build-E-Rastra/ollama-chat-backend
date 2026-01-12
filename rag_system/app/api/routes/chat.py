from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.db.mongodb import mongodb
from app.models.agent import Agent
from app.rag.retriever import retriever
from app.services.llm_service import LLMService


router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    use_hybrid_search: bool = True
    use_reranking: bool = True
    retrieval_limit: int = 10
    include_sources: bool = True


class ChatResponse(BaseModel):
    query: str
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    retrieval_results: Optional[List[Dict[str, Any]]] = None
    model_used: str
    agent_id: str


class ChatResponseStream(BaseModel):
    type: str  # "context", "response", "done"
    data: Optional[Dict[str, Any]] = None


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_agent: Agent = Depends(None)
):
    """Send a query to the agent and get a response"""
    try:
        # Validate query
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty"
            )
        
        # Retrieve context
        retrieval_results = await retriever.retrieve_context(
            agent_id=str(current_agent.id),
            query=request.query,
            embedding_model=current_agent.embedding_model,
            limit=request.retrieval_limit,
            use_hybrid=request.use_hybrid_search,
            rerank=request.use_reranking,
            score_threshold=settings.min_relevance_score
        )
        
        # Check if we have sufficient context
        if not retrieval_results:
            return ChatResponse(
                query=request.query,
                response="The information is not available in the provided knowledge base.",
                sources=None,
                retrieval_results=None,
                model_used=current_agent.chat_model,
                agent_id=str(current_agent.id)
            )
        
        # Prepare context for LLM
        context_parts = []
        sources = []
        
        for result in retrieval_results:
            payload = result.get("payload", {})
            content = payload.get("content", "")
            section = payload.get("section", "")
            source = payload.get("source", "Unknown")
            score = result.get("score", 0)
            
            # Build context entry
            context_entry = f"[Source: {source}{' - ' + section if section else ''}]\n{content}"
            context_parts.append(context_entry)
            
            # Build source info
            if request.include_sources:
                sources.append({
                    "source": source,
                    "section": section,
                    "score": score,
                    "content_preview": content[:200] + "..." if len(content) > 200 else content
                })
        
        # Combine context
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate response using LLM
        llm_service = LLMService(settings.ollama_url)
        response = await llm_service.generate_response(
            query=request.query,
            context=context,
            system_prompt=current_agent.system_prompt,
            model_name=current_agent.chat_model
        )
        
        return ChatResponse(
            query=request.query,
            response=response,
            sources=sources if request.include_sources else None,
            retrieval_results=retrieval_results if request.include_sources else None,
            model_used=current_agent.chat_model,
            agent_id=str(current_agent.id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/context")
async def retrieve_context_only(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    use_hybrid: bool = Query(True, description="Use hybrid search"),
    include_scores: bool = Query(True, description="Include relevance scores"),
    current_agent: Agent = Depends(None)
):
    """Retrieve context without generating a response"""
    try:
        # Retrieve context
        results = await retriever.retrieve_context(
            agent_id=str(current_agent.id),
            query=query,
            embedding_model=current_agent.embedding_model,
            limit=limit,
            use_hybrid=use_hybrid,
            rerank=True,
            score_threshold=settings.min_relevance_score
        )
        
        # Format results
        formatted_results = []
        for result in results:
            payload = result.get("payload", {})
            formatted_result = {
                "id": result.get("id"),
                "source": payload.get("source", "Unknown"),
                "section": payload.get("section", ""),
                "content": payload.get("content", ""),
            }
            
            if include_scores:
                formatted_result["score"] = result.get("score", 0)
            
            formatted_results.append(formatted_result)
        
        return {
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results,
            "agent_id": str(current_agent.id),
            "embedding_model": current_agent.embedding_model
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving context: {str(e)}"
        )


@router.get("/models")
async def get_available_models(
    current_agent: Agent = Depends(None)
):
    """Get available models for the current agent"""
    return {
        "chat_models": settings.approved_chat_models,
        "embedding_models": settings.approved_embedding_models,
        "rerankers": settings.approved_rerankers,
        "agent_configured": {
            "chat_model": current_agent.chat_model,
            "embedding_model": current_agent.embedding_model
        }
    }
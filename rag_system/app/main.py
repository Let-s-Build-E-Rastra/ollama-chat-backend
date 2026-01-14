from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from app.core.config import settings
from app.core.security import security_manager
from app.db.mongodb import mongodb
from app.db.qdrant import qdrant_db
from app.api.routes import agents, files, chat
from app.models.agent import AgentResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Multi-Agent RAG System...")
    
    # Connect to databases
    await mongodb.connect()
    await qdrant_db.connect()
    
    logger.info("Connected to MongoDB and Qdrant")
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await mongodb.disconnect()
    await qdrant_db.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-grade Multi-Agent RAG System",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key and return associated agent"""
    api_key = credentials.credentials
    
    # Hash the provided API key and check against stored hash
    # For now, we'll use a simple lookup (in production, use proper hashing)
    api_key_record = await mongodb.get_api_key_by_hash(api_key)
    
    if not api_key_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    if not api_key_record.is_active:
        raise HTTPException(
            status_code=401,
            detail="API key is deactivated"
        )
    
    # Get associated agent
    agent = await mongodb.get_active_agent(api_key_record.agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=401,
            detail="Associated agent not found or inactive"
        )
    
    # Update last used timestamp
    await mongodb.update_api_key_last_used(api_key_record.id)
    
    return agent


# Include routers
app.include_router(
    agents.router,
    prefix="/api/v1/agents",
    tags=["agents"],
)

app.include_router(
    files.router,
    prefix="/api/v1/files",
    tags=["files"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    chat.router,
    prefix="/api/v1/chat",
    tags=["chat"],
    dependencies=[Depends(verify_api_key)]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB
        await mongodb.db.command("ping")
        
        # Check Qdrant
        await qdrant_db.client.get_collections()
        
        return {
            "status": "healthy",
            "mongodb": "connected",
            "qdrant": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
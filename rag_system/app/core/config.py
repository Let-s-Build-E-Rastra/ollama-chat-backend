from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Multi-Agent RAG System"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    api_key_hash_rounds: int = 12
    
    # MongoDB
    mongodb_url: str = Field(..., env="MONGODB_URL")
    mongodb_database: str = Field(..., env="MONGODB_DATABASE")
    
    # Qdrant
    qdrant_url: str = Field(..., env="QDRANT_URL")
    qdrant_api_key: Optional[str] = None
    
    # Ollama
    ollama_url: str = Field(..., env="OLLAMA_URL")
    ollama_default_chat_model: str = "llama3.1"
    ollama_default_embedding_model: str = "nomic-embed-text"
    
    # RAG Settings
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    default_chunk_size: int = 512
    default_chunk_overlap: int = 50
    max_retrieval_results: int = 20
    reranker_top_k: int = 10
    min_relevance_score: float = 0.7
    
    # Embedding Models
    approved_embedding_models: list[str] = [
        "nomic-embed-text",
        "bge-m3",
        "e5-large",
        "gte-large"
    ]
    
    # Chat Models
    approved_chat_models: list[str] = [
        "llama3.1",
        "qwen2.5",
        "mistral-nemo",
        "phi-3.5"
    ]
    
    # Rerankers
    approved_rerankers: list[str] = [
        "bge-reranker",
        "cross-encoder/ms-marco",
        "colbert"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
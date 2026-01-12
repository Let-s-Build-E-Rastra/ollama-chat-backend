import asyncio
import httpx
from typing import List, Optional
from loguru import logger

from app.core.config import settings


class Embedder:
    """Text embedding service using Ollama"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0  # Long timeout for embedding operations
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_model(self, model_name: str) -> bool:
        """Check if a model is available in Ollama"""
        try:
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(model["name"] == model_name for model in models)
            return False
        except Exception as e:
            logger.error(f"Error checking model {model_name}: {e}")
            return False
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model to Ollama"""
        try:
            response = await self.client.post(
                "/api/pull",
                json={"name": model_name}
            )
            # Pull is async, so we'll just check if the request was accepted
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    async def get_embedding(
        self,
        text: str,
        model_name: str,
        normalize: bool = True
    ) -> Optional[List[float]]:
        """Get embedding for a single text"""
        try:
            # Ensure model is available
            if not await self.check_model(model_name):
                logger.info(f"Model {model_name} not found, attempting to pull...")
                if not await self.pull_model(model_name):
                    logger.error(f"Failed to pull model {model_name}")
                    return None
            
            # Get embedding
            response = await self.client.post(
                "/api/embeddings",
                json={
                    "model": model_name,
                    "prompt": text,
                    "options": {
                        "normalize": normalize
                    }
                }
            )
            
            if response.status_code == 200:
                embedding = response.json().get("embedding")
                if embedding:
                    return embedding
                else:
                    logger.error(f"No embedding in response for model {model_name}")
                    return None
            else:
                logger.error(f"Embedding API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None
    
    async def get_embeddings_batch(
        self,
        texts: List[str],
        model_name: str,
        normalize: bool = True,
        batch_size: int = 10
    ) -> List[Optional[List[float]]]:
        """Get embeddings for multiple texts"""
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Process batch concurrently
            batch_embeddings = await asyncio.gather(*[
                self.get_embedding(text, model_name, normalize)
                for text in batch
            ])
            
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    async def validate_embedding_model(self, model_name: str) -> bool:
        """Validate that an embedding model is approved"""
        return model_name in settings.approved_embedding_models
    
    async def get_model_info(self, model_name: str) -> Optional[dict]:
        """Get information about a model"""
        try:
            response = await self.client.post(
                "/api/show",
                json={"name": model_name}
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None
    
    async def get_embedding_dimension(self, model_name: str) -> Optional[int]:
        """Get embedding dimension for a model"""
        # Try to get embedding to determine dimension
        test_text = "test"
        embedding = await self.get_embedding(test_text, model_name)
        
        if embedding:
            return len(embedding)
        
        # Fallback to known dimensions
        model_dimensions = {
            "nomic-embed-text": 768,
            "bge-m3": 1024,
            "e5-large": 1024,
            "gte-large": 1024,
        }
        
        return model_dimensions.get(model_name)


# Global embedder instance
embedder = Embedder(settings.ollama_url)
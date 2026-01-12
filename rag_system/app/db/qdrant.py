from typing import Optional, List, Dict, Any
import asyncio

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    UpdateStatus
)

from app.core.config import settings


class QdrantDB:
    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None
    
    async def connect(self):
        """Connect to Qdrant"""
        if settings.qdrant_api_key:
            self.client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key
            )
        else:
            self.client = AsyncQdrantClient(url=settings.qdrant_url)
    
    async def disconnect(self):
        """Disconnect from Qdrant"""
        if self.client:
            await self.client.close()
    
    def get_collection_name(self, agent_id: str) -> str:
        """Get collection name for agent"""
        return f"rag_agent_{agent_id}"
    
    async def create_collection(self, agent_id: str, vector_size: int) -> bool:
        """Create vector collection for agent"""
        collection_name = self.get_collection_name(agent_id)
        
        try:
            # Check if collection exists
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if collection_name in collection_names:
                return True
            
            # Create new collection
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            
            # Create payload indexes
            await self.client.create_payload_index(
                collection_name=collection_name,
                field_name="file_id",
                field_schema="keyword"
            )
            
            await self.client.create_payload_index(
                collection_name=collection_name,
                field_name="section",
                field_schema="keyword"
            )
            
            return True
            
        except Exception as e:
            print(f"Error creating collection: {e}")
            return False
    
    async def delete_collection(self, agent_id: str) -> bool:
        """Delete vector collection for agent"""
        collection_name = self.get_collection_name(agent_id)
        
        try:
            await self.client.delete_collection(collection_name=collection_name)
            return True
        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False
    
    async def upsert_vectors(
        self,
        agent_id: str,
        file_id: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        chunk_indices: List[int]
    ) -> bool:
        """Insert or update vectors for a file"""
        collection_name = self.get_collection_name(agent_id)
        
        try:
            points = []
            for i, (vector, payload, chunk_idx) in enumerate(
                zip(vectors, payloads, chunk_indices)
            ):
                point_id = f"{file_id}_{chunk_idx}"
                
                # Add required payload fields
                point_payload = {
                    "agent_id": agent_id,
                    "file_id": file_id,
                    "chunk_index": chunk_idx,
                    **payload
                }
                
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=point_payload
                ))
            
            operation_info = await self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            return operation_info.status == UpdateStatus.COMPLETED
            
        except Exception as e:
            print(f"Error upserting vectors: {e}")
            return False
    
    async def delete_vectors_by_file(self, agent_id: str, file_id: str) -> bool:
        """Delete all vectors for a file"""
        collection_name = self.get_collection_name(agent_id)
        
        try:
            operation_info = await self.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="file_id",
                                match=MatchValue(value=file_id)
                            )
                        ]
                    )
                )
            )
            
            return operation_info.status == UpdateStatus.COMPLETED
            
        except Exception as e:
            print(f"Error deleting vectors: {e}")
            return False
    
    async def search_vectors(
        self,
        agent_id: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        file_id_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search vectors for an agent"""
        collection_name = self.get_collection_name(agent_id)
        
        try:
            # Build filter
            query_filter = None
            if file_id_filter:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="file_id",
                            match=models.MatchAny(any=file_id_filter)
                        )
                    ]
                )
            
            # Perform search
            search_result = await self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False
            )
            
            # Convert to dict format
            results = []
            for point in search_result:
                results.append({
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                })
            
            return results
            
        except Exception as e:
            print(f"Error searching vectors: {e}")
            return []
    
    async def hybrid_search(
        self,
        agent_id: str,
        query_vector: List[float],
        query_text: str,
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining vector and keyword search"""
        # For now, implement vector search
        # Keyword search would require additional text indexing
        return await self.search_vectors(
            agent_id=agent_id,
            query_vector=query_vector,
            limit=limit
        )
    
    async def count_vectors_by_file(self, agent_id: str, file_id: str) -> int:
        """Count vectors for a file"""
        collection_name = self.get_collection_name(agent_id)
        
        try:
            count_result = await self.client.count(
                collection_name=collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="file_id",
                            match=MatchValue(value=file_id)
                        )
                    ]
                )
            )
            return count_result.count
        except Exception as e:
            print(f"Error counting vectors: {e}")
            return 0


# Global Qdrant instance
qdrant_db = QdrantDB()
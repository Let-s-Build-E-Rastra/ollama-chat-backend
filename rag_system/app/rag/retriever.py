from typing import List, Dict, Any, Optional
import asyncio

from app.db.qdrant import qdrant_db
from app.rag.embedder import embedder


class Retriever:
    """Hybrid retrieval service for RAG pipeline"""
    
    def __init__(self):
        self.qdrant = qdrant_db
        self.embedder = embedder
    
    async def vector_search(
        self,
        agent_id: str,
        query: str,
        embedding_model: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        file_id_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        try:
            # Get query embedding
            query_embedding = await self.embedder.get_embedding(query, embedding_model)
            
            if not query_embedding:
                return []
            
            # Search in Qdrant
            results = await self.qdrant.search_vectors(
                agent_id=agent_id,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                file_id_filter=file_id_filter
            )
            
            return results
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
    
    async def keyword_search(
        self,
        agent_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform keyword-based search"""
        # This is a simplified implementation
        # In production, you'd use a proper text search engine
        # For now, return empty list as placeholder
        return []
    
    async def hybrid_search(
        self,
        agent_id: str,
        query: str,
        embedding_model: str,
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining vector and keyword search"""
        try:
            # Get vector search results
            vector_results = await self.vector_search(
                agent_id=agent_id,
                query=query,
                embedding_model=embedding_model,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Get keyword search results (placeholder)
            keyword_results = await self.keyword_search(
                agent_id=agent_id,
                query=query,
                limit=limit
            )
            
            # Combine results using weighted fusion
            combined_results = await self._fuse_results(
                vector_results,
                keyword_results,
                vector_weight,
                keyword_weight
            )
            
            # Sort by combined score and return top results
            combined_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
            return combined_results[:limit]
            
        except Exception as e:
            print(f"Error in hybrid search: {e}")
            return []
    
    async def _fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        vector_weight: float,
        keyword_weight: float
    ) -> List[Dict[str, Any]]:
        """Fuse vector and keyword search results"""
        # Create dictionaries for easy lookup
        vector_dict = {result["id"]: result for result in vector_results}
        keyword_dict = {result["id"]: result for result in keyword_results}
        
        # Get all unique result IDs
        all_ids = set(vector_dict.keys()) | set(keyword_dict.keys())
        
        fused_results = []
        
        for result_id in all_ids:
            # Get vector result (with default score of 0)
            vector_result = vector_dict.get(result_id, {})
            vector_score = vector_result.get("score", 0)
            
            # Get keyword result (with default score of 0)
            keyword_result = keyword_dict.get(result_id, {})
            keyword_score = keyword_result.get("score", 0)
            
            # Calculate combined score
            combined_score = (
                vector_weight * vector_score +
                keyword_weight * keyword_score
            )
            
            # Use vector result as base (has payload)
            if vector_result:
                fused_result = vector_result.copy()
            else:
                fused_result = keyword_result.copy()
            
            fused_result["combined_score"] = combined_score
            fused_result["vector_score"] = vector_score
            fused_result["keyword_score"] = keyword_score
            
            fused_results.append(fused_result)
        
        return fused_results
    
    async def rerank_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        reranker_model: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Rerank search results using a cross-encoder"""
        # This is a placeholder for reranking implementation
        # In production, you'd use a proper reranking model
        # For now, return top results by score
        
        if len(results) <= top_k:
            return results
        
        # Sort by score and return top k
        sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
        return sorted_results[:top_k]
    
    async def filter_by_threshold(
        self,
        results: List[Dict[str, Any]],
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Filter results by relevance threshold"""
        return [
            result for result in results
            if result.get("score", 0) >= threshold
        ]
    
    async def retrieve_context(
        self,
        agent_id: str,
        query: str,
        embedding_model: str,
        limit: int = 10,
        use_hybrid: bool = True,
        rerank: bool = True,
        reranker_model: str = "bge-reranker",
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Main retrieval method for getting context"""
        try:
            # Perform search
            if use_hybrid:
                results = await self.hybrid_search(
                    agent_id=agent_id,
                    query=query,
                    embedding_model=embedding_model,
                    limit=limit * 2,  # Get more for reranking
                    score_threshold=score_threshold
                )
            else:
                results = await self.vector_search(
                    agent_id=agent_id,
                    query=query,
                    embedding_model=embedding_model,
                    limit=limit * 2,
                    score_threshold=score_threshold
                )
            
            # Rerank if requested
            if rerank and len(results) > 0:
                results = await self.rerank_results(
                    results=results,
                    query=query,
                    reranker_model=reranker_model,
                    top_k=limit
                )
            else:
                # Just limit without reranking
                results = results[:limit]
            
            # Apply final threshold filter
            if score_threshold is not None:
                results = await self.filter_by_threshold(results, score_threshold)
            
            return results
            
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return []


# Global retriever instance
retriever = Retriever()
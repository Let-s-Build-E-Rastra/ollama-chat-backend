import httpx
from typing import Optional
from loguru import logger


class LLMService:
    """LLM service using Ollama for response generation"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=120.0  # Long timeout for generation
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_model(self, model_name: str) -> bool:
        """Check if a model is available"""
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
        """Pull a model"""
        try:
            response = await self.client.post(
                "/api/pull",
                json={"name": model_name}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    async def generate_response(
        self,
        query: str,
        context: str,
        system_prompt: str,
        model_name: str,
        max_tokens: int = 1000,
        temperature: float = 0.1
    ) -> str:
        """Generate response using context and query"""
        try:
            # Ensure model is available
            if not await self.check_model(model_name):
                logger.info(f"Model {model_name} not found, attempting to pull...")
                if not await self.pull_model(model_name):
                    logger.error(f"Failed to pull model {model_name}")
                    return "Error: Model not available"
            
            # Build prompt
            prompt = self._build_prompt(query, context, system_prompt)
            
            # Generate response
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "stop": ["Human:", "User:", "###", "---"]
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "")
                
                # Clean up the response
                generated_text = self._clean_response(generated_text)
                
                return generated_text
            else:
                logger.error(f"Generation API error {response.status_code}: {response.text}")
                return "Error generating response"
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Error generating response"
    
    def _build_prompt(self, query: str, context: str, system_prompt: str) -> str:
        """Build prompt for generation"""
        # Use the system prompt as base
        if system_prompt:
            base_prompt = system_prompt
        else:
            base_prompt = "You are a helpful assistant. Answer questions based on the provided context."
        
        # Add context and query
        prompt = f"""{base_prompt}

Context:
---
{context}
---

Question: {query}

Answer based on the provided context. If the answer is not in the context, say "The information is not available in the provided knowledge base." Do not make up information.

Answer:"""
        
        return prompt
    
    def _clean_response(self, response: str) -> str:
        """Clean generated response"""
        # Remove common artifacts
        response = response.strip()
        
        # Remove if response starts with repetition of the question
        lines = response.split('\n')
        if len(lines) > 0 and "question" in lines[0].lower():
            lines = lines[1:]
        
        response = '\n'.join(lines).strip()
        
        # Remove trailing incomplete sentences
        sentences = response.split('. ')
        if len(sentences) > 1 and not sentences[-1].endswith('.'):
            response = '. '.join(sentences[:-1]) + '.'
        
        return response
    
    async def generate_stream(
        self,
        query: str,
        context: str,
        system_prompt: str,
        model_name: str,
        max_tokens: int = 1000,
        temperature: float = 0.1
    ):
        """Generate streaming response"""
        try:
            # Ensure model is available
            if not await self.check_model(model_name):
                yield "Error: Model not available"
                return
            
            # Build prompt
            prompt = self._build_prompt(query, context, system_prompt)
            
            # Generate streaming response
            async with self.client.stream(
                "POST",
                "/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "stop": ["Human:", "User:", "###", "---"]
                    }
                }
            ) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                import json
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                            except:
                                continue
                else:
                    yield f"Error: HTTP {response.status_code}"
                    
        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            yield f"Error: {str(e)}"
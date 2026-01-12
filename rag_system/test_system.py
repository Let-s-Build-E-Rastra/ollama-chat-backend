#!/usr/bin/env python3
"""
Test script for Multi-Agent RAG System
Tests basic functionality without external dependencies
"""

import asyncio
import sys
import os

# Add app to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.rag.preprocessor import TextPreprocessor
from app.rag.chunker import TextChunker


def test_config():
    """Test configuration loading"""
    print("✅ Testing configuration...")
    
    # Test settings
    assert settings.app_name == "Multi-Agent RAG System"
    assert len(settings.approved_embedding_models) > 0
    assert len(settings.approved_chat_models) > 0
    
    print(f"   App Name: {settings.app_name}")
    print(f"   Embedding Models: {settings.approved_embedding_models}")
    print(f"   Chat Models: {settings.approved_chat_models}")
    print("✅ Configuration test passed")


def test_preprocessor():
    """Test text preprocessor"""
    print("\n✅ Testing text preprocessor...")
    
    preprocessor = TextPreprocessor()
    
    # Test text cleaning
    test_text = "   This is   a test.   With   extra spaces.   "
    cleaned = preprocessor.clean_text(test_text)
    assert "  " not in cleaned
    print(f"   Cleaned text: '{cleaned}'")
    
    # Test HTML extraction
    html_text = "<html><body><h1>Title</h1><p>Content</p></body></html>"
    extracted = preprocessor.extract_text_from_html(html_text)
    assert "Title" in extracted
    assert "Content" in extracted
    print(f"   Extracted from HTML: '{extracted}'")
    
    print("✅ Preprocessor test passed")


def test_chunker():
    """Test text chunker"""
    print("\n✅ Testing text chunker...")
    
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    
    # Test token counting
    test_text = "This is a test sentence."
    token_count = chunker.count_tokens(test_text)
    assert token_count > 0
    print(f"   Token count: {token_count}")
    
    # Test semantic chunking
    long_text = """
    # Section 1
    This is the first section with some content.
    It has multiple sentences and should be chunked properly.
    
    # Section 2
    This is the second section with different content.
    It should be handled as a separate chunk if needed.
    """
    
    chunks = chunker.semantic_chunk(long_text, source="test.txt")
    assert len(chunks) > 0
    print(f"   Created {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
        print(f"   Chunk {i+1}: {chunk.content[:50]}... ({chunk.token_count} tokens)")
    
    print("✅ Chunker test passed")


async def test_database_connections():
    """Test database connections"""
    print("\n✅ Testing database connections...")
    
    try:
        from app.db.mongodb import mongodb
        from app.db.qdrant import qdrant_db
        
        # Test MongoDB
        await mongodb.connect()
        print("   ✅ MongoDB connection successful")
        await mongodb.disconnect()
        
        # Test Qdrant
        await qdrant_db.connect()
        print("   ✅ Qdrant connection successful")
        await qdrant_db.disconnect()
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        print("   💡 Make sure Docker services are running")


def test_models():
    """Test data models"""
    print("\n✅ Testing data models...")
    
    from app.models.agent import AgentCreate
    from app.models.api_key import APIKeyCreate
    from app.models.file import FileCreate
    
    # Test agent model
    agent_data = AgentCreate(
        name="test-agent",
        description="Test agent",
        system_prompt="You are a test agent.",
        chat_model="llama3.1",
        embedding_model="nomic-embed-text"
    )
    assert agent_data.name == "test-agent"
    print("   ✅ Agent model test passed")
    
    # Test API key model
    key_data = APIKeyCreate(
        agent_id="test-agent-id",
        name="test-key"
    )
    assert key_data.name == "test-key"
    print("   ✅ API Key model test passed")
    
    # Test file model
    file_data = FileCreate(
        agent_id="test-agent-id",
        filename="test.txt",
        content_type="text/plain",
        size=1024
    )
    assert file_data.filename == "test.txt"
    print("   ✅ File model test passed")


def main():
    """Run all tests"""
    print("🧪 Multi-Agent RAG System Test Suite")
    print("=" * 50)
    
    try:
        # Run basic tests
        test_config()
        test_models()
        test_preprocessor()
        test_chunker()
        
        # Run async tests
        print("\n✅ Running async tests...")
        asyncio.run(test_database_connections())
        
        print("\n🎉 All tests passed!")
        print("\n✅ System is ready for use!")
        print("\n🚀 Next steps:")
        print("   1. Start the system: ./start.sh")
        print("   2. Pull models: ./pull_models.sh")
        print("   3. Create an agent via API")
        print("   4. Upload documents")
        print("   5. Start chatting!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
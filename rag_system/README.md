# Multi-Agent RAG System

A production-grade, open-source, multi-agent Retrieval-Augmented Generation (RAG) system built with FastAPI, MongoDB, Qdrant, and Ollama.

## 🚀 Features

- **Multi-Agent Architecture**: Support for multiple independent agents with isolated knowledge bases
- **High-Precision Retrieval**: Hybrid search combining vector similarity and keyword matching
- **Advanced RAG Pipeline**: Semantic chunking, query expansion, reranking, and context assembly
- **Multilingual Support**: Support for 100+ languages with cross-lingual retrieval
- **Security**: API key authentication with bcrypt hashing and complete agent isolation
- **Open Source**: 100% open-source stack with no proprietary dependencies

## 🏗️ Architecture

```
Client
  ↓ (API Key)
FastAPI Gateway
  ↓
Agent Resolver
  ↓
Query Understanding & Expansion
  ↓
Semantic + Hybrid Retrieval
  ↓
Reranking
  ↓
Context Assembly
  ↓
LLM Generation (Ollama)
```

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Vector Database**: Qdrant
- **LLM Runtime**: Ollama
- **Embedding Models**: nomic-embed-text, bge-m3, e5-large, gte-large
- **Chat Models**: llama3.1, qwen2.5, mistral-nemo, phi-3.5
- **Authentication**: Bcrypt-hashed API keys

## 📋 Requirements

- Docker and Docker Compose
- NVIDIA GPU (optional, for better performance with Ollama)
- Python 3.11+ (for development)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd rag_system
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your configuration:

```bash
# MongoDB Configuration
MONGODB_URL=mongodb://admin:mongopass123@localhost:27017/rag_system?authSource=admin

# Qdrant Configuration
QDRANT_URL=http://localhost:6333

# Ollama Configuration
OLLAMA_URL=http://localhost:11434

# Security
SECRET_KEY=your-super-secret-key-here
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Pull Required Models

```bash
# Pull embedding model
docker exec -it rag_ollama ollama pull nomic-embed-text

# Pull chat model
docker exec -it rag_ollama ollama pull llama3.1

# Pull multilingual model (optional)
docker exec -it rag_ollama ollama pull bge-m3
```

### 5. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check available models
curl http://localhost:8000/api/v1/chat/models
```

## 📖 Usage

### 1. Create an Agent

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "support-bot",
    "description": "Customer support assistant",
    "system_prompt": "You are a helpful customer support assistant. Answer questions based on the provided documentation.",
    "chat_model": "llama3.1",
    "embedding_model": "nomic-embed-text",
    "max_chat_history": 10
  }'
```

### 2. Create API Key

```bash
curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production-key"
  }'
```

### 3. Upload Documents

```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@document.pdf" \
  -F "agent_id={agent_id}"
```

### 4. Chat with Agent

```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I configure SSL?",
    "use_hybrid_search": true,
    "use_reranking": true,
    "retrieval_limit": 10,
    "include_sources": true
  }'
```

## 📚 API Reference

### Agents

- `POST /api/v1/agents` - Create agent
- `GET /api/v1/agents` - List agents
- `GET /api/v1/agents/{id}` - Get agent
- `PUT /api/v1/agents/{id}` - Update agent
- `DELETE /api/v1/agents/{id}` - Delete agent
- `POST /api/v1/agents/{id}/api-keys` - Create API key
- `GET /api/v1/agents/{id}/api-keys` - List API keys

### Files

- `POST /api/v1/files/upload` - Upload file
- `GET /api/v1/files` - List files
- `GET /api/v1/files/{id}` - Get file
- `DELETE /api/v1/files/{id}` - Delete file
- `GET /api/v1/files/{id}/chunks` - Get chunk info

### Chat

- `POST /api/v1/chat/` - Send query
- `GET /api/v1/chat/context` - Retrieve context only
- `GET /api/v1/chat/models` - Get available models

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URL` | MongoDB connection string | Required |
| `QDRANT_URL` | Qdrant connection string | Required |
| `OLLAMA_URL` | Ollama connection string | Required |
| `SECRET_KEY` | Secret key for security | Required |
| `MAX_UPLOAD_SIZE` | Maximum file upload size | 52428800 (50MB) |
| `DEFAULT_CHUNK_SIZE` | Default chunk size | 512 |
| `DEFAULT_CHUNK_OVERLAP` | Default chunk overlap | 50 |
| `MIN_RELEVANCE_SCORE` | Minimum relevance score | 0.7 |

### Approved Models

**Embedding Models:**
- nomic-embed-text (default)
- bge-m3 (multilingual)
- e5-large
- gte-large

**Chat Models:**
- llama3.1 (recommended)
- qwen2.5 (multilingual)
- mistral-nemo
- phi-3.5

## 🔒 Security

- API key authentication with bcrypt hashing
- Complete agent isolation at retrieval layer
- Soft delete for audit trail
- Rate limiting per API key
- No cross-agent data access

## 🧪 Testing

```bash
# Install development dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

## 📊 Monitoring

- Health check endpoint: `GET /health`
- Application metrics exposed via Loguru
- Database connection monitoring
- Vector database status checks

## 🚀 Deployment

### Production Deployment

1. Use proper secret keys
2. Configure CORS appropriately
3. Set up SSL/TLS
4. Use persistent volumes for data
5. Configure resource limits
6. Set up monitoring and logging

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## 📁 Project Structure

```
rag_system/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Core configuration
│   ├── db/               # Database connections
│   ├── models/           # Data models
│   ├── rag/              # RAG pipeline components
│   ├── services/         # Business logic
│   └── main.py           # FastAPI app
├── docker/               # Docker configurations
├── tests/                # Test files
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Docker Compose setup
└── README.md            # Documentation
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- Check the documentation
- Review the requirements document
- Check logs with `docker-compose logs`
- Verify all services are running

## 🔍 RAG Pipeline Details

### Preprocessing
- Normalize whitespace
- Remove boilerplate
- Preserve structure
- Handle multiple formats

### Chunking
- Meaning-aware chunking
- Section-based splitting
- 200-400 tokens per chunk
- 20-40 token overlap

### Retrieval
- Vector similarity search
- Keyword matching
- Weighted fusion
- Relevance thresholding

### Reranking
- Cross-encoder models
- Top 10-20 candidates
- Relevance scoring
- Quality filtering

### Context Assembly
- Structured formatting
- Source attribution
- Deduplication
- Size enforcement
#!/bin/bash

# Multi-Agent RAG System Startup Script

set -e

echo "🚀 Starting Multi-Agent RAG System..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create necessary directories
mkdir -p logs uploads data

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration before continuing."
    exit 1
fi

# Pull required Docker images
echo "📥 Pulling Docker images..."
sudo docker compose pull

# Start MongoDB and Qdrant first
echo "🗄️  Starting databases..."
sudo docker compose up -d mongodb qdrant
# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 10

# Start Ollama
echo "🧠 Starting Ollama..."
sudo docker compose up -d ollama

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be ready..."
sleep 15

# Pull default models
echo "📚 Pulling default models..."
docker exec rag_ollama ollama pull nomic-embed-text || true
docker exec rag_ollama ollama pull llama3.1 || true

# Start the application
echo "🚀 Starting FastAPI application..."
sudo docker compose up -d app

# Wait for app to be ready
echo "⏳ Waiting for application to be ready..."
sleep 10

# Check if everything is running
echo "🔍 Checking service status..."
sudo docker compose ps

echo ""
echo "✅ Multi-Agent RAG System is starting up!"
echo ""
echo "📍 Services:"
echo "  - FastAPI: http://localhost:8000"
echo "  - MongoDB: localhost:27017"
echo "  - Qdrant: http://localhost:6333"
echo "  - Ollama: http://localhost:11434"
echo ""
echo "📖 Documentation: http://localhost:8000/docs"
echo "📝 To create your first agent, check the README.md"
echo ""
echo "🛑 To stop all services: docker-compose down"
echo "📊 To view logs: docker-compose logs -f app"
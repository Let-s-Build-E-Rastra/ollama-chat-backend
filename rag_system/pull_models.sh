#!/bin/bash

# Pull required models for RAG system

set -e

echo "📚 Pulling models for Multi-Agent RAG System..."

# Check if Ollama is running
if ! docker ps | grep -q rag_ollama; then
    echo "❌ Ollama container is not running. Please start the system first."
    echo "   Run: ./start.sh"
    exit 1
fi

# Default models to pull
DEFAULT_MODELS=(
    "nomic-embed-text"
    "llama3.1"
    "bge-m3"
)

# Additional models (optional)
OPTIONAL_MODELS=(
    "qwen2.5"
    "mistral-nemo"
    "phi-3.5"
    "e5-large"
    "gte-large"
)

# Function to pull model
pull_model() {
    local model=$1
    echo "📥 Pulling $model..."
    
    if docker exec rag_ollama ollama pull "$model"; then
        echo "✅ Successfully pulled $model"
        return 0
    else
        echo "❌ Failed to pull $model"
        return 1
    fi
}

# Pull default models
echo ""
echo "🎯 Pulling default models..."
for model in "${DEFAULT_MODELS[@]}"; do
    pull_model "$model"
done

# Ask about optional models
echo ""
read -p "🤔 Pull optional models as well? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Pulling optional models..."
    for model in "${OPTIONAL_MODELS[@]}"; do
        pull_model "$model"
    done
fi

echo ""
echo "🎉 Model pulling complete!"
echo ""
echo "📋 Available models:"
docker exec rag_ollama ollama list
#!/bin/bash

# Multi-Agent RAG System Shutdown Script

set -e

echo "🛑 Stopping Multi-Agent RAG System..."

# Stop all services
sudo docker compose down

echo "✅ All services stopped."
echo ""
echo "🗑️  To remove all data volumes, run: docker-compose down -v"
echo "🧹 To clean up Docker images, run: docker system prune"
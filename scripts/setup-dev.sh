#!/bin/bash
# Development environment setup script

set -e

echo "======================================"
echo "Listfig Email Processor - Dev Setup"
echo "======================================"
echo ""

# Check if running from project root
if [ ! -f "SKELETON-MVP.md" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Check if .env exists, if not copy from example
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your OpenAI API key!"
    echo "   Set OPENAI_API_KEY=your-key-here"
    echo ""
    read -p "Press Enter to continue after updating .env..."
else
    echo "✓ .env file already exists"
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo ""
    echo "⚠️  WARNING: OPENAI_API_KEY not found in .env"
    echo "   The AI processing will fail without a valid API key."
    echo ""
fi

echo ""
echo "Starting Docker containers..."
echo "This may take a few minutes on first run..."
echo ""

cd infrastructure/docker

# Pull images first
docker-compose pull

# Build and start services
docker-compose up -d --build

echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check service health
echo ""
echo "Checking service health..."
echo ""

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✓ PostgreSQL is ready"
else
    echo "✗ PostgreSQL is not ready"
fi

# Check Temporal
if docker-compose exec -T temporal tctl --address localhost:7233 workflow list > /dev/null 2>&1; then
    echo "✓ Temporal is ready"
else
    echo "⚠ Temporal is starting (this may take a minute)..."
fi

# Check FastAPI
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Email Processor API is ready"
else
    echo "⚠ Email Processor API is starting..."
fi

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Access URLs:"
echo "  - Email Processor API: http://localhost:8000"
echo "  - API Documentation:   http://localhost:8000/docs"
echo "  - Temporal UI:         http://localhost:8080"
echo "  - SMTP Server:         localhost:2525"
echo ""
echo "View logs:"
echo "  cd infrastructure/docker"
echo "  docker-compose logs -f"
echo ""
echo "Send test email:"
echo "  ./scripts/test-email.sh"
echo ""
echo "Stop services:"
echo "  cd infrastructure/docker"
echo "  docker-compose down"
echo ""

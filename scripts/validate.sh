#!/bin/bash

# Validation script for Behavioral Health Session Summarization Agent

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Validating Setup..."

failed_services=0

# Check if docker-compose file exists
if [ ! -f docker-compose.yml ]; then
    echo -e "${RED}❌ docker-compose.yml not found${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

echo "📋 Checking Docker services..."

# Check Docker services
services=("app" "postgres" "redis")

for service in "${services[@]}"; do
    if docker-compose ps "$service" | grep -q "Up"; then
        echo -e "${GREEN}✅ $service container is running${NC}"
    else
        echo -e "${RED}❌ $service container is not running${NC}"
        ((failed_services++))
    fi
done

echo ""
echo "🌐 Checking web services..."

# Test web endpoints
if curl -s -f "http://localhost:8001" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Application is running on port 8001${NC}"
else
    echo -e "${RED}❌ Application is not accessible on port 8001${NC}"
    ((failed_services++))
fi

if curl -s -f "http://localhost:8001/api/docs" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API documentation is accessible${NC}"
else
    echo -e "${RED}❌ API documentation is not accessible${NC}"
    ((failed_services++))
fi

echo ""
echo "🔗 Testing API endpoints..."

# Test Application API
if curl -s -f "http://localhost:8001/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Application API is responding${NC}"
else
    echo -e "${RED}❌ Application API is not responding${NC}"
    ((failed_services++))
fi

echo ""
echo "🗄️  Testing database connection..."

# Test database connection
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL database is ready${NC}"
else
    echo -e "${RED}❌ PostgreSQL database is not ready${NC}"
    ((failed_services++))
fi

echo ""
echo "🤖 Testing Ollama (Optional)..."

# Check if Ollama is installed and running locally
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama is not installed (optional for enhanced analysis)${NC}"
    echo "💡 Install from: https://ollama.com/download"
else
    echo -e "${GREEN}✅ Ollama is installed${NC}"
    
    # Check if Ollama service is running
    if curl -s -f "http://localhost:11434/api/tags" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Ollama service is running${NC}"
        
        # Check if model is available
        if ollama list | grep -q "qwen2.5:3b-instruct-q4_0"; then
            echo -e "${GREEN}✅ Ollama model (qwen2.5:3b-instruct-q4_0) is available${NC}"
        else
            echo -e "${YELLOW}⚠️  Ollama model (qwen2.5:3b-instruct-q4_0) is not available${NC}"
            echo "💡 Download with: ollama pull qwen2.5:3b-instruct-q4_0"
        fi
    else
        echo -e "${YELLOW}⚠️  Ollama service is not running (optional)${NC}"
        echo "💡 Start Ollama with: ollama serve"
    fi
fi

echo ""
echo "🧪 Testing analysis functionality..."

# Test analysis endpoint
if curl -s -X POST "http://localhost:8001/api/summarize" -F "transcript=Test patient session for validation" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Analysis endpoint is working${NC}"
else
    echo -e "${RED}❌ Analysis endpoint is not working${NC}"
    ((failed_services++))
fi

echo ""
echo "📊 Summary:"

if [ $failed_services -eq 0 ]; then
    echo -e "${GREEN}🎉 All core systems are operational!${NC}"
    echo ""
    echo "🌐 Access your services:"
    echo "  - Application: http://localhost:8001"
    echo "  - API Documentation: http://localhost:8001/api/docs"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - Ollama API: http://localhost:11434 (if installed)"
    echo ""
    echo "📋 Next steps:"
    echo "1. Open http://localhost:8001 in your browser"
    echo "2. Upload an audio file or enter text transcript"
    echo "3. Click 'Analyze' to test the functionality"
    echo ""
    echo "Setup validation completed successfully!"
else
    echo -e "${RED}❌ Some core services are not working properly${NC}"
    echo ""
    echo "🔧 Troubleshooting steps:"
    echo "1. Check logs: docker-compose logs"
    echo "2. Restart services: docker-compose restart"
    echo "3. Check README.md for detailed help"
    exit 1
fi
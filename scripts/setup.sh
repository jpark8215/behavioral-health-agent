#!/bin/bash

# Setup script for Behavioral Health Session Summarization Agent

set -e

echo "🚀 Setting up Behavioral Health Session Summarization Agent..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    
    # Generate password
    POSTGRES_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    
    cat > .env << EOF
# Behavioral Health App Configuration

############
# Database Configuration
############
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

############
# Redis Configuration
############
REDIS_HOST=redis
REDIS_PORT=6379

############
# Ollama Configuration (Optional)
############
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:3b-instruct-q4_0

############
# Application Configuration
############
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,http://localhost:8001

# Application Server
HOST=0.0.0.0
PORT=8001

# Whisper Configuration
WHISPER_MODEL_SIZE=base
EOF

    echo "✅ .env file created"
    echo "⚠️  IMPORTANT: Please update the POSTGRES_PASSWORD in .env file for production use!"
    echo ""
else
    echo "📝 .env file already exists"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p temp/audio
mkdir -p static/uploads

# Start the services
echo "🏗️  Starting application services..."
docker-compose up -d

echo "⏳ Waiting for services to start..."
sleep 30

# Check if services are running
echo "🔍 Checking service status..."
docker-compose ps

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
timeout=60
while [ $timeout -gt 0 ]; do
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ Database is ready"
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo "❌ Database failed to start within 60 seconds"
    exit 1
fi

# Setup Ollama locally (Optional)
echo "🤖 Setting up Ollama (Optional - for enhanced analysis)..."

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "📥 Ollama not found. This is optional - the app works without it."
    echo "💡 For enhanced analysis, you can install Ollama:"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  Linux: curl -fsSL https://ollama.com/install.sh | sh"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  macOS: brew install ollama"
    fi
    
    echo "  Then run: ollama serve"
    echo "  Then run: ollama pull qwen2.5:3b-instruct-q4_0"
    echo ""
    echo "✅ Continuing without Ollama - using built-in analysis"
else
    echo "✅ Ollama is already installed"
    
    # Start Ollama service in background
    echo "🚀 Starting Ollama service..."
    ollama serve &
    OLLAMA_PID=$!
    
    # Wait for Ollama to start
    echo "⏳ Waiting for Ollama to start..."
    sleep 5
    
    # Pull the model
    echo "📥 Pulling qwen2.5:3b-instruct-q4_0 (this may take a while)..."
    ollama pull qwen2.5:3b-instruct-q4_0
    
    echo "✅ Ollama setup complete!"
    echo "💡 Ollama is running in the background (PID: $OLLAMA_PID)"
fi

echo "✅ Setup complete!"
echo ""
echo "🌐 Services are running at:"
echo "  - Application: http://localhost:8001"
echo "  - API Documentation: http://localhost:8001/api/docs"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - Ollama API: http://localhost:11434 (if installed)"
echo ""
echo "📋 Next steps:"
echo "1. Open the application at http://localhost:8001"
echo "2. Upload an audio file or enter text transcript"
echo "3. Click 'Analyze' to generate clinical summary"
echo "4. View comprehensive results with treatment recommendations"
echo ""
echo "🔧 Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart: docker-compose restart"
echo "  - Health check: curl http://localhost:8001/api/health"
@echo off
REM Setup script for Behavioral Health Session Summarization Agent (Windows)

echo 🚀 Setting up Behavioral Health Session Summarization Agent...

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file...
    
    REM Generate random password
    set POSTGRES_PASSWORD=postgrespass1211
    
    (
    echo # Behavioral Health App Configuration
    echo.
    echo ############
    echo # Database Configuration
    echo ############
    echo POSTGRES_PASSWORD=%POSTGRES_PASSWORD%
    echo POSTGRES_DB=postgres
    echo POSTGRES_HOST=postgres
    echo POSTGRES_PORT=5432
    echo.
    echo ############
    echo # Redis Configuration
    echo ############
    echo REDIS_HOST=redis
    echo REDIS_PORT=6379
    echo.
    echo ############
    echo # Ollama Configuration ^(Optional^)
    echo ############
    echo OLLAMA_BASE_URL=http://host.docker.internal:11434
    echo OLLAMA_MODEL=qwen2.5:3b-instruct-q4_0
    echo.
    echo ############
    echo # Application Configuration
    echo ############
    echo ENVIRONMENT=development
    echo ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,http://localhost:8001
    echo.
    echo # Application Server
    echo HOST=0.0.0.0
    echo PORT=8001
    echo.
    echo # Whisper Configuration
    echo WHISPER_MODEL_SIZE=base
    ) > .env
    
    echo ✅ .env file created
    echo ⚠️  IMPORTANT: Please update the POSTGRES_PASSWORD in .env file for production use!
    echo.
) else (
    echo 📝 .env file already exists
)

REM Create necessary directories
echo 📁 Creating necessary directories...
if not exist temp\audio mkdir temp\audio
if not exist static\uploads mkdir static\uploads

REM Start the services
echo 🏗️  Starting application services...
docker-compose up -d

echo ⏳ Waiting for services to start...
timeout /t 30 /nobreak >nul

REM Check if services are running
echo 🔍 Checking service status...
docker-compose ps

REM Wait for database to be ready
echo ⏳ Waiting for database to be ready...
timeout /t 20 /nobreak >nul

REM Setup Ollama locally (Optional)
echo 🤖 Setting up Ollama ^(Optional - for enhanced analysis^)...

REM Check if Ollama is installed
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Ollama not found. This is optional - the app works without it.
    echo 💡 For enhanced analysis, you can install Ollama:
    echo 1. Download from: https://ollama.com/download
    echo 2. Install the Windows version
    echo 3. Run: ollama serve
    echo 4. Run: ollama pull qwen2.5:3b-instruct-q4_0
    echo.
    echo ✅ Continuing without Ollama - using built-in analysis
) else (
    echo ✅ Ollama is already installed
    
    REM Start Ollama service
    echo 🚀 Starting Ollama service...
    start /B ollama serve
    
    REM Wait for Ollama to start
    echo ⏳ Waiting for Ollama to start...
    timeout /t 5 /nobreak >nul
    
    REM Pull the model
    echo 📥 Pulling qwen2.5:3b-instruct-q4_0 model ^(this may take a while^)...
    ollama pull qwen2.5:3b-instruct-q4_0
    
    echo ✅ Ollama setup complete!
    echo 💡 Ollama is running in the background
)

echo ✅ Setup complete!
echo.
echo 🌐 Services are running at:
echo   - Application: http://localhost:8001
echo   - API Documentation: http://localhost:8001/api/docs
echo   - PostgreSQL: localhost:5432
echo   - Redis: localhost:6379
echo   - Ollama API: http://localhost:11434 ^(if installed^)
echo.
echo 📋 Next steps:
echo 1. Open the application at http://localhost:8001
echo 2. Upload an audio file or enter text transcript
echo 3. Click "Analyze" to generate clinical summary
echo 4. View comprehensive results with treatment recommendations
echo.
echo 🔧 Useful commands:
echo   - View logs: docker-compose logs -f
echo   - Stop services: docker-compose down
echo   - Restart: docker-compose restart
echo   - Health check: curl http://localhost:8001/api/health
pause
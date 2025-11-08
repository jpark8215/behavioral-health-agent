@echo off
REM Validation script for Behavioral Health Session Summarization Agent (Windows)

echo 🔍 Validating Setup...

REM Check if docker-compose file exists
if not exist docker-compose.yml (
    echo ❌ docker-compose.yml not found
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo ❌ .env file not found
    exit /b 1
)

echo 📋 Checking Docker services...

REM Check Docker services
set services=app postgres redis
set failed_services=0

for %%s in (%services%) do (
    docker-compose ps %%s | findstr "Up" >nul
    if errorlevel 1 (
        echo ❌ %%s container is not running
        set /a failed_services+=1
    ) else (
        echo ✅ %%s container is running
    )
)

echo.
echo 🌐 Checking web services...

REM Test web endpoints
curl -s -f http://localhost:8001 >nul 2>&1
if errorlevel 1 (
    echo ❌ Application is not accessible on port 8001
    set /a failed_services+=1
) else (
    echo ✅ Application is running on port 8001
)

curl -s -f http://localhost:8001/api/docs >nul 2>&1
if errorlevel 1 (
    echo ❌ API documentation is not accessible
    set /a failed_services+=1
) else (
    echo ✅ API documentation is accessible
)

echo.
echo 🔗 Testing API endpoints...

REM Test Application API
curl -s -f http://localhost:8001/api/health >nul 2>&1
if errorlevel 1 (
    echo ❌ Application API is not responding
    set /a failed_services+=1
) else (
    echo ✅ Application API is responding
)

echo.
echo 🗄️  Testing database connection...

REM Test database connection
docker-compose exec -T postgres pg_isready -U postgres >nul 2>&1
if errorlevel 1 (
    echo ❌ PostgreSQL database is not ready
    set /a failed_services+=1
) else (
    echo ✅ PostgreSQL database is ready
)

echo.
echo 🤖 Testing Ollama ^(Optional^)...

REM Check if Ollama is installed and running locally
ollama --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Ollama is not installed ^(optional for enhanced analysis^)
    echo 💡 Install from: https://ollama.com/download
) else (
    echo ✅ Ollama is installed
    
    REM Check if Ollama service is running
    curl -s -f http://localhost:11434/api/tags >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  Ollama service is not running ^(optional^)
        echo 💡 Start Ollama with: ollama serve
    ) else (
        echo ✅ Ollama service is running
        
        REM Check if model is available
        ollama list | findstr "qwen2.5:3b-instruct-q4_0" >nul
        if errorlevel 1 (
            echo ⚠️  Ollama model ^(qwen2.5:3b-instruct-q4_0^) is not available
            echo 💡 Download with: ollama pull qwen2.5:3b-instruct-q4_0
        ) else (
            echo ✅ Ollama model ^(qwen2.5:3b-instruct-q4_0^) is available
        )
    )
)

echo.
echo 🧪 Testing analysis functionality...

REM Test analysis endpoint
curl -s -X POST "http://localhost:8001/api/summarize" -F "transcript=Test patient session for validation" >nul 2>&1
if errorlevel 1 (
    echo ❌ Analysis endpoint is not working
    set /a failed_services+=1
) else (
    echo ✅ Analysis endpoint is working
)

echo.
echo 📊 Summary:

if %failed_services% equ 0 (
    echo 🎉 All core systems are operational!
    echo.
    echo 🌐 Access your services:
    echo   - Application: http://localhost:8001
    echo   - API Documentation: http://localhost:8001/api/docs
    echo   - PostgreSQL: localhost:5432
    echo   - Redis: localhost:6379
    echo   - Ollama API: http://localhost:11434 ^(if installed^)
    echo.
    echo 📋 Next steps:
    echo 1. Open http://localhost:8001 in your browser
    echo 2. Upload an audio file or enter text transcript
    echo 3. Click "Analyze" to test the functionality
    echo.
    echo Setup validation completed successfully!
) else (
    echo ❌ Some core services are not working properly
    echo.
    echo 🔧 Troubleshooting steps:
    echo 1. Check logs: docker-compose logs
    echo 2. Restart services: docker-compose restart
    echo 3. Check README.md for detailed help
    exit /b 1
)

pause
# Local Deployment Guide

Complete guide for deploying the Behavioral Health Session Summarization Agent on your local machine.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Starting the Application](#starting-the-application)
5. [Verification](#verification)
6. [Optional: Ollama Setup](#optional-ollama-setup)
7. [Usage Examples](#usage-examples)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)
10. [Advanced Configuration](#advanced-configuration)

## Prerequisites

### Required Software

1. **Docker Desktop** (or Docker Engine + Docker Compose)
   - Windows: Download from https://www.docker.com/products/docker-desktop
   - macOS: Download from https://www.docker.com/products/docker-desktop
   - Linux: Install Docker Engine and Docker Compose separately

2. **System Requirements**
   - **Minimum**: 4GB RAM, 10GB free disk space
   - **Recommended**: 8GB+ RAM, 20GB+ free disk space
   - **CPU**: Multi-core processor recommended
   - **OS**: Windows 10+, macOS 10.15+, or modern Linux

### Optional Software

3. **Ollama** (for AI-powered analysis)
   - Only needed if you want enhanced LLM-based analysis
   - System works fine without it using rule-based analysis
   - Requires additional 2-4GB RAM

### Port Requirements

Ensure these ports are available:
- **8001**: Application web interface and API
- **5432**: PostgreSQL database
- **6379**: Redis cache

## Installation Steps

### Step 1: Get the Code

```bash
# Clone the repository
git clone https://github.com/jpark8215/behavioral-health-agent
cd behavioral-health-agent

# Verify files are present
ls -la
```

You should see:
- `docker-compose.yml`
- `Dockerfile`
- `.env.example`
- `main.py`
- `requirements.txt`

### Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env
```

**Edit `.env` file** (optional - defaults work for most setups):

```bash
# Database Configuration
POSTGRES_PASSWORD=changeme123  # Change this for production!
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Application Configuration
PORT=8001
ENVIRONMENT=development
WHISPER_MODEL_SIZE=base  # Options: tiny, base, small, medium, large

# Ollama Configuration (optional)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:3b-instruct-q4_0
```

**Important**: Change `POSTGRES_PASSWORD` for production deployments!

### Step 3: Build and Start

```bash
# Build and start all services
docker-compose up -d --build

# This will:
# 1. Build the application container
# 2. Download PostgreSQL and Redis images
# 3. Create network and volumes
# 4. Start all services
```

**Expected output**:
```
[+] Building 45.2s (15/15) FINISHED
[+] Running 4/4
 ✔ Network behavioral-health-agent_app-network   Created
 ✔ Container behavioral-health-agent-postgres-1  Started
 ✔ Container behavioral-health-agent-redis-1     Started
 ✔ Container behavioral-health-agent-app-1       Started
```

### Step 4: Wait for Startup

```bash
# Check container status
docker-compose ps

# All containers should show "Up" and "healthy"
```

Wait 10-15 seconds for the application to fully start.

## Configuration

### Database Configuration

The application uses PostgreSQL for persistent storage.

**Default settings** (in `.env`):
```bash
POSTGRES_PASSWORD=changeme123  # CHANGE THIS!
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
```

**For production**:
1. Use a strong, unique password
2. Consider using Docker secrets
3. Enable SSL connections
4. Regular backups (see [Maintenance](#maintenance))

### Redis Configuration

Redis is used for caching transcriptions and analyses.

**Default settings**:
```bash
REDIS_HOST=redis
REDIS_PORT=6379
```

**Cache behavior**:
- Transcriptions cached for 1 hour
- Analyses cached until reanalysis requested
- Automatic cache eviction when full

### Whisper Model Configuration

Choose model size based on your needs:

| Model | Size | Speed | Accuracy | RAM |
|-------|------|-------|----------|-----|
| tiny | 39MB | Fastest | Good | 1GB |
| base | 74MB | Fast | Better | 1GB |
| small | 244MB | Medium | Good | 2GB |
| medium | 769MB | Slow | Very Good | 5GB |
| large | 1550MB | Slowest | Best | 10GB |

**Set in `.env`**:
```bash
WHISPER_MODEL_SIZE=base  # Recommended for most users
```

**Note**: Model downloads on first use. Larger models take longer to download and process.

## Starting the Application

### Normal Startup

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app
```

### Stop Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (deletes all data!)
docker-compose down -v
```

### Restart Application

```bash
# Restart all services
docker-compose restart

# Restart only app
docker-compose restart app
```

## Verification

### Step 1: Check Container Health

```bash
docker-compose ps
```

**Expected output**:
```
NAME                                 STATUS
behavioral-health-agent-app-1        Up (healthy)
behavioral-health-agent-postgres-1   Up (healthy)
behavioral-health-agent-redis-1      Up (healthy)
```

All containers should show "Up" and "(healthy)".

### Step 2: Check Application Logs

```bash
docker-compose logs app --tail 20
```

**Look for**:
- "Application startup completed successfully"
- "PostgreSQL connection pool created"
- "Uvicorn running on http://0.0.0.0:8000"
- No error messages

### Step 3: Test Health Endpoint

```bash
curl http://localhost:8001/api/health
```

**Expected response**:
```json
{
  "status": "healthy",
  "database_status": "connected",
  "timestamp": "2024-11-07T...",
  "version": "1.0.0"
}
```

### Step 4: Access Web Interface

Open your browser and navigate to:
```
http://localhost:8001
```

You should see the application homepage with options to upload audio or enter text.

### Step 5: Test Basic Functionality

**Test text analysis**:
1. Go to http://localhost:8001
2. Enter sample text: "Patient reports feeling anxious about work deadlines and having trouble sleeping."
3. Click "Analyze"
4. Verify you receive:
   - Clinical summary
   - Diagnostic impression
   - Key points
   - Treatment plan

**Test audio upload** (if you have an audio file):
1. Click "Upload Audio"
2. Select a WAV, MP3, or M4A file
3. Click "Analyze"
4. Wait for transcription (10-15 seconds first time)
5. Verify transcription and analysis appear

## Optional: Ollama Setup

Ollama provides enhanced AI-powered analysis. The application works fine without it using rule-based analysis.

### When to Use Ollama

**Use Ollama if**:
- You want more detailed, context-aware analysis
- You have 8GB+ RAM available
- You're okay with slower analysis (5-10 seconds)

**Skip Ollama if**:
- You have limited RAM (< 8GB)
- You need fast analysis (rule-based is instant)
- You're just testing the application

### Installing Ollama

#### Windows
```bash
# Download installer from https://ollama.ai
# Or use winget
winget install Ollama.Ollama
```

#### macOS
```bash
brew install ollama
```

#### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Starting Ollama

```bash
# Start Ollama service
ollama serve

# In another terminal, pull a model
ollama pull qwen2.5:3b-instruct-q4_0
```

**Model recommendations**:

| Model | RAM | Speed | Quality |
|-------|-----|-------|---------|
| qwen2.5:1.5b | 2GB | Fast | Good |
| qwen2.5:3b-instruct-q4_0 | 4GB | Medium | Better |
| granite3.3:8b | 8GB | Slow | Best |

### Configuring Application for Ollama

**Update `.env`**:
```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:3b-instruct-q4_0
```

**Restart application**:
```bash
docker-compose restart app
```

**Verify Ollama connection**:
```bash
curl http://localhost:8001/api/health
```

Look for `"ollama_service": {"status": "healthy"}` in response.

### Troubleshooting Ollama

**"Model requires more system memory"**:
- Use smaller model: `ollama pull qwen2.5:1.5b`
- Close other applications
- Increase Docker memory limit
- Application will automatically use rule-based fallback

**"Cannot connect to Ollama"**:
- Verify Ollama is running: `ollama list`
- Check OLLAMA_BASE_URL in `.env`
- On Windows/Mac, use `host.docker.internal`
- On Linux, use `172.17.0.1` or host IP

## Usage Examples

### Example 1: Analyze Text Transcript

**Via Web Interface**:
1. Go to http://localhost:8001
2. Paste transcript text
3. Click "Analyze"

**Via API**:
```bash
curl -X POST "http://localhost:8001/api/summarize" \
  -F "transcript=Patient discussed anxiety symptoms and coping strategies. Reported improved sleep after implementing relaxation techniques."
```

### Example 2: Upload Audio File

**Via Web Interface**:
1. Go to http://localhost:8001
2. Click "Upload Audio"
3. Select audio file
4. Click "Analyze"
5. Wait for transcription and analysis

**Via API**:
```bash
curl -X POST "http://localhost:8001/api/upload-audio" \
  -F "audio_file=@/path/to/session.wav"
```

### Example 3: View Past Sessions

**Via Web Interface**:
1. Click "Sessions" in navigation
2. Browse session list
3. Click session to view details

**Via API**:
```bash
# List sessions
curl "http://localhost:8001/api/sessions?limit=10"

# Get specific session
curl "http://localhost:8001/api/sessions/{session_id}"
```

### Example 4: Reanalyze Session

**When to reanalyze**:
- Ollama was unavailable during initial analysis
- You want fresh analysis with updated prompts
- You want to try different analysis mode (LLM vs rule-based)

**Via Web Interface**:
1. Open session
2. Click "Reanalyze"
3. Choose analysis type
4. View updated results

**Via API**:
```bash
# Reanalyze with LLM
curl -X POST "http://localhost:8001/api/sessions/{session_id}/reanalyze" \
  -F "use_external_llm=true"

# Reanalyze with rule-based
curl -X POST "http://localhost:8001/api/sessions/{session_id}/reanalyze" \
  -F "use_external_llm=false"
```

## Troubleshooting

### Application Won't Start

**Check Docker is running**:
```bash
docker --version
docker-compose --version
```

**Check container status**:
```bash
docker-compose ps
```

**View logs**:
```bash
docker-compose logs app
docker-compose logs postgres
docker-compose logs redis
```

**Common issues**:
- Port 8001 already in use: Change PORT in `.env`
- Docker not running: Start Docker Desktop
- Permission denied: Run with sudo (Linux) or check Docker Desktop settings

### Database Connection Errors

**Symptoms**: "Database connection failed" in logs

**Solutions**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Verify connection
docker-compose exec postgres psql -U postgres -c "SELECT 1;"
```

### Audio Upload Fails

**Symptoms**: Upload returns error or times out

**Check file format**:
- Supported: WAV, MP3, M4A, FLAC, OGG, WebM
- Max size: 50MB recommended
- Sample rate: Any (will be resampled)

**Check logs**:
```bash
docker-compose logs app --tail 50
```

**Common issues**:
- Unsupported format: Convert to WAV or MP3
- File too large: Split into smaller segments
- Whisper model not loaded: Wait for first-time download

### Transcription Takes Too Long

**First transcription**:
- Whisper model downloads (~140MB for base model)
- Takes 10-15 seconds
- Subsequent transcriptions much faster

**Every transcription slow**:
- Use smaller model: `WHISPER_MODEL_SIZE=tiny`
- Check system resources: `docker stats`
- Increase Docker memory limit

### Analysis Returns Generic Results

**Symptoms**: All analyses seem similar

**Cause**: Using rule-based fallback (Ollama unavailable)

**This is normal if**:
- Ollama not installed
- Ollama out of memory
- Ollama not configured

**Solutions**:
1. Install and configure Ollama (see [Optional: Ollama Setup](#optional-ollama-setup))
2. Use smaller Ollama model
3. Reanalyze sessions when Ollama available
4. Accept rule-based analysis (still clinically relevant)

### Transcripts Not Saved

**Verify database**:
```bash
# Check sessions table
docker-compose exec postgres psql -U postgres -d postgres \
  -c "SELECT id, LENGTH(transcript), created_at FROM sessions ORDER BY created_at DESC LIMIT 5;"
```

**Check logs**:
```bash
docker-compose logs app | grep "Session created"
```

**If transcripts missing**:
- Check application logs for errors
- Verify database connection
- Restart application

### Performance Issues

**Slow web interface**:
- Check Docker resource limits
- Increase Docker memory/CPU
- Close other applications

**Slow analysis**:
- Ollama analysis: 5-10 seconds (normal)
- Rule-based analysis: <1 second
- Use caching (automatic)

**High memory usage**:
- Use smaller Whisper model
- Use smaller Ollama model
- Restart containers: `docker-compose restart`

## Maintenance

### Viewing Logs

```bash
# View all logs
docker-compose logs

# View specific service
docker-compose logs app
docker-compose logs postgres

# Follow logs in real-time
docker-compose logs -f app

# View last N lines
docker-compose logs --tail 50 app
```

### Database Backup

**Create backup**:
```bash
# Backup to file
docker-compose exec postgres pg_dump -U postgres postgres > backup_$(date +%Y%m%d).sql

# Verify backup
ls -lh backup_*.sql
```

**Restore backup**:
```bash
# Stop application
docker-compose stop app

# Restore database
docker-compose exec -T postgres psql -U postgres postgres < backup_20241107.sql

# Restart application
docker-compose start app
```

### Updating Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Verify
docker-compose ps
curl http://localhost:8001/api/health
```

### Cleaning Up

**Remove old containers**:
```bash
docker-compose down
```

**Remove volumes (deletes all data!)**:
```bash
docker-compose down -v
```

**Remove images**:
```bash
docker-compose down --rmi all
```

**Clean Docker system**:
```bash
docker system prune -a
```

## Advanced Configuration

### Production Deployment

**Security checklist**:
1. Change POSTGRES_PASSWORD to strong password
2. Set ENVIRONMENT=production in `.env`
3. Enable SSL for database connections
4. Use reverse proxy (nginx) for HTTPS
5. Implement rate limiting
6. Regular backups
7. Monitor logs and metrics

**Performance tuning**:
```yaml
# In docker-compose.yml, add resource limits
services:
  app:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
  
  postgres:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Custom Whisper Model

```bash
# In .env
WHISPER_MODEL_SIZE=medium  # For better accuracy

# Or use tiny for faster processing
WHISPER_MODEL_SIZE=tiny
```

### Custom Ollama Model

```bash
# Pull different model
ollama pull llama2:7b

# Update .env
OLLAMA_MODEL=llama2:7b

# Restart
docker-compose restart app
```

### Network Configuration

**Custom ports**:
```bash
# In .env
PORT=9000  # Change application port

# In docker-compose.yml
ports:
  - "9000:8000"  # Map to custom port
```

**External database**:
```bash
# In .env
POSTGRES_HOST=external-db.example.com
POSTGRES_PORT=5432
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
```

### Monitoring

**Check resource usage**:
```bash
docker stats
```

**Monitor logs**:
```bash
# Install log monitoring
docker-compose logs -f | grep ERROR
```

**Health checks**:
```bash
# Automated health check
watch -n 30 'curl -s http://localhost:8001/api/health | jq'
```

## Next Steps

1. **Test the application** with sample data
2. **Configure Ollama** if desired for enhanced analysis
3. **Set up backups** for production use
4. **Review security settings** before production deployment
5. **Read API documentation** at http://localhost:8001/api/docs

## Additional Resources

- **README.md**: Project overview and features
- **API Documentation**: http://localhost:8001/api/docs
- **docs/API_IMPROVEMENTS.md**: Complete API reference
- **docs/QUICK_REFERENCE.md**: Quick command reference
- **CHANGELOG.md**: Version history

## Support

If you encounter issues:
1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Review application logs: `docker-compose logs app`
3. Check health endpoint: `curl http://localhost:8001/api/health`
4. Verify all containers running: `docker-compose ps`

---

**Last Updated**: November 2024  
**Version**: 1.0.0

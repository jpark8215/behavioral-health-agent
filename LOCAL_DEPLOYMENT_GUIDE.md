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
11. [Next Steps](#next-steps)
12. [Additional Resources](#additional-resources)
13. [Support](#support)

## Prerequisites

### Required Software

1. **Docker Desktop** (or Docker Engine + Docker Compose)  
   - Windows: https://www.docker.com/products/docker-desktop  
   - macOS: https://www.docker.com/products/docker-desktop  
   - Linux: Install Docker Engine and Docker Compose separately  

2. **System Requirements**
   - Minimum: 4GB RAM, 10GB free disk space  
   - Recommended: 8GB+ RAM, 20GB+ free disk space  
   - CPU: Multi-core processor  
   - OS: Windows 10+, macOS 10.15+, or modern Linux  

### Optional Software

3. **Ollama** (for AI-powered analysis)  
   - Enhances LLM-based analysis; rule-based analysis works without it  
   - Requires additional 2-4GB RAM  

### Port Requirements

- 8001: Application web interface and API  
- 5432: PostgreSQL database  
- 6379: Redis cache  

## Installation Steps

### Step 1: Get the Code

```bash
git clone https://github.com/jpark8215/behavioral-health-agent
cd behavioral-health-agent
ls -la
````

You should see: `docker-compose.yml`, `Dockerfile`, `.env.example`, `main.py`, `requirements.txt`

### Step 2: Configure Environment

```bash
cp .env.example .env
```

**Edit `.env` as needed**:

```bash
POSTGRES_PASSWORD=changeme123  # Change for production!
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres

REDIS_HOST=redis
REDIS_PORT=6379

PORT=8001
ENVIRONMENT=development
WHISPER_MODEL_SIZE=base  # Options: tiny, base, small, medium, large

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
```

### Step 3: Build and Start

```bash
docker-compose up -d --build
docker-compose ps
```

* Ensure all containers show `Up` and `healthy`
* Wait 10-15 seconds for full startup

## Configuration

### Whisper Model

| Model  | Size   | Speed   | Accuracy  | RAM  |
| ------ | ------ | ------- | --------- | ---- |
| tiny   | 39MB   | Fastest | Good      | 1GB  |
| base   | 74MB   | Fast    | Better    | 1GB  |
| small  | 244MB  | Medium  | Good      | 2GB  |
| medium | 769MB  | Slow    | Very Good | 5GB  |
| large  | 1550MB | Slowest | Best      | 10GB |

Set in `.env`:

```bash
WHISPER_MODEL_SIZE=base
```

### Redis Cache

* Caches transcriptions for 1 hour
* Analyses cached until reanalysis requested
* Automatic cache eviction when full

## Starting the Application

```bash
docker-compose up -d
docker-compose logs -f app
```

Stop application:

```bash
docker-compose down
```

Restart:

```bash
docker-compose restart app
```

## Verification

1. **Check container health**

```bash
docker-compose ps
```

2. **Check application logs**

```bash
docker-compose logs app --tail 20
```

3. **Test health endpoint**

```bash
curl http://localhost:8001/api/health
```

4. **Access Web Interface**

```
http://localhost:8001
```

5. **Test basic functionality** via text or audio upload

## Optional: Ollama Setup

* Enhances AI-powered analysis
* Works without it using rule-based fallback

**Install & start Ollama**:

Windows:

```bash
winget install Ollama.Ollama
```

macOS:

```bash
brew install ollama
```

Linux:

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

```bash
ollama serve
ollama pull mistral:7b
```

Update `.env`:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
docker-compose restart app
```

## Usage Examples

**Text transcript via API**

```bash
curl -X POST "http://localhost:8001/api/summarize" \
  -F "transcript=Patient discussed anxiety symptoms and coping strategies."
```

**Audio upload via API**

```bash
curl -X POST "http://localhost:8001/api/upload-audio" \
  -F "audio_file=@/path/to/session.wav"
```

**View sessions**

```bash
curl "http://localhost:8001/api/sessions?limit=10"
```

**Reanalyze session**

```bash
curl -X POST "http://localhost:8001/api/sessions/{session_id}/reanalyze" \
  -F "use_external_llm=true"
```

## Troubleshooting

* **App won’t start**: Check Docker, ports, logs (`docker-compose logs app`)
* **Database errors**: Ensure PostgreSQL container is running; verify `.env`
* **Audio issues**: Check format (WAV, MP3, M4A), size, and logs
* **Slow transcription/analysis**: Use smaller Whisper or Ollama model, check system resources

## Maintenance

* **View logs**

```bash
docker-compose logs -f app
```

* **Database backup**

```bash
docker-compose exec postgres pg_dump -U postgres postgres > backup.sql
```

* **Restore backup**

```bash
docker-compose exec -T postgres psql -U postgres postgres < backup.sql
```

* **Update application**

```bash
git pull
docker-compose down
docker-compose up -d --build
```

* **Clean up Docker**

```bash
docker-compose down -v
docker system prune -a
```

## Advanced Configuration

* Production: strong passwords, ENVIRONMENT=production, SSL, reverse proxy, backups
* Custom Whisper or Ollama models via `.env` and `ollama pull`
* Custom ports or external database by editing `.env` and `docker-compose.yml`
* Monitor resources: `docker stats` and health endpoints

## Next Steps

1. Test application with sample data
2. Configure Ollama if desired
3. Set up automated backups
4. Review security before production
5. Consult API documentation: [http://localhost:8001/api/docs](http://localhost:8001/api/docs)

## Additional Resources

* **README.md**: Project overview
* **API Documentation**: [http://localhost:8001/api/docs](http://localhost:8001/api/docs)
* **docs/API_IMPROVEMENTS.md**
* **docs/QUICK_REFERENCE.md**
* **CHANGELOG.md**

## Support

* Check troubleshooting section
* View logs: `docker-compose logs app`
* Check health endpoint: `curl http://localhost:8001/api/health`
* Verify all containers: `docker-compose ps`

---

**Last Updated:** November 2025
**Version:** 1.0.0

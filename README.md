# Behavioral Health Session Summarization Agent

An AI-powered clinical documentation tool designed for behavioral health professionals. Upload therapy session recordings or enter transcripts to receive comprehensive clinical analysis including summaries, diagnostic impressions, key therapeutic points, and evidence-based treatment recommendations.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [System Architecture](#system-architecture)
- [Usage Guide](#usage-guide)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)

## Overview

This application streamlines clinical documentation for behavioral health professionals by:
- **Transcribing** audio recordings of therapy sessions using OpenAI Whisper
- **Analyzing** session content with AI-powered or rule-based clinical analysis
- **Generating** comprehensive session notes with diagnostic impressions and treatment plans
- **Storing** complete session data including full transcripts for future reference

The system is designed with healthcare compliance in mind, featuring audit logging, data sanitization, and secure handling of sensitive information.

## Key Features

### Core Functionality
- **Audio Transcription**: Automatic transcription using OpenAI Whisper (base model)
  - Supports: WAV, MP3, M4A, FLAC, OGG, WebM formats
  - Caching for improved performance
  - Confidence scoring

- **Clinical Analysis**: Dual-mode analysis system
  - **AI-Powered**: Uses Ollama LLM for detailed, context-aware analysis
  - **Rule-Based Fallback**: Context-aware analysis when LLM unavailable
    - Crisis situations (safety concerns)
    - Anxiety disorders
    - Depression
    - Relationship issues
    - Trauma/PTSD
    - Substance use
    - Work-related stress
    - General therapeutic concerns

- **Session Management**
  - Complete transcript storage
  - Duplicate detection
  - Session reanalysis capability
  - Pagination and search

### Advanced Features
- **Reanalysis**: Reanalyze sessions with fresh analysis or when LLM becomes available
- **Flexible Analysis**: Choose between AI-powered or rule-based analysis
- **Caching**: Intelligent caching for transcriptions and analyses
- **Audit Logging**: Complete audit trail for compliance
- **Security**: Input validation, data sanitization, PII protection

## Quick Start

### Prerequisites

- **Docker & Docker Compose** (required)
- **Ollama** (optional, for AI-powered analysis)
- **4GB+ RAM** (8GB+ recommended for Ollama)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jpark8215/behavioral-health-agent
   cd behavioral-health-agent
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults work for most setups)
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Web Interface: http://localhost:8001
   - API Documentation: http://localhost:8001/api/docs
   - Health Check: http://localhost:8001/api/health

### First Use

1. Open http://localhost:8001 in your browser
2. Either:
   - **Upload an audio file** (WAV, MP3, etc.) for transcription and analysis
   - **Enter a text transcript** directly for analysis
3. Click "Analyze" and wait for results
4. View the generated clinical summary, diagnosis, key points, and treatment plan

**Note**: First audio transcription takes ~10-15 seconds as Whisper model loads. Subsequent transcriptions are much faster.

## System Architecture

### Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Interface                           │
│                   (FastAPI + Jinja2)                        │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Audio      │  │   Analysis   │  │   Database   │       │
│  │   Service    │  │   Service    │  │   Client     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
┌────────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐
│  OpenAI Whisper │  │  Ollama LLM     │  │  PostgreSQL    │
│  (Transcription)│  │  (Optional)     │  │  (Storage)     │
└─────────────────┘  └─────────────────┘  └────────────────┘
                              │
                     ┌────────▼────────┐
                     │  Rule-Based     │
                     │  Fallback       │
                     └─────────────────┘
```

### Components

- **FastAPI**: Modern Python web framework for API and web interface
- **PostgreSQL**: Reliable storage for sessions, transcripts, and analyses
- **Redis**: Caching layer for improved performance
- **OpenAI Whisper**: State-of-the-art speech recognition
- **Ollama** (Optional): Local LLM for enhanced analysis
- **Rule-Based Engine**: Intelligent fallback when LLM unavailable

### Data Flow

1. **Audio Upload** → Whisper Transcription → Text
2. **Text/Transcript** → Analysis Service → Clinical Analysis
3. **Analysis** → Database Storage → Session Record
4. **Retrieval** → Database Query → Complete Session Data

## Usage Guide

### Web Interface

#### Analyzing a Session

1. **Navigate** to http://localhost:8001
2. **Choose input method**:
   - Click "Upload Audio" for audio files
   - Or paste transcript text directly
3. **Add metadata** (optional):
   - Patient ID
   - Session date
   - Session type
4. **Click "Analyze"**
5. **Review results**:
   - Clinical summary
   - Diagnostic impression
   - Key therapeutic points
   - Treatment recommendations

#### Viewing Past Sessions

1. Click "Sessions" in navigation
2. Browse session list
3. Click any session to view full details including transcript

#### Reanalyzing a Session

1. Open a session
2. Click "Reanalyze"
3. Choose analysis type (AI or Rule-based)
4. View updated analysis

### API Usage

#### Analyze Text Transcript

```bash
curl -X POST "http://localhost:8001/api/summarize" \
  -F "transcript=Patient reports feeling anxious about work deadlines..."
```

#### Upload and Analyze Audio

```bash
curl -X POST "http://localhost:8001/api/upload-audio" \
  -F "audio_file=@session.wav"
```

#### Get Session Details

```bash
curl "http://localhost:8001/api/sessions/{session_id}"
```

#### Reanalyze Session

```bash
curl -X POST "http://localhost:8001/api/sessions/{session_id}/reanalyze" \
  -F "use_external_llm=true"
```

#### List All Sessions

```bash
curl "http://localhost:8001/api/sessions?limit=50&offset=0"
```

## API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/api/summarize` | POST | Analyze text transcript |
| `/api/upload-audio` | POST | Upload and transcribe audio |
| `/api/sessions` | GET | List all sessions |
| `/api/sessions/{id}` | GET | Get specific session |
| `/api/sessions/{id}/reanalyze` | POST | Reanalyze session |
| `/api/health` | GET | System health check |
| `/api/docs` | GET | Interactive API docs (Swagger) |

### Request Parameters

#### POST /api/summarize
- `transcript` (required): Session transcript text (10-50,000 characters)
- `metadata` (optional): JSON metadata object
- `force_reanalysis` (optional): Boolean, bypass cache for fresh analysis

#### POST /api/upload-audio
- `audio_file` (required): Audio file (WAV, MP3, M4A, FLAC, OGG, WebM)
- `metadata` (optional): JSON metadata object

#### POST /api/sessions/{id}/reanalyze
- `use_external_llm` (optional): Boolean, use Ollama (true) or rule-based (false)

#### GET /api/sessions
- `limit` (optional): Number of results (1-100, default: 50)
- `offset` (optional): Pagination offset (default: 0)

### Response Format

All successful responses include:
- `session_id`: Unique identifier
- `note`: Complete session note object
  - `id`: Session ID
  - `transcript`: Full transcript text
  - `summary`: Clinical summary
  - `diagnosis`: Diagnostic impression
  - `key_points`: Array of key observations
  - `treatment_plan`: Array of recommendations
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

For complete API documentation, visit http://localhost:8001/api/docs

## Configuration

### Environment Variables

Key configuration options in `.env`:

#### Database
```bash
POSTGRES_PASSWORD=your_secure_password  # Required
POSTGRES_HOST=postgres                   # Default: postgres
POSTGRES_PORT=5432                       # Default: 5432
POSTGRES_DB=postgres                     # Default: postgres
```

#### Redis
```bash
REDIS_HOST=redis                         # Default: redis
REDIS_PORT=6379                          # Default: 6379
```

#### Ollama (Optional)
```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434  # Default
OLLAMA_MODEL=mistral:7b              # Default model
```

#### Application
```bash
PORT=8001                                # Default: 8001
ENVIRONMENT=development                  # development or production
WHISPER_MODEL_SIZE=base                  # tiny, base, small, medium, large
```

### Ollama Setup (Optional)

For enhanced AI-powered analysis:

1. **Install Ollama**
   - Windows: Download from https://ollama.ai
   - macOS: `brew install ollama`
   - Linux: `curl -fsSL https://ollama.ai/install.sh | sh`

2. **Start Ollama**
   ```bash
   ollama serve
   ```

3. **Pull a model**
   ```bash
   # Smaller model (less memory, faster)
   ollama pull mistral:7b
   
   # Larger model (more memory, better quality)
   ollama pull granite3.3:8b
   ```

4. **Update .env**
   ```bash
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   OLLAMA_MODEL=mistral:7b
   ```

**Note**: If Ollama is unavailable or runs out of memory, the system automatically uses rule-based analysis.

## Troubleshooting

### Application Won't Start

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs app

# Restart services
docker-compose restart
```

### Audio Upload Fails

**Symptoms**: Upload returns error or times out

**Solutions**:
1. Check file format (must be WAV, MP3, M4A, FLAC, OGG, or WebM)
2. Verify file size (recommended < 50MB)
3. Check logs: `docker-compose logs app --tail 50`
4. Ensure sufficient disk space for Whisper model (~140MB)

### Analysis Returns Generic Results

**Symptoms**: All analyses seem similar or generic

**Cause**: Ollama unavailable or out of memory, using rule-based fallback

**Solutions**:
1. Check Ollama status: `ollama list`
2. Use smaller model: `ollama pull qwen2.5:1.5b`
3. Increase system memory
4. Use reanalysis feature when Ollama available:
   ```bash
   curl -X POST "http://localhost:8001/api/sessions/{id}/reanalyze" \
     -F "use_external_llm=true"
   ```

### Transcripts Not Showing

**Symptoms**: Sessions created but transcript field empty

**Solutions**:
1. Check database connection:
   ```bash
   docker-compose logs postgres
   ```
2. Verify session in database:
   ```bash
   docker-compose exec postgres psql -U postgres -d postgres \
     -c "SELECT id, LENGTH(transcript) FROM sessions LIMIT 5;"
   ```
3. Check application logs for errors

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Performance Issues

**Slow transcription**:
- First transcription loads Whisper model (~10-15 seconds)
- Subsequent transcriptions use cached model (much faster)
- Consider using smaller Whisper model: `WHISPER_MODEL_SIZE=tiny`

**Slow analysis**:
- Ollama analysis depends on model size and system resources
- Rule-based analysis is instant
- Use caching (automatic for identical transcripts)

## Documentation

### Main Documentation
- **README.md** (this file) - Project overview and quick start
- **LOCAL_DEPLOYMENT_GUIDE.md** - Detailed deployment instructions
- **CHANGELOG.md** - Version history and changes

### Additional Documentation
- **docs/API_IMPROVEMENTS.md** - Complete API reference
- **docs/QUICK_REFERENCE.md** - Quick command reference
- **docs/FIXES_SUMMARY.md** - Recent updates and fixes

### Getting Help

1. Check the [Troubleshooting](#troubleshooting) section
2. Review [LOCAL_DEPLOYMENT_GUIDE.md](LOCAL_DEPLOYMENT_GUIDE.md) for detailed setup
3. Check logs: `docker-compose logs app --tail 100`
4. Visit API docs: http://localhost:8001/api/docs

## Project Structure

```
behavioral-health-agent/
├── core/                   # Core utilities
│   ├── exceptions.py       # Custom exceptions
│   └── security.py         # Security and audit logging
├── database/               # Database layer
│   └── postgres_client.py  # PostgreSQL operations
├── models/                 # Data models
│   └── schemas.py          # Pydantic schemas
├── services/               # Business logic
│   ├── audio_service.py    # Audio transcription
│   ├── analysis_service.py # Clinical analysis
│   ├── ollama_service.py   # LLM integration
│   └── ollama_config.py    # LLM configuration
├── templates/              # HTML templates
├── static/                 # Static assets (CSS, JS)
├── docs/                   # Documentation
├── config.py               # Application configuration
├── main.py                 # FastAPI application
├── docker-compose.yml      # Docker orchestration
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Security & Compliance

### Data Protection
- Input validation on all endpoints
- Data sanitization for PII
- Secure password handling
- SQL injection prevention

### Audit Logging
- All operations logged with timestamps
- Session access tracking
- Data processing events
- Security event monitoring

### Healthcare Compliance
- Designed with HIPAA considerations
- Audit trail for all operations
- PII protection in logs
- Secure data storage

**Note**: This application is a tool to assist healthcare professionals. It does not replace professional clinical judgment and should be used as part of a comprehensive clinical workflow.

## Contributing

Contributions are welcome! Please ensure:
- Code passes all diagnostics
- Documentation is updated
- Security best practices followed
- Tests are included where appropriate

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Maintainer**: Jieun Park

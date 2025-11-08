# Behavioral Health Session Summarization Agent

An AI-powered clinical documentation tool for behavioral health professionals. Upload therapy session recordings or transcripts to receive comprehensive analyses, including clinical summaries, diagnostic impressions, key therapeutic points, and evidence-based treatment recommendations.

---

## Overview

This system automates clinical note generation by:

- **Transcribing** audio sessions via OpenAI Whisper  
- **Analyzing** transcripts using AI or rule-based logic  
- **Generating** structured clinical summaries and treatment recommendations  
- **Storing** complete data in PostgreSQL for secure retrieval  

Designed with healthcare compliance in mind, featuring audit logging, data sanitization, and secure handling of sensitive information.

---

## Key Features

### Core
- **Audio Transcription** (WAV, MP3, M4A, FLAC, OGG, WebM) with caching and confidence scoring  
- **AI or Rule-Based Clinical Analysis** with fallback for crisis, anxiety, depression, trauma, substance use, work stress, and general therapy concerns  
- **Session Management**: full transcript storage, duplicate detection, reanalysis, pagination, and search  

### Advanced
- **Ollama LLM Integration** (optional local inference)  
- **Intelligent caching & reanalysis**  
- **Audit logging** for compliance  
- **Security**: input validation, PII protection, SQL injection prevention  

---

## System Architecture

```mermaid
flowchart TD
    A[Web Interface (FastAPI + Jinja2)] --> B[FastAPI Application]
    B --> C[Audio Service]
    B --> D[Analysis Service]
    B --> E[Database Client]
    C --> F[OpenAI Whisper]
    D --> G[Ollama LLM (Optional)]
    D --> H[Rule-Based Fallback]
    E --> I[PostgreSQL Storage]
````

* **FastAPI**: Web/API layer
* **PostgreSQL**: Persistent storage
* **Redis**: Caching layer
* **OpenAI Whisper**: Speech-to-text engine
* **Ollama (Optional)**: AI-powered analysis
* **Rule-Based Engine**: Fallback when LLM unavailable

---

## Setup & Configuration

### Prerequisites

* Docker & Docker Compose
* Ollama (optional for AI-powered analysis)
* 4GB+ RAM (8GB+ recommended for Ollama)

### Installation

```bash
git clone https://github.com/jpark8215/behavioral-health-agent
cd behavioral-health-agent
cp .env.example .env
docker-compose up -d
```

### Access

* Web App: [http://localhost:8001](http://localhost:8001)
* API Docs: [http://localhost:8001/api/docs](http://localhost:8001/api/docs)
* Health Check: [http://localhost:8001/api/health](http://localhost:8001/api/health)

### Environment Variables

```bash
POSTGRES_PASSWORD=your_secure_password  # Required
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=postgres
REDIS_HOST=redis
REDIS_PORT=6379
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
PORT=8001
ENVIRONMENT=development
WHISPER_MODEL_SIZE=base
```

---

## Database Management

PostgreSQL stores all session data. Manage it via CLI, pgAdmin, or external clients.

### Quick Commands

| Task                    | Command                                                                                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| View 10 latest sessions | `docker-compose exec postgres psql -U postgres -d postgres -c "SELECT id, created_at, summary FROM sessions ORDER BY created_at DESC LIMIT 10;"` |
| Count total sessions    | `docker-compose exec postgres psql -U postgres -d postgres -c "SELECT COUNT(*) FROM sessions;"`                                                  |
| Delete a session        | `docker-compose exec postgres psql -U postgres -d postgres -c "DELETE FROM sessions WHERE id='xxx';"`                                            |
| Backup DB               | `docker-compose exec postgres pg_dump -U postgres postgres > backup.sql`                                                                         |
| Restore DB              | `docker-compose exec -T postgres psql -U postgres postgres < backup.sql`                                                                         |

### Access Methods

#### 1. Command Line (psql)

```bash
docker-compose exec postgres psql -U postgres -d postgres
```

Inside `psql`:

```sql
\dt                 -- List tables
\d sessions         -- Describe table
SELECT * FROM sessions LIMIT 5;
\q                  -- Exit
```

#### 2. pgAdmin (Web GUI)

```bash
docker-compose --profile tools up -d pgadmin
```

* Visit: [http://localhost:5050](http://localhost:5050)
* Login: `admin@localhost.com` / `admin`
* Connect to host `postgres` (port `5432`, user `postgres`)

#### 3. Desktop Clients

* **DBeaver** (Free) — [https://dbeaver.io](https://dbeaver.io)
* **TablePlus** — [https://tableplus.com](https://tableplus.com)
* **DataGrip (JetBrains, Paid)**

---

### Common SQL Tasks

| Task                  | Example                                                                       |
| --------------------- | ----------------------------------------------------------------------------- |
| View sessions by date | `SELECT DATE(created_at), COUNT(*) FROM sessions GROUP BY 1 ORDER BY 1 DESC;` |
| Search by keyword     | `SELECT id, summary FROM sessions WHERE transcript ILIKE '%anxiety%';`        |
| Delete old sessions   | `DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '30 days';`         |
| Optimize table        | `VACUUM ANALYZE sessions;`                                                    |

---

### Backup & Restore (Summarized)

| Action            | Command                                                          |                       |
| ----------------- | ---------------------------------------------------------------- | --------------------- |
| Full backup       | `pg_dump -U postgres postgres > backup.sql`                      |                       |
| Table backup      | `pg_dump -U postgres -t sessions postgres > sessions_backup.sql` |                       |
| Restore           | `psql -U postgres postgres < backup.sql`                         |                       |
| Compressed backup | `pg_dump -U postgres postgres                                    | gzip > backup.sql.gz` |

Automate with cron:

```bash
0 2 * * * cd /path/to/project && docker-compose exec postgres pg_dump -U postgres postgres | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

---

## API & Data Flow

### Key Endpoints

| Endpoint                       | Method | Description                |
| ------------------------------ | ------ | -------------------------- |
| `/api/summarize`               | POST   | Analyze text transcript    |
| `/api/upload-audio`            | POST   | Transcribe & analyze audio |
| `/api/sessions`                | GET    | List sessions              |
| `/api/sessions/{id}`           | GET    | Get session details        |
| `/api/sessions/{id}/reanalyze` | POST   | Reanalyze with AI          |
| `/api/health`                  | GET    | System status              |

### Usage Examples

Analyze transcript:

```bash
curl -X POST "http://localhost:8001/api/summarize" \
  -F "transcript=Patient reports feeling anxious about work..."
```

Upload audio:

```bash
curl -X POST "http://localhost:8001/api/upload-audio" \
  -F "audio_file=@session.wav"
```

---

## Security & Compliance

* Change default DB password
* Restrict port 5432 in production
* Audit logging for all operations
* PII sanitization & SQL injection prevention
* HIPAA-aligned with complete audit trails

---

## Troubleshooting

| Issue                       | Solution                                         |
| --------------------------- | ------------------------------------------------ |
| App won’t start             | `docker-compose ps` → `docker-compose logs app`  |
| PostgreSQL down             | `docker-compose restart postgres`                |
| Audio upload fails          | Check format (WAV/MP3/etc.), size (<50MB), logs  |
| LLM unavailable             | Run `ollama serve` and reanalyze session         |
| Reset DB (⚠️ all data lost) | `docker-compose down -v && docker-compose up -d` |

---

## Project Structure

```
behavioral-health-agent/
├── core/               # Utilities
├── database/           # DB operations
├── models/             # Data models
├── services/           # Transcription & analysis
├── templates/          # Web UI
├── docker-compose.yml  # Orchestration
├── main.py             # FastAPI app
└── README.md           # This file
```

---

## Contributing

Contributions are welcome! Please ensure:
- Code passes all diagnostics
- Documentation is updated
- Security best practices followed
- Tests are included where appropriate

---

**Version:** 1.0.0
**Last Updated:** November 2025
**Maintainer:** Jieun Park
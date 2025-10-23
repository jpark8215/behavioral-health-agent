# Behavioral Health Session Summarization Agent

An AI-powered tool that processes behavioral health session transcripts and generates structured summaries, diagnoses, key points, and **clinically robust treatment plans** — running fully locally via Ollama (no external API calls).

## Features

- **Session Input**: Paste or upload therapy session transcripts
- **Local AI Analysis**: Summaries, diagnosis suggestions, key points, and evidence-based treatment plans
- **Enhanced Treatment Plans**: Card-based UI with numbered steps, titles, and concise descriptions
- **Session History**: Visual cards with colored avatars, diagnosis badges, and session previews
- **Responsive Design**: Adaptive layout that scales to viewport height
- **Export Options**: Copy to clipboard or download results as text file
- **Performance Optimized**: Fast inference with streamlined prompts (15-30s typical)
- **Error Pages**: Custom 404/500 views

## Prerequisites

- Python 3.9+ recommended
- **Ollama** installed and running ([Download Ollama](https://ollama.ai))
# Behavioral Health Session Summarization Agent

An AI-powered tool that processes behavioral health session transcripts and generates structured summaries, diagnoses, key points, and clinically actionable treatment plans — running fully locally via Ollama (no external external API calls required).

## Quickstart (Windows PowerShell)

1. Open PowerShell and change into the project directory:

```powershell
cd C:\Users\jpark\CascadeProjects\behavioral-health-agent
```

2. Create and activate the virtual environment:

```powershell
python -m venv .venv
# Activate (PowerShell)
& .\.venv\Scripts\Activate.ps1
# If script execution is blocked in this PowerShell session, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
# then re-run the Activate command above.
```

3. Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Note: If you see a pip launcher error like "Fatal error in launcher: Unable to create process...", run pip via the Python module as shown above (`python -m pip ...`) which avoids launcher issues. To repair the pip shim you can run:

```powershell
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

4. Configure environment variables

Create a `.env` file in the project root (see example below) or set environment variables in your shell.

Example `.env` (recommended):

```
HOST=127.0.0.1
PORT=8000
ENVIRONMENT=development
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=granite3.3:8b
SESSIONS_FILE=data/sessions/sessions.json
USE_DUMMY_LLM=false
```

5. Pull and run Ollama (separate terminal)

```powershell
# Download Ollama from https://ollama.ai and install
ollama pull granite3.3:8b
ollama serve
```

6. Run the server (development)

```powershell
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open http://127.0.0.1:8000 in your browser.

## Features

- Session input (paste or upload transcript text)
- Local inference via Ollama with configurable model
- Structured output: summary, diagnosis, key points, and treatment plan items
- Session persistence to a local JSON file (`SESSIONS_FILE`)
- Health endpoint: `GET /api/health`
- Dummy LLM mode for testing (`USE_DUMMY_LLM=true`)

## API Endpoints

- `POST /api/summarize` — Analyze a transcript and return a session note
- `GET /api/notes` — List session notes (pagination)
- `GET /api/notes/{session_id}` — Get a specific session note
- `GET /api/health` — Health check and Ollama connection status

## Notes about a recent bugfix

While loading sessions from disk the app attempted to compute a `content_hash` for backward compatibility. This required a helper `generate_content_hash` to be defined before `load_sessions` ran on import. The codebase has been updated so the helper is defined before sessions are loaded, preventing a NameError during startup. If you previously saw `Error loading sessions: name 'generate_content_hash' is not defined`, please restart your server after pulling the latest changes.

## Development / Testing

- To enable deterministic dummy outputs for tests, set `USE_DUMMY_LLM=true` in your `.env`.
- Run tests (if present):

```powershell
python -m pytest
```

## Troubleshooting

- Ollama connection: Check `http://localhost:11434/api/tags` or use the `/api/health` endpoint
- Session file issues: Ensure `data/sessions/sessions.json` exists and is writable by your user
- Pip launcher errors: use `python -m pip` or reinstall pip in the venv as shown above

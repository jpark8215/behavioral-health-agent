import os
import json
import uuid
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Form, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Behavioral Health Session Summarization Agent",
    description="An AI-powered tool for summarizing behavioral health sessions",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Create necessary directories
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("data/sessions", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Add CORS middleware (configure according to your needs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "granite3.3:8b")

# Cache Ollama connection status for 30 seconds
_ollama_connection_cache = {"status": None, "timestamp": 0}

def check_ollama_connection() -> bool:
    """Check if Ollama is running and accessible (with caching)."""
    import time
    current_time = time.time()
    
    # Return cached result if less than 30 seconds old
    if current_time - _ollama_connection_cache["timestamp"] < 30:
        if _ollama_connection_cache["status"] is not None:
            return _ollama_connection_cache["status"]
    
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        status = response.status_code == 200
        _ollama_connection_cache["status"] = status
        _ollama_connection_cache["timestamp"] = current_time
        return status
    except Exception as e:
        logger.error(f"Cannot connect to Ollama: {e}")
        _ollama_connection_cache["status"] = False
        _ollama_connection_cache["timestamp"] = current_time
        return False

class SessionNote(BaseModel):
    """Model for storing session notes and summaries"""
    id: str = Field(default_factory=lambda: f"session_{uuid.uuid4().hex[:8]}")
    content_hash: str = Field(..., description="Hash of transcript content for duplicate detection")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    transcript: str = Field(..., description="The raw transcript of the session")
    summary: str = Field(..., description="The generated summary of the session")
    diagnosis: str = Field(..., description="The suggested diagnosis based on the session")
    key_points: List[str] = Field(default_factory=list, description="Key points from the session")
    treatment_plan: List[str] = Field(default_factory=list, description="Suggested treatment plan")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

# In-memory storage (replace with a database in production)
session_notes: Dict[str, SessionNote] = {}

# Load existing sessions from disk
SESSIONS_FILE = os.getenv("SESSIONS_FILE", "data/sessions/sessions.json")

def generate_content_hash(transcript: str) -> str:
    """Generate a hash of the transcript content for duplicate detection."""
    # Normalize content by stripping whitespace and converting to lowercase
    normalized_content = transcript.strip().lower()
    # Generate MD5 hash
    return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()

def load_sessions() -> Dict[str, SessionNote]:
    """Load sessions from disk."""
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                sessions_data = json.load(f)
                loaded_sessions = {}
                for sid, data in sessions_data.items():
                    # Handle backward compatibility for sessions without content_hash
                    if 'content_hash' not in data:
                        data['content_hash'] = generate_content_hash(data.get('transcript', ''))
                    loaded_sessions[sid] = SessionNote(**data)
                return loaded_sessions
    except Exception as e:
        logger.error(f"Error loading sessions: {e}")
    return {}

def save_sessions():
    """Save sessions to disk."""
    try:
        os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {sid: note.dict() for sid, note in session_notes.items()},
                f,
                indent=2,
                default=str,
                ensure_ascii=False
            )
    except Exception as e:
        logger.error(f"Error saving sessions: {e}")

# Load existing sessions on startup
session_notes = load_sessions()

# Load existing sessions on startup
def _parse_json_safely(text: str) -> Dict[str, Any]:
    """Try to parse JSON; if it fails, attempt to extract the first JSON object block."""
    if not text or not isinstance(text, str):
        return {}
    
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract the largest {...} block
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # As a last resort, return empty dict
    logger.warning(f"Failed to parse JSON from text: {text[:100]}...")
    return {}

def generate_session_summary(transcript: str) -> dict:
    """Generate a summary, diagnosis, and treatment plan using Ollama with Granite 3.3."""
    try:
        # Check if using dummy mode
        use_dummy = os.getenv("USE_DUMMY_LLM", "false").lower() == "true"
        if use_dummy:
            dummy_json = {
                "summary": "Patient discussed ongoing stressors and coping strategies.",
                "diagnosis": "Adjustment disorder (provisional)",
                "key_points": [
                    "Stress related to work performance",
                    "Sleep disturbances reported",
                    "Interest in CBT techniques"
                ],
                "treatment_plan": [
                    "Cognitive Behavioral Therapy (CBT): Weekly 50-minute sessions for 12 weeks focusing on identifying and restructuring maladaptive thought patterns related to work performance. Implement thought records 3x/week to track automatic thoughts, emotions, and behavioral responses.",
                    "Sleep Hygiene Protocol: Establish consistent sleep-wake schedule (10:30 PM - 6:30 AM). Implement stimulus control techniques including 20-minute rule for sleep onset. Track sleep quality using daily sleep diary. Goal: Achieve 7-8 hours of consolidated sleep within 4 weeks.",
                    "Behavioral Activation: Schedule 3 pleasurable activities per week to counter avoidance patterns. Use activity monitoring log to track engagement and mood correlation. Measurable outcome: Increase in positive affect ratings by 30% within 6 weeks.",
                    "Stress Management Skills: Practice progressive muscle relaxation (PMR) daily for 15 minutes. Introduce diaphragmatic breathing exercises for acute stress episodes. Goal: Reduce subjective stress ratings from 8/10 to 5/10 or below within 8 weeks.",
                    "Homework Assignments: Complete weekly thought records, maintain sleep diary, practice relaxation techniques daily, and engage in scheduled behavioral activation activities. Review progress in each session.",
                    "Outcome Measures: Administer GAD-7 and PHQ-9 at baseline, week 6, and week 12 to track symptom reduction. Target: 50% reduction in anxiety and depression scores by end of treatment.",
                    "Adjunct Recommendations: Consider psychiatric consultation if symptoms do not improve by week 6 for medication evaluation. Provide psychoeducation materials on stress management and cognitive distortions."
                ]
            }
            return dummy_json
        
        # Check Ollama connection
        if not check_ollama_connection():
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to Ollama. Please ensure Ollama is running with 'ollama serve'"
            )
        
        system_message = (
            "You are a behavioral health counselor. Return ONLY valid JSON with keys: "
            "summary (string), diagnosis (string), key_points (array of 3-5 strings), treatment_plan (array of 4-6 strings).\n\n"
            "Treatment plan format: 'Title: Brief description with specific technique, frequency, and goal.'\n"
            "Example: 'CBT Sessions: Weekly 50-min sessions for 12 weeks. Use thought records 3x/week. Goal: 50% symptom reduction.'\n"
            "Keep each item under 200 characters. Be specific and actionable."
        )
        
        user_message = f"Transcript:\n{transcript[:2000]}\n\nProvide concise JSON analysis."
        
        # Call Ollama API
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.3,
                "num_predict": 1024,  # Reduced for faster generation
                "num_ctx": 2048,  # Reduced context window
                "top_p": 0.9,
                "top_k": 40
            }
        }
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=120,  
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Ollama API error: {response.text}"
            )
        
        result = response.json()
        text = result.get("message", {}).get("content", "{}")
        parsed = _parse_json_safely(text)

        # Fill with defaults if missing
        summary = parsed.get("summary") or ""
        diagnosis = parsed.get("diagnosis") or ""
        key_points = parsed.get("key_points") or []
        treatment_plan = parsed.get("treatment_plan") or []

        # Coerce types
        if not isinstance(key_points, list):
            key_points = [str(key_points)]
        if not isinstance(treatment_plan, list):
            treatment_plan = [str(treatment_plan)]

        return {
            "summary": str(summary),
            "diagnosis": str(diagnosis),
            "key_points": [str(x) for x in key_points],
            "treatment_plan": [str(x) for x in treatment_plan],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ollama inference error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@app.post("/api/summarize")
async def summarize_session(
    transcript: str = Form(..., min_length=10, description="The session transcript to analyze"),
    metadata: Optional[str] = Form(None, description="Optional metadata in JSON format"),
    force_reanalysis: bool = Form(False, description="Force re-analysis even if duplicate content exists")
):
    """
    Submit a session transcript and receive a summary, diagnosis, and treatment plan.
    
    - **transcript**: The session transcript text (minimum 10 characters)
    - **metadata**: Optional JSON string with additional metadata (e.g., patient ID, session date)
    - **force_reanalysis**: Force re-analysis even if duplicate content exists
    """
    try:
        # Parse metadata if provided
        note_metadata = {}
        if metadata:
            try:
                note_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid metadata format. Must be valid JSON."
                )
        
        # Generate content hash for duplicate detection
        content_hash = generate_content_hash(transcript)
        
        # Check for existing session with same content hash unless forced
        if not force_reanalysis:
            for session_id, session in session_notes.items():
                if hasattr(session, 'content_hash') and session.content_hash == content_hash:
                    return {
                        "session_id": session_id,
                        "note": jsonable_encoder(session),
                        "is_duplicate": True
                    }
        
        # Generate the summary and analysis
        analysis = generate_session_summary(transcript)
        
        # Create a new session note
        note = SessionNote(
            content_hash=content_hash,
            transcript=transcript,
            summary=analysis.get("summary", ""),
            diagnosis=analysis.get("diagnosis", ""),
            key_points=analysis.get("key_points", []),
            treatment_plan=analysis.get("treatment_plan", []),
            metadata=note_metadata
        )
        
        # Store the note
        session_notes[note.id] = note
        save_sessions()
        
        return {
            "session_id": note.id,
            "note": jsonable_encoder(note),
            "is_duplicate": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in summarize_session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

@app.get("/api/notes/{session_id}", response_model=SessionNote)
async def get_session_note(session_id: str):
    """
    Retrieve a session note by ID.
    
    - **session_id**: The ID of the session to retrieve
    """
    if session_id not in session_notes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found"
        )
    return session_notes[session_id]

@app.get("/api/notes")
async def list_session_notes(
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "-created_at"
):
    """
    List all session notes with pagination and sorting.
    
    - **skip**: Number of items to skip (for pagination)
    - **limit**: Maximum number of items to return (for pagination)
    - **sort_by**: Field to sort by (prefix with - for descending order)
    """
    try:
        # Validate pagination parameters
        skip = max(0, skip)
        limit = min(max(1, limit), 1000)  # Cap at 1000
        
        # Convert to list for sorting (only include necessary fields for performance)
        notes_list = [
            {
                "id": sid,
                "created_at": note.created_at,
                "updated_at": note.updated_at,
                "summary": note.summary[:200] if note.summary else "",  # Truncate for list view
                "diagnosis": note.diagnosis,
                "content_hash": getattr(note, 'content_hash', None)  # Include content_hash for duplicate detection
            }
            for sid, note in session_notes.items()
        ]
        
        # Sort the notes
        reverse_sort = sort_by.startswith('-')
        sort_field = sort_by[1:] if reverse_sort else sort_by
        
        # Handle nested fields and missing keys
        def get_sort_key(item):
            keys = sort_field.split('.')
            value = item
            for key in keys:
                value = value.get(key, '')
                if value is None:
                    return ''
            return value
        
        notes_list.sort(
            key=get_sort_key,
            reverse=reverse_sort
        )
        
        # Apply pagination
        total = len(notes_list)
        paginated_notes = notes_list[skip:skip + limit]
        
        return {
            "sessions": paginated_notes,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + limit < total
        }
        
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving session notes"
        )

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "css_file": "/static/styles.css",
            "app_name": "Behavioral Health Summarizer",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "max_file_size_mb": 10
        },
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Custom exception handlers
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.detail if hasattr(exc, 'detail') else "Not Found"},
        )
    return templates.TemplateResponse(
        "404.html",
        {"request": request},
        status_code=404
    )

@app.exception_handler(500)
async def server_error_exception_handler(request: Request, exc: Exception):
    logger.error(f"Server error: {exc}", exc_info=True)
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
    return templates.TemplateResponse(
        "500.html",
        {"request": request},
        status_code=500
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(exc.errors())},
    )

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    ollama_status = "connected" if check_ollama_connection() else "disconnected"
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "sessions_count": len(session_notes),
        "ollama_status": ollama_status,
        "ollama_model": OLLAMA_MODEL
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Configure logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s [%(name)s] %(levelprefix)s %(message)s"
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s [%(name)s] %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_config=log_config,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )

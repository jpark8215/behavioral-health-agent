"""
Behavioral Health Session Summarization Agent
Enhanced with proper architecture, security, and error handling
"""
import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Form, Request, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer

# Import improved components
from config import settings
from models.schemas import (
    TranscriptRequest, AnalysisResponse, SessionNote, 
    AudioUploadResponse, HealthCheckResponse, ErrorResponse
)
from core.exceptions import (
    validation_error, processing_error, service_unavailable_error,
    not_found_error, internal_server_error
)
from core.security import AuditLogger, DataSanitizer, ContentValidator
from services.analysis_service import analysis_service
from services.audio_service import audio_service
from database.postgres_client import get_postgres_client
import hashlib
import json

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title=settings.app_name,
    description="Enhanced AI-powered tool for behavioral health session analysis",
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    responses={
        400: {"model": ErrorResponse, "description": "Validation Error"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Processing Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        503: {"model": ErrorResponse, "description": "Service Unavailable"},
    }
)

# Security
security = HTTPBearer(auto_error=False)

# CORS middleware
if settings.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing and security info"""
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} for {request.method} {request.url.path} "
        f"in {process_time:.3f}s"
    )
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Database client
db_client = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db_client
    try:
        db_client = get_postgres_client()
        await db_client.connect()
        logger.info("Application startup completed successfully")
        
        AuditLogger.log_data_processing(
            operation="application_startup",
            data_type="system",
            success=True
        )
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        AuditLogger.log_data_processing(
            operation="application_startup",
            data_type="system",
            success=False,
            error_message=str(e)
        )

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Application shutdown initiated")
    AuditLogger.log_data_processing(
        operation="application_shutdown",
        data_type="system",
        success=True
    )

def get_client_ip(request: Request) -> str:
    """Extract client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@app.post("/api/summarize", response_model=AnalysisResponse)
async def analyze_transcript(
    request: Request,
    transcript: str = Form(..., min_length=10, max_length=50000),
    metadata: Optional[str] = Form(None),
    force_reanalysis: bool = Form(False)
):
    """
    Analyze therapy session transcript with enhanced validation and security
    """
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    try:
        # Validate database connection
        if not db_client:
            raise service_unavailable_error("Database")
        
        # Validate and sanitize transcript
        is_valid, error_msg = ContentValidator.validate_transcript(transcript)
        if not is_valid:
            raise validation_error(error_msg)
        
        # Parse and validate metadata
        note_metadata = {}
        if metadata:
            try:
                import json
                note_metadata = json.loads(metadata)
                is_valid, error_msg = ContentValidator.validate_metadata(note_metadata)
                if not is_valid:
                    raise validation_error(f"Invalid metadata: {error_msg}")
            except json.JSONDecodeError:
                raise validation_error("Invalid metadata format. Must be valid JSON.")
        
        # Generate content hash for duplicate detection
        content_hash = hashlib.sha256(transcript.encode()).hexdigest()
        
        # Check for duplicates unless forced
        if not force_reanalysis:
            existing_session = await db_client.check_duplicate_by_hash(content_hash)
            if existing_session:
                AuditLogger.log_session_access(
                    session_id=existing_session["id"],
                    action="duplicate_detected",
                    ip_address=client_ip
                )
                
                return AnalysisResponse(
                    session_id=existing_session["id"],
                    note=SessionNote(**existing_session),
                    is_duplicate=True
                )
        
        # Perform clinical analysis with reanalysis option
        analysis = await analysis_service.analyze_session(
            transcript, 
            use_external_llm=True,
            force_reanalysis=force_reanalysis
        )
        
        # Create session data
        session_data = {
            "content_hash": content_hash,
            "transcript": transcript,
            "summary": analysis.summary,
            "diagnosis": analysis.diagnosis,
            "key_points": analysis.key_points,
            "treatment_plan": analysis.treatment_plan,
            "metadata": note_metadata,
            "processing_status": "completed"
        }
        
        # Store in database
        created_session = await db_client.create_session(session_data)
        
        # Log successful analysis
        processing_time = int((time.time() - start_time) * 1000)
        AuditLogger.log_session_access(
            session_id=created_session["id"],
            action="created",
            ip_address=client_ip
        )
        
        return AnalysisResponse(
            session_id=created_session["id"],
            note=SessionNote(**created_session),
            is_duplicate=False,
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_transcript: {str(e)}", exc_info=True)
        AuditLogger.log_security_event(
            event_type="analysis_error",
            severity="medium",
            description=f"Analysis failed: {str(e)}",
            ip_address=client_ip
        )
        raise internal_server_error("Analysis processing failed")

@app.get("/api/health", response_model=HealthCheckResponse)
async def enhanced_health_check():
    """Comprehensive health check with detailed service status"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "version": settings.app_version,
            "environment": settings.environment
        }
        
        # Check database
        if db_client:
            try:
                await db_client.connect()
                health_status["database_status"] = "connected"
            except Exception as e:
                health_status["database_status"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
        else:
            health_status["database_status"] = "not_configured"
            health_status["status"] = "degraded"
        
        # Check Ollama service
        try:
            ollama_health = await analysis_service.ollama_service.health_check()
            health_status["ollama_service"] = ollama_health
            if ollama_health.get("status") != "healthy":
                # Ollama issues don't degrade overall status since we have fallback
                pass
        except Exception as e:
            health_status["ollama_service"] = {"status": "error", "error": str(e)}
        
        # Check audio service
        try:
            audio_health = await audio_service.health_check()
            health_status["audio_service"] = audio_health
            if not audio_health.get("whisper_available", False):
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["audio_service"] = {"status": "error", "error": str(e)}
            health_status["status"] = "degraded"
        
        return HealthCheckResponse(**health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            environment=settings.environment,
            database_status="error",
            error=str(e)
        )

@app.post("/api/upload-audio", response_model=AudioUploadResponse)
async def upload_audio(
    request: Request,
    audio_file: UploadFile = File(...),
    metadata: Optional[str] = Form(None)
):
    """
    Upload and transcribe audio file with enhanced validation
    """
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    try:
        # Validate file
        is_valid, error_msg = ContentValidator.validate_audio_file(audio_file)
        if not is_valid:
            raise validation_error(error_msg)
        
        # Parse metadata if provided
        note_metadata = {}
        if metadata:
            try:
                note_metadata = json.loads(metadata)
                is_valid, error_msg = ContentValidator.validate_metadata(note_metadata)
                if not is_valid:
                    raise validation_error(f"Invalid metadata: {error_msg}")
            except json.JSONDecodeError:
                raise validation_error("Invalid metadata format. Must be valid JSON.")
        
        # Process audio file
        audio_content = await audio_file.read()
        
        # Transcribe audio
        transcription_result = await audio_service.transcribe_audio(
            audio_content, 
            audio_file.filename
        )
        
        if not transcription_result.get("success"):
            raise processing_error(
                "Audio transcription failed",
                details=transcription_result.get("error")
            )
        
        transcript = transcription_result["transcript"]
        
        # Validate transcript length
        if len(transcript.strip()) < 10:
            raise validation_error("Transcribed content too short for analysis")
        
        # Generate analysis (always use LLM for audio uploads)
        analysis = await analysis_service.analyze_session(
            transcript,
            use_external_llm=True,
            force_reanalysis=False
        )
        
        # Create session data
        content_hash = hashlib.sha256(transcript.encode()).hexdigest()
        session_data = {
            "content_hash": content_hash,
            "transcript": transcript,
            "summary": analysis.summary,
            "diagnosis": analysis.diagnosis,
            "key_points": analysis.key_points,
            "treatment_plan": analysis.treatment_plan,
            "metadata": {
                **note_metadata,
                "audio_filename": audio_file.filename,
                "audio_size": len(audio_content),
                "transcription_confidence": transcription_result.get("confidence", 0.0)
            },
            "processing_status": "completed"
        }
        
        # Store in database
        created_session = await db_client.create_session(session_data)
        
        # Log successful processing
        processing_time = int((time.time() - start_time) * 1000)
        AuditLogger.log_data_processing(
            operation="audio_upload_transcription",
            data_type="audio",
            success=True,
            session_id=created_session["id"]
        )
        
        return AudioUploadResponse(
            session_id=created_session["id"],
            transcript=transcript,
            note=SessionNote(**created_session),
            processing_time_ms=processing_time,
            transcription_confidence=transcription_result.get("confidence", 0.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_audio: {str(e)}", exc_info=True)
        AuditLogger.log_data_processing(
            operation="audio_upload_transcription",
            data_type="audio",
            success=False,
            error_message=str(e)
        )
        raise internal_server_error("Audio processing failed")

@app.get("/api/sessions/{session_id}")
async def get_session(
    request: Request,
    session_id: str
):
    """
    Retrieve session by ID with audit logging
    """
    client_ip = get_client_ip(request)
    
    try:
        if not db_client:
            raise service_unavailable_error("Database")
        
        session = await db_client.get_session(session_id)
        if not session:
            raise not_found_error("Session", str(session_id))
        
        AuditLogger.log_session_access(
            session_id=session_id,
            action="retrieved",
            ip_address=client_ip
        )
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session {session_id}: {str(e)}", exc_info=True)
        AuditLogger.log_security_event(
            event_type="session_access_error",
            severity="medium",
            description=f"Failed to retrieve session {session_id}",
            ip_address=client_ip
        )
        raise internal_server_error("Session retrieval failed")

@app.post("/api/sessions/{session_id}/reanalyze", response_model=AnalysisResponse)
async def reanalyze_session(
    request: Request,
    session_id: str,
    use_external_llm: bool = Form(True)
):
    """
    Reanalyze an existing session with fresh analysis
    Useful when Ollama was unavailable or for getting updated analysis
    """
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    try:
        if not db_client:
            raise service_unavailable_error("Database")
        
        # Get existing session
        session = await db_client.get_session(session_id)
        if not session:
            raise not_found_error("Session", str(session_id))
        
        transcript = session.get("transcript")
        if not transcript:
            raise validation_error("Session has no transcript to reanalyze")
        
        # Perform fresh analysis
        analysis = await analysis_service.analyze_session(
            transcript,
            use_external_llm=use_external_llm,
            force_reanalysis=True
        )
        
        # Update session with new analysis
        update_data = {
            "summary": analysis.summary,
            "diagnosis": analysis.diagnosis,
            "key_points": analysis.key_points,
            "treatment_plan": analysis.treatment_plan,
            "processing_status": "reanalyzed"
        }
        
        updated_session = await db_client.update_session(session_id, update_data)
        
        # Log reanalysis
        processing_time = int((time.time() - start_time) * 1000)
        AuditLogger.log_session_access(
            session_id=session_id,
            action="reanalyzed",
            ip_address=client_ip
        )
        
        return AnalysisResponse(
            session_id=session_id,
            note=SessionNote(**updated_session),
            is_duplicate=False,
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reanalyzing session {session_id}: {str(e)}", exc_info=True)
        AuditLogger.log_security_event(
            event_type="reanalysis_error",
            severity="medium",
            description=f"Reanalysis failed for session {session_id}",
            ip_address=client_ip
        )
        raise internal_server_error("Reanalysis failed")

@app.get("/api/sessions")
async def list_sessions(
    request: Request,
    limit: int = 50,
    offset: int = 0
):
    """
    List recent sessions with pagination
    """
    client_ip = get_client_ip(request)
    
    try:
        if not db_client:
            raise service_unavailable_error("Database")
        
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            raise validation_error("Limit must be between 1 and 100")
        if offset < 0:
            raise validation_error("Offset must be non-negative")
        
        result = await db_client.list_sessions(skip=offset, limit=limit)
        
        AuditLogger.log_data_processing(
            operation="sessions_list",
            data_type="session_metadata",
            success=True
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        AuditLogger.log_security_event(
            event_type="sessions_list_error",
            severity="medium",
            description="Failed to list sessions",
            ip_address=client_ip
        )
        raise internal_server_error("Sessions listing failed")

@app.get("/", response_class=HTMLResponse)
async def web_interface(request: Request):
    """
    Serve the main web interface
    """
    try:
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request,
                "app_name": settings.app_name,
                "version": settings.app_version
            }
        )
    except Exception as e:
        logger.error(f"Error serving web interface: {str(e)}")
        raise internal_server_error("Web interface unavailable")

@app.get("/sessions/{session_id}", response_class=HTMLResponse)
async def view_session(request: Request, session_id: int):
    """
    Serve session view page
    """
    try:
        return templates.TemplateResponse(
            "session.html",
            {
                "request": request,
                "session_id": session_id,
                "app_name": settings.app_name
            }
        )
    except Exception as e:
        logger.error(f"Error serving session view: {str(e)}")
        raise internal_server_error("Session view unavailable")

# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with sanitized responses"""
    client_ip = get_client_ip(request)
    
    AuditLogger.log_security_event(
        event_type="validation_error",
        severity="low",
        description="Request validation failed",
        ip_address=client_ip,
        additional_data={"errors": exc.errors()}
    )
    
    from fastapi.responses import JSONResponse
    error = validation_error(
        message="Request validation failed",
        details={"validation_errors": exc.errors()}
    )
    return JSONResponse(
        status_code=error.status_code,
        content=error.detail
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle internal server errors with sanitized responses"""
    client_ip = get_client_ip(request)
    
    logger.error(f"Internal server error: {exc}", exc_info=True)
    AuditLogger.log_security_event(
        event_type="internal_error",
        severity="high",
        description="Internal server error occurred",
        ip_address=client_ip
    )
    
    from fastapi.responses import JSONResponse
    # Don't expose internal error details in production
    if settings.environment == "production":
        error = internal_server_error("An internal error occurred")
    else:
        error = internal_server_error(f"Internal error: {str(exc)}")
    
    return JSONResponse(
        status_code=error.status_code,
        content=error.detail
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )
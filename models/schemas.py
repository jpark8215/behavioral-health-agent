"""
Pydantic models for request/response validation and data structures
Ensures type safety and validation for behavioral health application
"""
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ProcessingStatus(str, Enum):
    """Session processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisType(str, Enum):
    """Type of clinical analysis"""
    CRISIS = "crisis"
    ANXIETY = "anxiety"
    DEPRESSION = "depression"
    RELATIONSHIP = "relationship"
    TRAUMA = "trauma"
    SUBSTANCE_USE = "substance_use"
    WORK_STRESS = "work_stress"
    GENERAL = "general"


class SessionMetadata(BaseModel):
    """Metadata for therapy sessions"""
    patient_id: Optional[str] = Field(None, description="Patient identifier (anonymized)")
    session_date: Optional[datetime] = Field(None, description="Session date")
    session_duration_minutes: Optional[int] = Field(None, ge=1, le=300)
    therapist_id: Optional[str] = Field(None, description="Therapist identifier")
    session_type: Optional[str] = Field(None, description="Type of therapy session")
    audio_info: Optional[Dict[str, Any]] = Field(None, description="Audio file information")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ClinicalAnalysis(BaseModel):
    """Clinical analysis results"""
    summary: str = Field(..., min_length=10, max_length=1000, description="Session summary")
    diagnosis: str = Field(..., min_length=5, max_length=500, description="Clinical impression")
    key_points: List[str] = Field(..., min_items=1, max_items=10, description="Key therapeutic points")
    treatment_plan: List[str] = Field(..., min_items=1, max_items=15, description="Treatment recommendations")
    analysis_type: AnalysisType = Field(default=AnalysisType.GENERAL, description="Type of analysis performed")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Analysis confidence")
    
    @validator("key_points")
    def validate_key_points(cls, v):
        """Validate key points are not empty"""
        return [point.strip() for point in v if point.strip()]
    
    @validator("treatment_plan")
    def validate_treatment_plan(cls, v):
        """Validate treatment plan items"""
        return [item.strip() for item in v if item.strip()]


class SessionNote(BaseModel):
    """Complete session note with analysis"""
    id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    content_hash: str = Field(..., description="Content hash for duplicate detection")
    transcript: str = Field(..., min_length=10, description="Session transcript")
    summary: str = Field(..., description="Clinical summary")
    diagnosis: str = Field(..., description="Clinical diagnosis/impression")
    key_points: List[str] = Field(..., description="Key therapeutic points")
    treatment_plan: List[str] = Field(..., description="Treatment recommendations")
    metadata: SessionMetadata = Field(default_factory=SessionMetadata, description="Session metadata")
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.COMPLETED)
    audio_file_path: Optional[str] = Field(None, description="Path to audio file")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TranscriptRequest(BaseModel):
    """Request for transcript analysis"""
    transcript: str = Field(..., min_length=10, max_length=50000, description="Session transcript")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    force_reanalysis: bool = Field(False, description="Force re-analysis of duplicate content")
    
    @validator("transcript")
    def validate_transcript(cls, v):
        """Validate and clean transcript"""
        cleaned = v.strip()
        if len(cleaned) < 10:
            raise ValueError("Transcript must be at least 10 characters")
        return cleaned


class AudioUploadResponse(BaseModel):
    """Response for audio upload and transcription"""
    session_id: str = Field(..., description="Session identifier")
    transcript: str = Field(..., description="Transcribed text")
    note: SessionNote = Field(..., description="Complete session note with analysis")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    transcription_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Transcription confidence score")


class AnalysisResponse(BaseModel):
    """Response for analysis request"""
    session_id: str = Field(..., description="Session identifier")
    note: SessionNote = Field(..., description="Complete session note")
    is_duplicate: bool = Field(False, description="Whether this is a duplicate analysis")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")


class SessionListResponse(BaseModel):
    """Response for session list"""
    sessions: List[SessionNote] = Field(..., description="List of sessions")
    total: int = Field(..., ge=0, description="Total number of sessions")
    skip: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Maximum items returned")
    has_more: bool = Field(..., description="Whether more items are available")


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    database_status: str = Field(..., description="Database connection status")
    ollama_service: Optional[Dict[str, Any]] = Field(None, description="Ollama service status")
    audio_service: Optional[Dict[str, Any]] = Field(None, description="Audio service status")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Standardized error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
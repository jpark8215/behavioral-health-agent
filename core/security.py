"""
Security utilities for behavioral health application
Implements data sanitization, audit logging, and security controls
"""
import re
import hashlib
import logging
from typing import Any, Dict, Optional
from datetime import datetime
import json

# Configure audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Create audit log handler if not exists
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    audit_logger.addHandler(handler)


class DataSanitizer:
    """Sanitizes sensitive data for logging and storage"""
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = {
        'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
        'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'credit_card': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        'date_of_birth': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
    }
    
    @classmethod
    def sanitize_text(cls, text: str, replacement: str = "[REDACTED]") -> str:
        """Remove sensitive information from text"""
        if not text:
            return text
            
        sanitized = text
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            sanitized = pattern.sub(replacement, sanitized)
        
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], sensitive_keys: Optional[list] = None) -> Dict[str, Any]:
        """Sanitize sensitive keys in dictionary"""
        if not data:
            return data
            
        sensitive_keys = sensitive_keys or [
            'password', 'token', 'secret', 'key', 'ssn', 'social_security',
            'credit_card', 'phone', 'email', 'address', 'dob', 'date_of_birth'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, sensitive_keys)
            else:
                sanitized[key] = value
                
        return sanitized


class AuditLogger:
    """Audit logging for healthcare compliance"""
    
    @staticmethod
    def log_session_access(
        session_id: str,
        user_id: Optional[str] = None,
        action: str = "view",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log session access for audit trail"""
        audit_data = {
            "event_type": "session_access",
            "session_id": str(session_id),  # Convert UUID to string
            "user_id": user_id or "anonymous",
            "action": action,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        audit_logger.info(json.dumps(audit_data))
    
    @staticmethod
    def log_data_processing(
        operation: str,
        data_type: str,
        record_count: int = 1,
        processing_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log data processing operations"""
        audit_data = {
            "event_type": "data_processing",
            "operation": operation,
            "data_type": data_type,
            "record_count": record_count,
            "processing_time_ms": processing_time_ms,
            "success": success,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if session_id:
            audit_data["session_id"] = str(session_id)
        
        if additional_data:
            audit_data["additional_data"] = additional_data
        
        audit_logger.info(json.dumps(audit_data))
    
    @staticmethod
    def log_security_event(
        event_type: str,
        severity: str,
        description: str,
        ip_address: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log security-related events"""
        audit_data = {
            "event_type": "security_event",
            "security_event_type": event_type,
            "severity": severity,
            "description": description,
            "ip_address": ip_address,
            "additional_data": DataSanitizer.sanitize_dict(additional_data or {}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        audit_logger.info(json.dumps(audit_data))


class ContentValidator:
    """Validates content for security and compliance"""
    
    # Potentially harmful patterns
    HARMFUL_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'<iframe[^>]*>', re.IGNORECASE),
        re.compile(r'<object[^>]*>', re.IGNORECASE),
        re.compile(r'<embed[^>]*>', re.IGNORECASE),
    ]
    
    @classmethod
    def validate_transcript(cls, transcript: str) -> tuple[bool, Optional[str]]:
        """Validate transcript content for security"""
        if not transcript:
            return False, "Transcript cannot be empty"
        
        # Check for potentially harmful content
        for pattern in cls.HARMFUL_PATTERNS:
            if pattern.search(transcript):
                return False, "Transcript contains potentially harmful content"
        
        # Check length limits
        if len(transcript) > 50000:  # 50KB limit
            return False, "Transcript exceeds maximum length"
        
        if len(transcript.strip()) < 10:
            return False, "Transcript is too short for meaningful analysis"
        
        return True, None
    
    @classmethod
    def validate_metadata(cls, metadata: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate metadata for security"""
        if not metadata:
            return True, None
        
        # Check for reasonable size
        try:
            json_str = json.dumps(metadata)
            if len(json_str) > 10000:  # 10KB limit
                return False, "Metadata exceeds maximum size"
        except (TypeError, ValueError):
            return False, "Metadata contains non-serializable content"
        
        return True, None
    
    @classmethod
    def validate_audio_file(cls, audio_file) -> tuple[bool, Optional[str]]:
        """Validate audio file for security and format"""
        if not audio_file:
            return False, "No audio file provided"
        
        # Check filename
        if not audio_file.filename:
            return False, "Audio file has no filename"
        
        # Check file extension
        allowed_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm']
        file_ext = audio_file.filename.lower()
        if not any(file_ext.endswith(ext) for ext in allowed_extensions):
            return False, f"Unsupported audio format. Allowed: {', '.join(allowed_extensions)}"
        
        # Check content type if available
        if hasattr(audio_file, 'content_type') and audio_file.content_type:
            allowed_types = ['audio/', 'application/octet-stream']
            if not any(audio_file.content_type.startswith(t) for t in allowed_types):
                return False, f"Invalid content type: {audio_file.content_type}"
        
        return True, None


def generate_secure_hash(content: str, salt: Optional[str] = None) -> str:
    """Generate secure hash for content identification"""
    if salt:
        content = f"{salt}{content}"
    
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data showing only last few characters"""
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ""
    
    return mask_char * (len(data) - visible_chars) + data[-visible_chars:]
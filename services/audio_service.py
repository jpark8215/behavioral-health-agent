import os
import uuid
import logging
import tempfile
import asyncio
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import aiofiles
import soundfile as sf
import librosa
from functools import wraps
import redis
import pickle

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based caching service for audio processing"""
    
    def __init__(self):
        # Build Redis URL from environment variables
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        redis_url = os.getenv('REDIS_URL', f'redis://{redis_host}:{redis_port}')
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=False)
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis cache service initialized successfully at {redis_url}")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.redis_client = None
            self._memory_cache = {}
    
    def _get_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key"""
        return f"{prefix}:{identifier}"
    
    def set_cache(self, key: str, value: Any, ttl: int = 3600):
        """Set cache value with TTL"""
        try:
            if self.redis_client:
                if isinstance(value, str):
                    self.redis_client.setex(key, ttl, value.encode('utf-8'))
                else:
                    self.redis_client.setex(key, ttl, pickle.dumps(value))
            else:
                # Fallback to memory cache
                import time
                self._memory_cache[key] = {
                    'value': value,
                    'expires': time.time() + ttl
                }
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        try:
            if self.redis_client:
                result = self.redis_client.get(key)
                if result:
                    try:
                        return pickle.loads(result)
                    except:
                        return result.decode('utf-8')
                return None
            else:
                # Fallback to memory cache
                import time
                if key in self._memory_cache:
                    cache_item = self._memory_cache[key]
                    if time.time() < cache_item['expires']:
                        return cache_item['value']
                    else:
                        del self._memory_cache[key]
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def cache_transcription(self, audio_hash: str, transcript: str, ttl: int = 3600):
        """Cache transcription results"""
        key = self._get_key("transcription", audio_hash)
        self.set_cache(key, transcript, ttl)
    
    def get_cached_transcription(self, audio_hash: str) -> Optional[str]:
        """Get cached transcription"""
        key = self._get_key("transcription", audio_hash)
        return self.get_cache(key)

# Global cache service instance
cache_service = CacheService()

def cache_transcription(ttl: int = 3600):
    """Decorator for caching transcription results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, audio_data: bytes, *args, **kwargs):
            # Generate hash of audio data for caching
            audio_hash = hashlib.sha256(audio_data).hexdigest()
            
            # Check cache first
            cached = cache_service.get_cached_transcription(audio_hash)
            if cached:
                logger.info(f"Cache hit for transcription: {audio_hash[:8]}")
                return {
                    "file_path": None,
                    "transcript": cached,
                    "audio_info": {},  # Empty audio_info for cached results
                    "status": "completed",
                    "cached": True
                }
            
            # Generate transcription
            result = await func(self, audio_data, *args, **kwargs)
            
            # Cache result if successful
            if result.get("status") == "completed" and result.get("transcript"):
                cache_service.cache_transcription(audio_hash, result["transcript"], ttl)
                logger.info(f"Cached transcription: {audio_hash[:8]}")
            
            result["cached"] = False
            return result
        return wrapper
    return decorator

class OptimizedAudioService:
    """Optimized audio transcription service with model caching"""
    
    def __init__(self):
        self.temp_dir = Path("temp/audio")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Model caching with lazy loading
        self._whisper_model = None
        self._model_lock = asyncio.Lock()
        self._model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        
        logger.info(f"Initialized OptimizedAudioService with Whisper model: {self._model_size}")
    
    @property
    async def whisper_model(self):
        """Lazy-loaded, cached Whisper model"""
        if self._whisper_model is None:
            async with self._model_lock:
                if self._whisper_model is None:
                    logger.info(f"Loading Whisper model: {self._model_size}")
                    try:
                        import whisper
                        # Load model in thread to avoid blocking
                        self._whisper_model = await asyncio.to_thread(
                            whisper.load_model, self._model_size
                        )
                        logger.info(f"Whisper model {self._model_size} loaded successfully")
                    except Exception as e:
                        logger.error(f"Failed to load Whisper model: {e}")
                        raise
        return self._whisper_model
    
    async def save_audio_file(self, audio_data: bytes, filename: str) -> str:
        """Save uploaded audio file to temporary storage"""
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_extension = Path(filename).suffix.lower()
            if not file_extension:
                file_extension = '.wav'  # Default to WAV
            
            temp_filename = f"{file_id}{file_extension}"
            temp_path = self.temp_dir / temp_filename
            
            # Save file
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(audio_data)
            
            logger.info(f"Saved audio file: {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
            raise
    
    async def get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """Get audio file information"""
        try:
            # Use librosa to get audio info
            y, sr = librosa.load(file_path, sr=None)
            duration = len(y) / sr
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            return {
                "duration_seconds": duration,
                "sample_rate": sr,
                "file_size": file_size,
                "format": Path(file_path).suffix.lower().lstrip('.')
            }
        except Exception as e:
            logger.error(f"Error getting audio info for {file_path}: {e}")
            raise
    
    async def transcribe_audio_optimized(self, file_path: str) -> str:
        """Optimized transcription with cached model"""
        try:
            logger.info(f"Starting optimized transcription for: {file_path}")
            
            # Get cached model
            model = await self.whisper_model
            
            # Transcribe using cached model in thread
            result = await asyncio.to_thread(self._transcribe_with_cached_model, model, file_path)
            
            logger.info(f"Optimized transcription completed for: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error in optimized transcription {file_path}: {e}")
            # Fallback to error message
            return "Transcription failed. Please try again or enter text manually."
    
    def _transcribe_with_cached_model(self, model, audio_path: str) -> str:
        """Internal method using cached Whisper model"""
        try:
            # Use the cached model for transcription
            result = model.transcribe(
                audio_path,
                # Optimized parameters for healthcare domain
                language="en",
                task="transcribe",
                temperature=0.0,  # Deterministic output
                best_of=1,        # Faster processing
                beam_size=1,      # Faster processing
                patience=1.0,
                condition_on_previous_text=True,
                initial_prompt="This is a behavioral health therapy session transcript. Please transcribe accurately including medical and psychological terminology."
            )
            
            return result["text"].strip()
            
        except Exception as e:
            logger.error(f"Error in cached model transcription: {e}")
            return "Transcription failed. Please try again or enter text manually."
    
    @cache_transcription(ttl=3600)  # Cache for 1 hour
    async def process_audio_upload_optimized(self, audio_data: bytes, filename: str) -> Dict[str, Any]:
        """Optimized audio processing pipeline with caching"""
        try:
            # Save audio file
            file_path = await self.save_audio_file(audio_data, filename)
            
            # Get audio information
            audio_info = await self.get_audio_info(file_path)
            
            # Check if audio is too long (>1 hour)
            if audio_info.get("duration_seconds", 0) > 3600:
                return {
                    "file_path": file_path,
                    "transcript": "",
                    "audio_info": audio_info,
                    "status": "failed",
                    "error": "Audio file too long. Maximum duration is 1 hour."
                }
            
            # Transcribe audio with optimized model
            transcript = await self.transcribe_audio_optimized(file_path)
            
            return {
                "file_path": file_path,
                "transcript": transcript,
                "audio_info": audio_info,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error processing audio upload: {e}")
            return {
                "file_path": None,
                "transcript": "",
                "audio_info": {},
                "status": "failed",
                "error": str(e)
            }
    
    # Keep backward compatibility
    async def process_audio_upload(self, audio_data: bytes, filename: str) -> Dict[str, Any]:
        """Backward compatible method - delegates to optimized version"""
        return await self.process_audio_upload_optimized(audio_data, filename)
    
    async def transcribe_audio(self, audio_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Transcribe audio file and return result
        Main API method for audio transcription
        """
        result = await self.process_audio_upload_optimized(audio_data, filename)
        
        # Transform to expected format
        return {
            "success": result.get("status") == "completed",
            "transcript": result.get("transcript", ""),
            "confidence": 0.85 if result.get("status") == "completed" else 0.0,
            "audio_info": result.get("audio_info", {}),
            "cached": result.get("cached", False),
            "error": result.get("error")
        }
    
    async def cleanup_temp_file(self, file_path: str):
        """Clean up temporary audio file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temp file {file_path}: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for audio service"""
        try:
            # Check if Whisper can be imported
            whisper_available = False
            try:
                import whisper
                whisper_available = True
            except ImportError:
                pass
            
            # Check temp directory
            temp_dir_exists = self.temp_dir.exists()
            temp_dir_writable = os.access(self.temp_dir, os.W_OK) if temp_dir_exists else False
            
            # Check cache service
            cache_status = "unknown"
            try:
                if cache_service.redis_client:
                    cache_service.redis_client.ping()
                    cache_status = "redis_connected"
                else:
                    cache_status = "memory_cache"
            except Exception:
                cache_status = "cache_error"
            
            return {
                "status": "healthy" if whisper_available and temp_dir_writable else "degraded",
                "whisper_available": whisper_available,
                "temp_directory": {
                    "exists": temp_dir_exists,
                    "writable": temp_dir_writable,
                    "path": str(self.temp_dir)
                },
                "cache_service": cache_status,
                "model_size": self._model_size
            }
        except Exception as e:
            logger.error(f"Audio service health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "whisper_available": False
            }

# Global instance
audio_service = OptimizedAudioService()
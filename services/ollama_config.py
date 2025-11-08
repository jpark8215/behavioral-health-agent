"""
Optimized Ollama Configuration Service

This service manages Ollama model configurations, connection pooling,
and performance optimizations for the behavioral health application.
"""

import os
import json
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for an Ollama model"""
    name: str
    context_length: int = 4096
    temperature: float = 0.1
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    num_predict: int = -1
    stop_sequences: List[str] = None
    system_prompt: str = ""
    
    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = []

@dataclass
class ConnectionStats:
    """Statistics for Ollama connections"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    
class OllamaConfigService:
    """Optimized Ollama configuration and connection management"""
    
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.default_model = os.getenv("OLLAMA_MODEL", "mistral:7b")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))
        
        # Connection pool settings
        self.max_connections = 10
        self.max_keepalive_connections = 5
        self.keepalive_expiry = 30
        
        # Model configurations
        self.model_configs = self._load_model_configs()
        
        # Connection statistics
        self.stats = ConnectionStats()
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_created_at: Optional[datetime] = None
        self._session_lock = asyncio.Lock()
        
    def _load_model_configs(self) -> Dict[str, ModelConfig]:
        """Load model configurations from environment or defaults"""
        configs = {}
        
        # Default configuration for behavioral health analysis
        configs["behavioral_health"] = ModelConfig(
            name=self.default_model,
            context_length=8192,
            temperature=0.1,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.1,
            system_prompt="""You are an experienced behavioral health counselor and clinical psychologist. 
Analyze therapy session transcripts with clinical expertise and provide comprehensive assessments.

Guidelines:
- Use evidence-based therapeutic approaches
- Provide specific, actionable treatment recommendations
- Maintain professional clinical language
- Focus on observable behaviors and reported symptoms
- Consider differential diagnoses when appropriate
- Ensure recommendations are practical and measurable

Always respond in valid JSON format with the requested structure.""",
            stop_sequences=["Human:", "Assistant:", "User:", "AI:"]
        )
        
        # Fast configuration for quick responses
        configs["quick_analysis"] = ModelConfig(
            name=self.default_model,
            context_length=4096,
            temperature=0.2,
            top_p=0.8,
            num_predict=512,
            system_prompt="""Provide a brief clinical summary of the therapy session transcript.
Focus on key observations and primary recommendations. Be concise but thorough.
Respond in valid JSON format."""
        )
        
        # Detailed configuration for comprehensive analysis
        configs["detailed_analysis"] = ModelConfig(
            name=self.default_model,
            context_length=16384,
            temperature=0.05,
            top_p=0.95,
            repeat_penalty=1.05,
            system_prompt="""Conduct a comprehensive behavioral health analysis of the therapy session.
Provide detailed clinical insights, multiple treatment modalities, and thorough assessment.
Include risk factors, protective factors, and long-term treatment planning.
Respond in valid JSON format with extensive detail."""
        )
        
        return configs
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create an optimized aiohttp session"""
        async with self._session_lock:
            now = datetime.utcnow()
            
            # Create new session if needed
            if (self._session is None or 
                self._session.closed or
                (self._session_created_at and 
                 now - self._session_created_at > timedelta(minutes=30))):
                
                if self._session and not self._session.closed:
                    await self._session.close()
                
                # Create optimized connector
                connector = aiohttp.TCPConnector(
                    limit=self.max_connections,
                    limit_per_host=self.max_connections,
                    keepalive_timeout=self.keepalive_expiry,
                    enable_cleanup_closed=True,
                    ttl_dns_cache=300,
                    use_dns_cache=True
                )
                
                # Create session with optimized settings
                timeout = aiohttp.ClientTimeout(
                    total=self.timeout,
                    connect=30,
                    sock_read=60
                )
                
                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "BehavioralHealth-API/1.0"
                    }
                )
                
                self._session_created_at = now
                logger.info("Created new optimized Ollama session")
            
            return self._session
    
    async def close_session(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self._session_created_at = None
    
    def get_model_config(self, config_type: str = "behavioral_health") -> ModelConfig:
        """Get model configuration by type"""
        return self.model_configs.get(config_type, self.model_configs["behavioral_health"])
    
    async def check_model_availability(self, model_name: str = None) -> Dict[str, Any]:
        """Check if a specific model is available and loaded"""
        if not model_name:
            model_name = self.default_model
            
        try:
            session = await self.get_session()
            
            # Check available models
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    
                    # Check if our model is in the list
                    model_available = any(
                        model.get("name", "").startswith(model_name.split(":")[0])
                        for model in models
                    )
                    
                    return {
                        "available": model_available,
                        "models": [m.get("name") for m in models],
                        "status": "connected"
                    }
                else:
                    return {
                        "available": False,
                        "error": f"HTTP {response.status}",
                        "status": "error"
                    }
                    
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return {
                "available": False,
                "error": str(e),
                "status": "disconnected"
            }
    
    async def preload_model(self, model_name: str = None) -> bool:
        """Preload a model to improve first-request performance"""
        if not model_name:
            model_name = self.default_model
            
        try:
            session = await self.get_session()
            
            # Send a small request to preload the model
            payload = {
                "model": model_name,
                "prompt": "Hello",
                "stream": False,
                "options": {
                    "num_predict": 1,
                    "temperature": 0.1
                }
            }
            
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    logger.info(f"Model {model_name} preloaded successfully")
                    return True
                else:
                    logger.warning(f"Failed to preload model {model_name}: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error preloading model {model_name}: {e}")
            return False
    
    def build_chat_payload(
        self, 
        messages: List[Dict[str, str]], 
        config_type: str = "behavioral_health",
        custom_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Build optimized chat payload for Ollama"""
        config = self.get_model_config(config_type)
        
        # Base payload
        payload = {
            "model": config.name,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "num_ctx": config.context_length
            }
        }
        
        # Add num_predict if specified
        if config.num_predict > 0:
            payload["options"]["num_predict"] = config.num_predict
        
        # Add stop sequences if specified
        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences
        
        # Apply custom options
        if custom_options:
            payload["options"].update(custom_options)
        
        return payload
    
    def update_stats(self, success: bool, response_time: float):
        """Update connection statistics"""
        self.stats.total_requests += 1
        self.stats.last_request_time = datetime.utcnow()
        
        if success:
            self.stats.successful_requests += 1
        else:
            self.stats.failed_requests += 1
        
        # Update rolling average response time
        if self.stats.total_requests == 1:
            self.stats.average_response_time = response_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats.average_response_time = (
                alpha * response_time + 
                (1 - alpha) * self.stats.average_response_time
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        success_rate = 0.0
        if self.stats.total_requests > 0:
            success_rate = self.stats.successful_requests / self.stats.total_requests * 100
        
        return {
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": round(success_rate, 2),
            "average_response_time": round(self.stats.average_response_time, 2),
            "last_request": self.stats.last_request_time.isoformat() if self.stats.last_request_time else None,
            "session_active": self._session is not None and not self._session.closed
        }
    
    async def optimize_for_workload(self, expected_requests_per_minute: int):
        """Optimize configuration based on expected workload"""
        if expected_requests_per_minute > 30:
            # High load: optimize for throughput
            self.model_configs["behavioral_health"].temperature = 0.2
            self.model_configs["behavioral_health"].num_predict = 1024
            logger.info("Optimized for high-throughput workload")
            
        elif expected_requests_per_minute > 10:
            # Medium load: balanced configuration
            self.model_configs["behavioral_health"].temperature = 0.1
            self.model_configs["behavioral_health"].num_predict = -1
            logger.info("Optimized for balanced workload")
            
        else:
            # Low load: optimize for quality
            self.model_configs["behavioral_health"].temperature = 0.05
            self.model_configs["behavioral_health"].context_length = 16384
            logger.info("Optimized for high-quality analysis")

# Global instance
ollama_config = OllamaConfigService()
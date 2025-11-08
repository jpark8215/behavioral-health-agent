import os
import logging
import asyncio
import hashlib
import time
from typing import Dict, Any, Optional
import requests
import json
from functools import lru_cache

from .ollama_config import ollama_config

logger = logging.getLogger(__name__)

class OptimizedOllamaService:
    """Optimized Ollama service with healthcare-specific configuration"""
    
    def __init__(self):
        self.config_service = ollama_config
        self.base_url = self.config_service.base_url
        self.model = self.config_service.default_model
        self.timeout = self.config_service.timeout
        
        # Connection caching
        self._connection_cache = {"status": None, "timestamp": 0}
        self._cache_ttl = 30  # 30 seconds
        
        # Analysis caching
        self._analysis_cache = {}
        self._cache_max_size = 100
        
        logger.info(f"Initialized OptimizedOllamaService with model: {self.model}")
    
    def check_connection(self) -> bool:
        """Check Ollama connection with caching"""
        current_time = time.time()
        
        # Return cached result if less than TTL seconds old
        if current_time - self._connection_cache["timestamp"] < self._cache_ttl:
            if self._connection_cache["status"] is not None:
                return self._connection_cache["status"]
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            status = response.status_code == 200
            self._connection_cache["status"] = status
            self._connection_cache["timestamp"] = current_time
            
            # Update config service stats
            self.config_service.update_stats(status, 0.1)  # Quick health check
            
            return status
        except Exception as e:
            logger.error(f"Cannot connect to Ollama: {e}")
            self._connection_cache["status"] = False
            self._connection_cache["timestamp"] = current_time
            
            # Update config service stats
            self.config_service.update_stats(False, 0)
            
            return False
    
    def get_optimized_config(self, transcript: str) -> Dict[str, Any]:
        """Get healthcare-optimized Ollama configuration based on transcript"""
        transcript_length = len(transcript)
        word_count = len(transcript.split())
        
        # Base configuration optimized for healthcare domain
        config = {
            "temperature": 0.4,           # Balanced creativity for clinical reasoning
            "top_p": 0.85,               # More focused responses
            "top_k": 30,                 # Reduced for consistency
            "repeat_penalty": 1.1,       # Prevent repetition
            "stop": [                    # Stop at dialogue markers
                "Human:", "Patient:", "Therapist:", "Dr.", "Client:"
            ]
        }
        
        # Dynamic configuration based on content length
        if word_count < 500:
            # Short sessions
            config.update({
                "num_predict": 1024,
                "num_ctx": 2048,
                "temperature": 0.3  # More deterministic for short content
            })
        elif word_count < 2000:
            # Medium sessions
            config.update({
                "num_predict": 1536,
                "num_ctx": 4096,
                "temperature": 0.4
            })
        else:
            # Long sessions
            config.update({
                "num_predict": 2048,
                "num_ctx": 8192,
                "temperature": 0.45  # Slightly more creative for complex cases
            })
        
        # Adjust for very long transcripts
        if transcript_length > 10000:
            config["num_ctx"] = min(16384, transcript_length + 2000)
            config["num_predict"] = 3072
        
        return config
    
    def get_healthcare_system_prompt(self) -> str:
        """Get optimized system prompt for healthcare domain"""
        return """You are an experienced behavioral health counselor and clinical psychologist with expertise in evidence-based treatments. 

Analyze the therapy session transcript and provide a comprehensive clinical assessment in valid JSON format.

REQUIRED JSON STRUCTURE:
{
  "summary": "Plain text summary here (2-3 sentences)",
  "diagnosis": "Plain text diagnosis here",
  "key_points": [
    "First key point as plain text",
    "Second key point as plain text",
    "Third key point as plain text"
  ],
  "treatment_plan": [
    "CBT: Weekly 50-min sessions focusing on cognitive restructuring for 12 weeks",
    "Homework: Complete thought records 3 times per week to track negative thoughts",
    "Mindfulness: Daily 10-minute meditation practice to reduce anxiety symptoms"
  ]
}

CRITICAL RULES:
1. ALL values must be simple strings - NO nested objects, NO dictionaries within values
2. "diagnosis" must be a single plain text string (e.g., "Major Depressive Disorder - Moderate Severity")
3. "key_points" must be an array of plain text strings
4. "treatment_plan" must be an array of plain text strings
5. Each treatment plan item should be a complete sentence describing the intervention
6. DO NOT use dictionary syntax like {'criteria': [...]} or {'intervention_type': '...'}
7. Write naturally as if documenting in a clinical note

Treatment plan guidelines:
- Start each item with the intervention type followed by a colon (e.g., "CBT:", "Medication:", "Therapy:")
- Include specific techniques, frequency, duration, and measurable goals in the same sentence
- Keep each item under 200 characters
- Focus on evidence-based practices

WRONG FORMAT: {"intervention_type": "CBT", "technique": "Cognitive Restructuring"}
RIGHT FORMAT: "CBT: Use cognitive restructuring techniques in weekly sessions to challenge negative thoughts"

Return ONLY valid JSON. Be specific, actionable, and clinically appropriate."""
    
    def get_user_prompt(self, transcript: str) -> str:
        """Get optimized user prompt with transcript"""
        # Truncate very long transcripts but preserve important parts
        if len(transcript) > 8000:
            # Keep first 3000 and last 3000 characters with indicator
            truncated = transcript[:3000] + "\n\n[... middle section truncated for analysis ...]\n\n" + transcript[-3000:]
            word_count = len(transcript.split())
            return f"Session Transcript ({word_count} words, truncated for analysis):\n\n{truncated}\n\nProvide comprehensive clinical analysis in JSON format."
        else:
            word_count = len(transcript.split())
            return f"Session Transcript ({word_count} words):\n\n{transcript}\n\nProvide comprehensive clinical analysis in JSON format."
    
    async def generate_analysis_optimized(self, transcript: str) -> Dict[str, Any]:
        """Generate optimized analysis with caching and healthcare-specific configuration"""
        start_time = time.time()
        
        try:
            # Check cache first
            content_hash = hashlib.md5(transcript.encode()).hexdigest()
            if content_hash in self._analysis_cache:
                logger.info(f"Cache hit for analysis: {content_hash[:8]}")
                return self._analysis_cache[content_hash]
            
            # Check connection
            if not self.check_connection():
                raise Exception("Cannot connect to Ollama. Please ensure Ollama is running.")
            
            # Use config service to build optimized payload
            messages = [
                {
                    "role": "system", 
                    "content": self.get_healthcare_system_prompt()
                },
                {
                    "role": "user", 
                    "content": self.get_user_prompt(transcript)
                }
            ]
            
            # Determine config type based on transcript length
            word_count = len(transcript.split())
            if word_count < 500:
                config_type = "quick_analysis"
            elif word_count > 2000:
                config_type = "detailed_analysis"
            else:
                config_type = "behavioral_health"
            
            # Build payload using config service
            payload = self.config_service.build_chat_payload(messages, config_type)
            
            # Add healthcare-specific optimizations
            healthcare_options = self.get_optimized_config(transcript)
            payload["options"].update(healthcare_options)
            
            logger.info(f"Starting Ollama analysis with config type: {config_type}")
            
            # Use config service session for request
            session = await self.config_service.get_session()
            
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama API error: {response.status} - {error_text}")
                
                result = await response.json()
                content = result.get("message", {}).get("content", "{}")
            
            # Parse JSON response
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                # Fallback parsing
                analysis = self._parse_json_safely(content)
            
            # Validate and clean response
            cleaned_analysis = self._validate_analysis_response(analysis)
            
            # Cache successful result
            if len(self._analysis_cache) >= self._cache_max_size:
                # Remove oldest entry (simple LRU)
                oldest_key = next(iter(self._analysis_cache))
                del self._analysis_cache[oldest_key]
            
            self._analysis_cache[content_hash] = cleaned_analysis
            logger.info(f"Cached analysis: {content_hash[:8]}")
            
            # Update performance stats
            response_time = time.time() - start_time
            self.config_service.update_stats(True, response_time)
            
            return cleaned_analysis
            
        except Exception as e:
            # Update performance stats for failure
            response_time = time.time() - start_time
            self.config_service.update_stats(False, response_time)
            
            logger.error(f"Error in optimized Ollama analysis: {e}")
            raise
    
    def _parse_json_safely(self, text: str) -> Dict[str, Any]:
        """Enhanced JSON parsing with healthcare-specific fallbacks"""
        if not text or not isinstance(text, str):
            return self._get_fallback_analysis()
        
        text = text.strip()
        
        # Try direct JSON parsing
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON block
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = text[start:end+1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Try to parse line by line for partial JSON
        try:
            lines = text.split('\n')
            json_lines = [line for line in lines if line.strip().startswith('"') and ':' in line]
            if json_lines:
                json_str = "{\n" + ",\n".join(json_lines) + "\n}"
                return json.loads(json_str)
        except:
            pass
        
        logger.warning(f"Failed to parse JSON, using fallback: {text[:200]}...")
        return self._get_fallback_analysis()
    
    def _clean_json_artifacts(self, text: str) -> str:
        """Remove JSON formatting artifacts like brackets, quotes, and escape characters"""
        if not text:
            return text
        
        text = text.strip()
        
        # If it's a dictionary string representation, try to extract readable text
        if text.startswith('{') and text.endswith('}'):
            try:
                # Try to parse as JSON/dict and extract values
                import ast
                try:
                    parsed = ast.literal_eval(text)
                    if isinstance(parsed, dict):
                        # Extract all string values and join them
                        values = []
                        for key, value in parsed.items():
                            if isinstance(value, list):
                                values.extend([str(v) for v in value])
                            else:
                                values.append(str(value))
                        if values:
                            text = '. '.join(values)
                except:
                    # If parsing fails, just remove the brackets
                    text = text[1:-1].strip()
            except:
                text = text[1:-1].strip()
        
        # Remove array brackets if the entire string is wrapped in them
        if text.startswith('[') and text.endswith(']'):
            text = text[1:-1].strip()
        
        # Remove leading/trailing quotes
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        
        # Clean up escaped quotes
        text = text.replace('\\"', '"').replace("\\'", "'")
        
        # Clean up escaped newlines and tabs
        text = text.replace('\\n', ' ').replace('\\r', '').replace('\\t', ' ')
        
        # Remove multiple spaces
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _validate_analysis_response(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean analysis response"""
        
        # Extract diagnosis properly - ensure it's a clean string without JSON formatting
        diagnosis_raw = analysis.get("diagnosis", "")
        if isinstance(diagnosis_raw, dict):
            # If diagnosis is a dict, extract the name or primary diagnosis
            diagnosis = diagnosis_raw.get("name") or diagnosis_raw.get("primary_diagnosis") or str(diagnosis_raw.get("diagnosis", ""))
            if not diagnosis:
                # Fallback to first value if it's a dict
                diagnosis = next(iter(diagnosis_raw.values())) if diagnosis_raw else ""
        elif isinstance(diagnosis_raw, str):
            diagnosis = diagnosis_raw
        else:
            diagnosis = str(diagnosis_raw)
        
        # Clean diagnosis from any JSON artifacts
        diagnosis = self._clean_json_artifacts(diagnosis)
        
        cleaned = {
            "summary": self._clean_json_artifacts(str(analysis.get("summary", "")).strip()),
            "diagnosis": diagnosis.strip(),
            "key_points": [],
            "treatment_plan": []
        }
        
        # Validate key_points
        key_points = analysis.get("key_points", [])
        if isinstance(key_points, list):
            cleaned_points = []
            for point in key_points:
                if isinstance(point, dict):
                    # If it's a dict, extract all values and join them
                    point_text = '. '.join([str(v) for v in point.values() if v])
                    cleaned_points.append(self._clean_json_artifacts(point_text))
                elif point and str(point).strip():
                    cleaned_points.append(self._clean_json_artifacts(str(point).strip()))
            cleaned["key_points"] = cleaned_points
        elif isinstance(key_points, str):
            cleaned["key_points"] = [self._clean_json_artifacts(key_points.strip())]
        
        # Validate treatment_plan - ensure clean strings without JSON formatting
        treatment_plan = analysis.get("treatment_plan", [])
        if isinstance(treatment_plan, list):
            cleaned_plan = []
            for item in treatment_plan:
                if isinstance(item, dict):
                    # If it's a dict, format it as a readable sentence
                    parts = []
                    
                    # Get intervention type
                    intervention = item.get('intervention_type', item.get('type', ''))
                    if intervention:
                        intervention = intervention.rstrip(':')
                    
                    # Get technique/description
                    technique = item.get('technique', item.get('description', ''))
                    
                    # Get frequency
                    frequency = item.get('frequency', '')
                    
                    # Get goal
                    goal = item.get('goal', '')
                    
                    # Get homework
                    homework = item.get('homework_assignment', item.get('homework', ''))
                    
                    # Build a natural sentence
                    if intervention and technique:
                        sentence = f"{intervention}: {technique}"
                        if frequency:
                            sentence += f" {frequency.lower()}"
                        if goal:
                            sentence += f". Goal: {goal}"
                        if homework:
                            sentence += f". Homework: {homework}"
                        item_text = sentence
                    elif intervention:
                        # Just intervention type with other details
                        sentence = f"{intervention}:"
                        details = []
                        if technique:
                            details.append(technique)
                        if frequency:
                            details.append(frequency)
                        if goal:
                            details.append(f"Goal: {goal}")
                        if homework:
                            details.append(f"Homework: {homework}")
                        if details:
                            sentence += " " + ". ".join(details)
                        item_text = sentence
                    else:
                        # No clear structure, just join all values
                        item_text = '. '.join([str(v) for v in item.values() if v])
                    
                    cleaned_plan.append(self._clean_json_artifacts(item_text))
                elif item and str(item).strip():
                    cleaned_plan.append(self._clean_json_artifacts(str(item).strip()))
            cleaned["treatment_plan"] = cleaned_plan
        elif isinstance(treatment_plan, str):
            cleaned["treatment_plan"] = [self._clean_json_artifacts(treatment_plan.strip())]
        
        # Ensure minimum content
        if not cleaned["summary"]:
            cleaned["summary"] = "Session analysis completed. Please review transcript for details."
        
        if not cleaned["diagnosis"]:
            cleaned["diagnosis"] = "Clinical assessment pending. Further evaluation recommended."
        
        if not cleaned["key_points"]:
            cleaned["key_points"] = ["Session content reviewed", "Clinical assessment in progress"]
        
        if not cleaned["treatment_plan"]:
            cleaned["treatment_plan"] = [
                "Clinical Assessment: Complete comprehensive evaluation to determine appropriate treatment approach",
                "Follow-up: Schedule follow-up session within 1-2 weeks to continue assessment and treatment planning"
            ]
        
        return cleaned
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis when parsing fails"""
        return {
            "summary": "Session analysis encountered technical difficulties. Manual review recommended.",
            "diagnosis": "Technical analysis incomplete. Clinical review required.",
            "key_points": [
                "Automated analysis encountered parsing issues",
                "Manual clinical review recommended",
                "Session content preserved for review"
            ],
            "treatment_plan": [
                "Clinical Review: Manual review of session transcript by qualified clinician",
                "Technical Support: Contact system administrator regarding analysis parsing issues",
                "Follow-up: Schedule follow-up session to ensure continuity of care"
            ]
        }
    
    async def preload_model(self) -> bool:
        """Preload the model for better performance"""
        return await self.config_service.preload_model(self.model)
    
    async def check_model_availability(self) -> Dict[str, Any]:
        """Check if the configured model is available"""
        return await self.config_service.check_model_availability(self.model)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        config_stats = self.config_service.get_performance_stats()
        
        # Add service-specific stats
        cache_hit_rate = 0.0
        if self.config_service.stats.total_requests > 0:
            cache_hit_rate = (len(self._analysis_cache) / self.config_service.stats.total_requests) * 100
        
        return {
            **config_stats,
            "cache_size": len(self._analysis_cache),
            "cache_max_size": self._cache_max_size,
            "estimated_cache_hit_rate": round(cache_hit_rate, 2),
            "model": self.model,
            "base_url": self.base_url
        }
    
    async def optimize_for_load(self, expected_requests_per_minute: int):
        """Optimize service configuration based on expected load"""
        await self.config_service.optimize_for_workload(expected_requests_per_minute)
        
        # Adjust cache size based on load
        if expected_requests_per_minute > 30:
            self._cache_max_size = 200  # Larger cache for high load
        elif expected_requests_per_minute > 10:
            self._cache_max_size = 100  # Default cache size
        else:
            self._cache_max_size = 50   # Smaller cache for low load
        
        logger.info(f"Optimized for {expected_requests_per_minute} requests/min, cache size: {self._cache_max_size}")
    
    def clear_cache(self):
        """Clear the analysis cache"""
        self._analysis_cache.clear()
        logger.info("Analysis cache cleared")
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        connection_ok = self.check_connection()
        model_info = await self.check_model_availability()
        stats = self.get_performance_stats()
        
        return {
            "status": "healthy" if connection_ok and model_info.get("available") else "unhealthy",
            "connection": "ok" if connection_ok else "failed",
            "model_available": model_info.get("available", False),
            "model_name": self.model,
            "performance": stats,
            "cache_status": {
                "size": len(self._analysis_cache),
                "max_size": self._cache_max_size,
                "utilization": round((len(self._analysis_cache) / self._cache_max_size) * 100, 1)
            }
        }

# Global instance
ollama_service = OptimizedOllamaService()
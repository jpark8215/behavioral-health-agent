"""
Clinical Analysis Service
Centralized service for behavioral health session analysis with fallback mechanisms
"""
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from models.schemas import ClinicalAnalysis, AnalysisType
from core.exceptions import ProcessingError, ExternalServiceError
from core.security import AuditLogger, ContentValidator
from services.ollama_service import ollama_service

logger = logging.getLogger(__name__)


class ClinicalAnalysisService:
    """Service for clinical analysis of therapy sessions"""
    
    def __init__(self):
        self.ollama_service = ollama_service
        self.fallback_enabled = True
        
    async def analyze_session(
        self, 
        transcript: str, 
        use_external_llm: bool = True,
        force_reanalysis: bool = False
    ) -> ClinicalAnalysis:
        """
        Analyze therapy session transcript
        
        Args:
            transcript: Session transcript text
            use_external_llm: Whether to attempt external LLM analysis (default: True)
            force_reanalysis: Force new analysis even if cached (default: False)
            
        Returns:
            ClinicalAnalysis object with results
            
        Raises:
            ProcessingError: If analysis fails
        """
        start_time = time.time()
        
        try:
            # Validate content
            is_valid, error_msg = ContentValidator.validate_transcript(transcript)
            if not is_valid:
                raise ProcessingError(f"Invalid transcript: {error_msg}")
            
            # Clear cache if force reanalysis
            if force_reanalysis and use_external_llm:
                import hashlib
                content_hash = hashlib.md5(transcript.encode()).hexdigest()
                if content_hash in self.ollama_service._analysis_cache:
                    del self.ollama_service._analysis_cache[content_hash]
                    logger.info(f"Cleared cache for forced reanalysis: {content_hash[:8]}")
            
            # Attempt external LLM analysis first
            if use_external_llm:
                try:
                    result = await self._analyze_with_ollama(transcript)
                    if result:
                        processing_time = int((time.time() - start_time) * 1000)
                        AuditLogger.log_data_processing(
                            operation="clinical_analysis_llm",
                            data_type="transcript",
                            processing_time_ms=processing_time,
                            success=True,
                            additional_data={"forced": force_reanalysis}
                        )
                        return result
                except ExternalServiceError as e:
                    logger.warning(f"External LLM analysis failed: {e}")
                    if not self.fallback_enabled:
                        raise ProcessingError(f"LLM analysis failed and fallback disabled: {str(e)}")
                    logger.info("Using rule-based analysis as fallback")
            
            # Use rule-based analysis (either as fallback or by choice)
            result = self._analyze_with_fallback(transcript)
            
            processing_time = int((time.time() - start_time) * 1000)
            AuditLogger.log_data_processing(
                operation="clinical_analysis_rule_based",
                data_type="transcript",
                processing_time_ms=processing_time,
                success=True
            )
            
            return result
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            AuditLogger.log_data_processing(
                operation="clinical_analysis",
                data_type="transcript",
                processing_time_ms=processing_time,
                success=False,
                error_message=str(e)
            )
            raise ProcessingError(f"Analysis failed: {str(e)}")
    
    async def _analyze_with_ollama(self, transcript: str) -> Optional[ClinicalAnalysis]:
        """Attempt analysis using Ollama service"""
        try:
            if not self.ollama_service.check_connection():
                raise ExternalServiceError("Ollama service not available")
            
            # Use the existing ollama service for analysis
            result = await self.ollama_service.generate_analysis_optimized(transcript)
            
            if not result:
                return None
            
            # Convert to ClinicalAnalysis model
            analysis_type = self._determine_analysis_type(transcript)
            
            return ClinicalAnalysis(
                summary=result.get("summary", ""),
                diagnosis=result.get("diagnosis", ""),
                key_points=result.get("key_points", []),
                treatment_plan=result.get("treatment_plan", []),
                analysis_type=analysis_type,
                confidence_score=0.85  # High confidence for LLM analysis
            )
            
        except Exception as e:
            logger.error(f"Ollama analysis error: {e}")
            raise ExternalServiceError(f"External LLM analysis failed: {str(e)}")
    
    def _analyze_with_fallback(self, transcript: str) -> ClinicalAnalysis:
        """Rule-based fallback analysis"""
        transcript_lower = transcript.lower()
        analysis_type = self._determine_analysis_type(transcript)
        
        # Generate analysis based on detected type
        if analysis_type == AnalysisType.CRISIS:
            return self._generate_crisis_analysis(transcript)
        elif analysis_type == AnalysisType.ANXIETY:
            return self._generate_anxiety_analysis(transcript)
        elif analysis_type == AnalysisType.DEPRESSION:
            return self._generate_depression_analysis(transcript)
        elif analysis_type == AnalysisType.RELATIONSHIP:
            return self._generate_relationship_analysis(transcript)
        elif analysis_type == AnalysisType.TRAUMA:
            return self._generate_trauma_analysis(transcript)
        elif analysis_type == AnalysisType.SUBSTANCE_USE:
            return self._generate_substance_analysis(transcript)
        elif analysis_type == AnalysisType.WORK_STRESS:
            return self._generate_work_stress_analysis(transcript)
        else:
            return self._generate_general_analysis(transcript)
    
    def _determine_analysis_type(self, transcript: str) -> AnalysisType:
        """Determine the primary analysis type based on content"""
        transcript_lower = transcript.lower()
        
        # Crisis indicators (highest priority)
        crisis_keywords = ["suicidal", "suicide", "kill myself", "end it all", "harm myself", "die"]
        if any(keyword in transcript_lower for keyword in crisis_keywords):
            return AnalysisType.CRISIS
        
        # Anxiety indicators
        anxiety_keywords = ["panic", "anxiety", "anxious", "worried", "nervous", "fear", "phobia"]
        if any(keyword in transcript_lower for keyword in anxiety_keywords):
            return AnalysisType.ANXIETY
        
        # Depression indicators
        depression_keywords = ["depressed", "depression", "sad", "hopeless", "empty", "worthless", "guilt"]
        if any(keyword in transcript_lower for keyword in depression_keywords):
            return AnalysisType.DEPRESSION
        
        # Relationship indicators
        relationship_keywords = ["relationship", "marriage", "divorce", "family", "partner", "spouse", "conflict"]
        if any(keyword in transcript_lower for keyword in relationship_keywords):
            return AnalysisType.RELATIONSHIP
        
        # Trauma indicators
        trauma_keywords = ["trauma", "ptsd", "flashback", "nightmare", "abuse", "assault"]
        if any(keyword in transcript_lower for keyword in trauma_keywords):
            return AnalysisType.TRAUMA
        
        # Substance use indicators
        substance_keywords = ["alcohol", "drinking", "drugs", "substance", "addiction", "recovery"]
        if any(keyword in transcript_lower for keyword in substance_keywords):
            return AnalysisType.SUBSTANCE_USE
        
        # Work stress indicators
        work_keywords = ["work", "job", "career", "boss", "workplace", "stress", "burnout"]
        if any(keyword in transcript_lower for keyword in work_keywords):
            return AnalysisType.WORK_STRESS
        
        return AnalysisType.GENERAL
    
    def _generate_crisis_analysis(self, transcript: str) -> ClinicalAnalysis:
        """Generate crisis-focused analysis"""
        return ClinicalAnalysis(
            summary="Client presents with safety concerns and potential self-harm ideation requiring immediate intervention.",
            diagnosis="Crisis Intervention Required - Immediate Safety Assessment",
            key_points=[
                "Active safety concerns identified in session",
                "Immediate risk assessment needed",
                "Crisis intervention protocols required",
                "Urgent clinical attention necessary"
            ],
            treatment_plan=[
                "Crisis Assessment: Immediate safety evaluation and risk assessment",
                "Safety Planning: Develop comprehensive safety plan with emergency contacts",
                "Emergency Resources: Provide crisis hotline numbers and emergency services",
                "Immediate Follow-up: Schedule urgent follow-up within 24-48 hours",
                "Professional Consultation: Contact supervising clinician immediately"
            ],
            analysis_type=AnalysisType.CRISIS,
            confidence_score=0.95
        )
    
    def _generate_anxiety_analysis(self, transcript: str) -> ClinicalAnalysis:
        """Generate anxiety-focused analysis"""
        return ClinicalAnalysis(
            summary="Client reports anxiety-related symptoms impacting daily functioning and quality of life.",
            diagnosis="Anxiety Disorder - Comprehensive Assessment Recommended",
            key_points=[
                "Anxiety symptoms significantly impacting functioning",
                "Physical and emotional manifestations present",
                "Avoidance behaviors may be developing",
                "Coping strategies need enhancement"
            ],
            treatment_plan=[
                "Anxiety Assessment: Comprehensive evaluation using standardized anxiety measures",
                "Cognitive Behavioral Therapy: Weekly sessions focusing on thought restructuring",
                "Relaxation Training: Progressive muscle relaxation and breathing techniques",
                "Exposure Therapy: Gradual exposure to anxiety triggers when appropriate",
                "Lifestyle Interventions: Sleep hygiene and stress management techniques"
            ],
            analysis_type=AnalysisType.ANXIETY,
            confidence_score=0.80
        )
    
    def _generate_depression_analysis(self, transcript: str) -> ClinicalAnalysis:
        """Generate depression-focused analysis"""
        return ClinicalAnalysis(
            summary="Client presents with depressive symptoms affecting mood, energy, and daily activities.",
            diagnosis="Depressive Disorder - Clinical Evaluation Recommended",
            key_points=[
                "Persistent low mood and energy reported",
                "Impact on daily activities and relationships",
                "Negative thought patterns identified",
                "Sleep and appetite changes may be present"
            ],
            treatment_plan=[
                "Depression Screening: Administer PHQ-9 and assess symptom severity",
                "Behavioral Activation: Schedule pleasant activities and social engagement",
                "Cognitive Therapy: Address negative thought patterns and cognitive distortions",
                "Lifestyle Interventions: Sleep hygiene, exercise, and nutrition counseling",
                "Medical Evaluation: Consider referral for psychiatric assessment if indicated"
            ],
            analysis_type=AnalysisType.DEPRESSION,
            confidence_score=0.80
        )
    
    def _generate_relationship_analysis(self, transcript: str) -> ClinicalAnalysis:
        """Generate relationship-focused analysis"""
        return ClinicalAnalysis(
            summary="Client discusses relationship dynamics and interpersonal challenges requiring therapeutic support.",
            diagnosis="Relationship Issues - Couples or Family Therapy Indicated",
            key_points=[
                "Interpersonal conflicts affecting well-being",
                "Communication patterns need improvement",
                "Relationship satisfaction concerns",
                "Family dynamics impacting individual functioning"
            ],
            treatment_plan=[
                "Relationship Assessment: Evaluate communication patterns and conflict resolution",
                "Communication Skills: Teach active listening and assertiveness techniques",
                "Couples Therapy: Consider joint sessions if partner is willing to participate",
                "Boundary Setting: Develop healthy boundaries in relationships",
                "Family Systems Work: Address family dynamics and roles"
            ],
            analysis_type=AnalysisType.RELATIONSHIP,
            confidence_score=0.75
        )
    
    def _generate_trauma_analysis(self, transcript: str) -> ClinicalAnalysis:
        """Generate trauma-focused analysis"""
        return ClinicalAnalysis(
            summary="Client reports trauma-related symptoms requiring specialized trauma-informed treatment.",
            diagnosis="Trauma/PTSD - Specialized Assessment Recommended",
            key_points=[
                "Trauma history significantly impacting current functioning",
                "Re-experiencing symptoms may be present",
                "Avoidance and hypervigilance behaviors noted",
                "Specialized trauma treatment indicated"
            ],
            treatment_plan=[
                "Trauma Assessment: Comprehensive PTSD evaluation using PCL-5 or similar",
                "Trauma-Focused Therapy: Consider EMDR or Trauma-Focused CBT",
                "Stabilization: Grounding techniques and emotional regulation skills",
                "Safety Planning: Ensure current safety and develop coping strategies",
                "Specialized Referral: Connect with trauma-specialized therapist"
            ],
            analysis_type=AnalysisType.TRAUMA,
            confidence_score=0.85
        )
    
    def _generate_substance_analysis(self, transcript: str) -> ClinicalAnalysis:
        """Generate substance use focused analysis"""
        return ClinicalAnalysis(
            summary="Client discusses substance use concerns requiring assessment and potential treatment planning.",
            diagnosis="Substance Use Disorder - Comprehensive Evaluation Required",
            key_points=[
                "Substance use patterns affecting life functioning",
                "Potential dependency or abuse issues",
                "Impact on relationships and responsibilities",
                "Motivation for change assessment needed"
            ],
            treatment_plan=[
                "Substance Use Assessment: Comprehensive evaluation using AUDIT or DAST tools",
                "Motivational Interviewing: Explore readiness for change and treatment goals",
                "Relapse Prevention: Develop coping strategies and trigger identification",
                "Support Groups: Consider AA/NA or other peer support programs",
                "Medical Evaluation: Assess need for medical detox or medication support"
            ],
            analysis_type=AnalysisType.SUBSTANCE_USE,
            confidence_score=0.80
        )
    
    def _generate_work_stress_analysis(self, transcript: str) -> ClinicalAnalysis:
        """Generate work stress focused analysis"""
        return ClinicalAnalysis(
            summary="Client reports work-related stress and occupational challenges impacting overall well-being.",
            diagnosis="Occupational Stress - Adjustment Support Recommended",
            key_points=[
                "Work-related stressors affecting mental health",
                "Work-life balance challenges identified",
                "Occupational functioning concerns",
                "Stress management skills needed"
            ],
            treatment_plan=[
                "Stress Assessment: Evaluate sources and impact of occupational stress",
                "Stress Management: Teach time management and prioritization skills",
                "Boundary Setting: Develop healthy work-life boundaries",
                "Career Counseling: Explore career satisfaction and potential changes",
                "Workplace Interventions: Consider workplace accommodations if needed"
            ],
            analysis_type=AnalysisType.WORK_STRESS,
            confidence_score=0.75
        )
    
    def _generate_general_analysis(self, transcript: str) -> ClinicalAnalysis:
        """Generate general analysis"""
        return ClinicalAnalysis(
            summary="Client engaged in therapeutic discussion addressing personal concerns and seeking professional support.",
            diagnosis="General Adjustment - Comprehensive Assessment Pending",
            key_points=[
                "Client actively engaged in therapeutic process",
                "Multiple life stressors may be present",
                "Seeking professional guidance and support",
                "Motivation for positive change demonstrated"
            ],
            treatment_plan=[
                "Comprehensive Assessment: Complete biopsychosocial evaluation",
                "Goal Setting: Collaborate on specific therapeutic objectives",
                "Therapeutic Alliance: Establish strong working relationship",
                "Treatment Planning: Develop individualized intervention approach",
                "Regular Monitoring: Track progress and adjust treatment as needed"
            ],
            analysis_type=AnalysisType.GENERAL,
            confidence_score=0.70
        )


# Global service instance
analysis_service = ClinicalAnalysisService()
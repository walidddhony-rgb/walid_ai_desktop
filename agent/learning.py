"""
Auto-Learning Module - Enables Walid AI to learn automatically from every interaction.

Features:
- Automatic success/error detection
- Learning from tool usage patterns
- Skill improvement tracking
- Feedback integration
- Continuous self-improvement
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
import logging

from core.intelligence_enhancements import (
    get_enhancer,
    get_reflection_engine,
    get_compactor,
    IntelligenceEnhancer,
    SelfReflectionEngine,
    KnowledgeCompactor
)

logger = logging.getLogger(__name__)


@dataclass
class InteractionRecord:
    """Records a single interaction with the AI."""
    timestamp: str
    interaction_type: str  # 'chat', 'tool_use', 'code_execution', 'file_operation'
    user_input: str
    ai_response: str
    success: bool
    tools_used: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    user_feedback: Optional[str] = None


class AutoLearner:
    """
    Automatic learning system that learns from every AI interaction.
    
    Automatically:
    - Detects successes and failures
    - Extracts lessons from interactions
    - Updates skill profiles
    - Compacts old knowledge
    - Provides learning summaries
    """
    
    def __init__(self, learning_dir: str = "learning_data"):
        self.learning_dir = learning_dir
        self.enhancer: IntelligenceEnhancer = get_enhancer()
        self.reflection: SelfReflectionEngine = get_reflection_engine()
        self.compactor: KnowledgeCompactor = get_compactor()
        self.interactions: List[InteractionRecord] = []
        self._ensure_learning_dir()
        self._load_interactions()
    
    def _ensure_learning_dir(self):
        """Create learning directory if it doesn't exist."""
        os.makedirs(self.learning_dir, exist_ok=True)
    
    def _load_interactions(self):
        """Load previous interactions."""
        interactions_file = os.path.join(self.learning_dir, 'interactions.json')
        if os.path.exists(interactions_file):
            try:
                with open(interactions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.interactions = [InteractionRecord(**item) for item in data]
            except Exception as e:
                logger.warning(f"Could not load interactions: {e}")
    
    def _save_interactions(self):
        """Persist interactions to disk."""
        interactions_file = os.path.join(self.learning_dir, 'interactions.json')
        with open(interactions_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(i) for i in self.interactions], f, indent=2, ensure_ascii=False)
    
    def record_interaction(
        self,
        interaction_type: str,
        user_input: str,
        ai_response: str,
        success: bool,
        tools_used: List[str] = None,
        errors: List[str] = None,
        duration_ms: float = 0.0
    ):
        """
        Record an interaction and automatically learn from it.
        
        This is the main method called after every AI interaction.
        """
        record = InteractionRecord(
            timestamp=datetime.now().isoformat(),
            interaction_type=interaction_type,
            user_input=user_input,
            ai_response=ai_response,
            success=success,
            tools_used=tools_used or [],
            errors=errors or [],
            duration_ms=duration_ms
        )
        
        self.interactions.append(record)
        self._save_interactions()
        
        # Automatically learn from this interaction
        self._learn_from_interaction(record)
    
    def _learn_from_interaction(self, record: InteractionRecord):
        """Extract learning from an interaction."""
        
        # Learn from tool usage
        for tool in record.tools_used:
            self.enhancer.update_skill(
                skill_name=f"tool_{tool}",
                success=record.success,
                notes=f"Used in {record.interaction_type}"
            )
        
        # Learn from interaction type
        self.enhancer.update_skill(
            skill_name=f"interaction_{record.interaction_type}",
            success=record.success
        )
        
        # Record success or error
        if record.success:
            # Extract lesson from successful interaction
            lesson = self._extract_success_lesson(record)
            if lesson:
                self.enhancer.record_success(
                    description=f"Successful {record.interaction_type}",
                    lesson=lesson,
                    tags=[record.interaction_type, 'success'] + record.tools_used
                )
        else:
            # Record errors and corrections
            for error in record.errors:
                correction = self._suggest_correction(error, record)
                self.enhancer.record_error(
                    description=f"Error in {record.interaction_type}",
                    error_msg=error,
                    correction=correction or "Review and fix the error",
                    tags=[record.interaction_type, 'error']
                )
        
        # Compact knowledge periodically
        if len(self.interactions) % 50 == 0:
            self.enhancer.compact_knowledge(max_events=200)
    
    def _extract_success_lesson(self, record: InteractionRecord) -> str:
        """Extract a lesson from a successful interaction."""
        
        # Use reflection engine to analyze the successful response
        critique_prompt = self.reflection.generate_self_critique_prompt(record.ai_response)
        
        # Simple heuristic: what made this successful?
        lessons = []
        
        if record.tools_used:
            lessons.append(f"Effective tool usage: {', '.join(record.tools_used)}")
        
        if len(record.ai_response) > 100:
            lessons.append("Detailed responses improve user satisfaction")
        
        if record.duration_ms < 5000:
            lessons.append("Fast response time is good")
        
        return "; ".join(lessons) if lessons else "Successful interaction pattern"
    
    def _suggest_correction(self, error: str, record: InteractionRecord) -> str:
        """Suggest a correction for an error."""
        
        error_lower = error.lower()
        
        # Common error patterns and corrections
        if "module not found" in error_lower:
            return "Install missing module or check import statement"
        elif "syntax error" in error_lower:
            return "Review code syntax and fix the error"
        elif "permission denied" in error_lower:
            return "Check file permissions or run with appropriate privileges"
        elif "file not found" in error_lower:
            return "Verify file path exists before accessing"
        elif "timeout" in error_lower:
            return "Increase timeout or optimize the operation"
        elif "connection" in error_lower:
            return "Check network connection and retry"
        
        return "Review error message and fix the underlying issue"
    
    def add_user_feedback(self, interaction_index: int, feedback: str):
        """Add user feedback to a specific interaction."""
        if 0 <= interaction_index < len(self.interactions):
            self.interactions[interaction_index].user_feedback = feedback
            self._save_interactions()
            
            # Learn from feedback
            record = self.interactions[interaction_index]
            improvement = self._extract_improvement_from_feedback(feedback)
            
            self.enhancer.record_feedback(
                user_feedback=feedback,
                context=f"{record.interaction_type}: {record.user_input[:100]}",
                improvement=improvement
            )
    
    def _extract_improvement_from_feedback(self, feedback: str) -> str:
        """Extract improvement suggestion from user feedback."""
        
        feedback_lower = feedback.lower()
        
        if "good" in feedback_lower or "great" in feedback_lower:
            return "Continue current approach"
        elif "better" in feedback_lower:
            return "User suggested improvement"
        elif "wrong" in feedback_lower or "error" in feedback_lower:
            return "Fix the identified issue"
        elif "faster" in feedback_lower:
            return "Optimize for speed"
        elif "clearer" in feedback_lower or "explain" in feedback_lower:
            return "Improve explanation clarity"
        
        return "Incorporate user feedback"
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a comprehensive learning summary."""
        
        total_interactions = len(self.interactions)
        successful = sum(1 for i in self.interactions if i.success)
        success_rate = successful / total_interactions if total_interactions > 0 else 0
        
        # Most used tools
        tool_usage = {}
        for interaction in self.interactions:
            for tool in interaction.tools_used:
                tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        # Get enhancer summary
        enhancer_summary = self.enhancer.generate_learning_summary()
        
        return {
            'total_interactions': total_interactions,
            'success_rate': success_rate,
            'successful_interactions': successful,
            'failed_interactions': total_interactions - successful,
            'tool_usage': tool_usage,
            'learning_events': enhancer_summary,
            'recent_interactions': [asdict(i) for i in self.interactions[-10:]]
        }
    
    def get_similar_past_interactions(self, query: str, top_k: int = 5) -> List[InteractionRecord]:
        """Find similar past interactions based on query."""
        
        query_lower = query.lower()
        scored = []
        
        for i, interaction in enumerate(self.interactions):
            score = 0
            text = f"{interaction.user_input} {interaction.ai_response} {' '.join(interaction.tools_used)}".lower()
            
            for word in query_lower.split():
                if word in text:
                    score += 1
            
            if score > 0:
                scored.append((score, i, interaction))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [interaction for _, _, interaction in scored[:top_k]]
    
    def export_learning_data(self, output_file: str):
        """Export all learning data to a file."""
        
        data = {
            'interactions': [asdict(i) for i in self.interactions],
            'learning_events': [asdict(e) for e in self.enhancer.learning_events],
            'skill_profiles': {k: asdict(v) for k, v in self.enhancer.skill_profiles.items()},
            'summary': self.get_learning_summary()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported learning data to {output_file}")


# Singleton instance
_auto_learner_instance: Optional[AutoLearner] = None


def get_auto_learner() -> AutoLearner:
    """Get or create the auto-learner instance."""
    global _auto_learner_instance
    if _auto_learner_instance is None:
        _auto_learner_instance = AutoLearner()
    return _auto_learner_instance


def auto_learn(
    interaction_type: str,
    user_input: str,
    ai_response: str,
    success: bool,
    tools_used: List[str] = None,
    errors: List[str] = None,
    duration_ms: float = 0.0
):
    """
    Convenience function for automatic learning.
    
    Call this after every AI interaction to enable continuous learning.
    """
    learner = get_auto_learner()
    learner.record_interaction(
        interaction_type=interaction_type,
        user_input=user_input,
        ai_response=ai_response,
        success=success,
        tools_used=tools_used,
        errors=errors,
        duration_ms=duration_ms
    )

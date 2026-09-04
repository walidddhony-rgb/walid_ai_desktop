"""
Intelligence Enhancements Module - Makes Walid AI smarter and faster learner.

Features:
- Advanced reasoning patterns
- Self-reflection and error correction
- Learning from feedback
- Context optimization
- Knowledge compaction
- Skill acquisition tracking
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class LearningEvent:
    """Represents a learning event."""
    timestamp: str
    event_type: str  # 'success', 'error', 'feedback', 'optimization'
    description: str
    lesson_learned: str
    confidence_score: float = 1.0
    tags: List[str] = field(default_factory=list)


@dataclass
class SkillProfile:
    """Tracks skill acquisition and proficiency."""
    skill_name: str
    proficiency_level: float = 0.0  # 0.0 to 1.0
    last_used: str = ""
    usage_count: int = 0
    success_rate: float = 1.0
    notes: str = ""


class IntelligenceEnhancer:
    """
    Main class for enhancing AI intelligence and learning capabilities.
    
    Implements:
    - Self-reflection patterns
    - Error analysis and correction
    - Knowledge compaction
    - Adaptive learning
    - Performance optimization
    """
    
    def __init__(self, learning_dir: str = "learning_data"):
        self.learning_dir = learning_dir
        self.learning_events: List[LearningEvent] = []
        self.skill_profiles: Dict[str, SkillProfile] = {}
        self._ensure_learning_dir()
        self._load_learning_data()
    
    def _ensure_learning_dir(self):
        """Create learning directory if it doesn't exist."""
        os.makedirs(self.learning_dir, exist_ok=True)
    
    def _load_learning_data(self):
        """Load previously learned data."""
        events_file = os.path.join(self.learning_dir, 'learning_events.json')
        skills_file = os.path.join(self.learning_dir, 'skill_profiles.json')
        
        if os.path.exists(events_file):
            try:
                with open(events_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.learning_events = [LearningEvent(**item) for item in data]
            except Exception:
                pass
        
        if os.path.exists(skills_file):
            try:
                with open(skills_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.skill_profiles = {k: SkillProfile(**v) for k, v in data.items()}
            except Exception:
                pass
    
    def _save_learning_data(self):
        """Persist learning data to disk."""
        events_file = os.path.join(self.learning_dir, 'learning_events.json')
        skills_file = os.path.join(self.learning_dir, 'skill_profiles.json')
        
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(e) for e in self.learning_events], f, indent=2, ensure_ascii=False)
        
        with open(skills_file, 'w', encoding='utf-8') as f:
            json.dump({k: asdict(v) for k, v in self.skill_profiles.items()}, f, indent=2, ensure_ascii=False)
    
    def record_success(self, description: str, lesson: str, tags: List[str] = None):
        """Record a successful operation and extract learning."""
        event = LearningEvent(
            timestamp=datetime.now().isoformat(),
            event_type='success',
            description=description,
            lesson_learned=lesson,
            confidence_score=1.0,
            tags=tags or []
        )
        self.learning_events.append(event)
        self._save_learning_data()
    
    def record_error(self, description: str, error_msg: str, correction: str, tags: List[str] = None):
        """Record an error and its correction for future learning."""
        lesson = f"Error: {error_msg}. Correction: {correction}"
        event = LearningEvent(
            timestamp=datetime.now().isoformat(),
            event_type='error',
            description=description,
            lesson_learned=lesson,
            confidence_score=0.8,
            tags=tags or ['error', 'correction']
        )
        self.learning_events.append(event)
        self._save_learning_data()
    
    def record_feedback(self, user_feedback: str, context: str, improvement: str):
        """Learn from user feedback."""
        event = LearningEvent(
            timestamp=datetime.now().isoformat(),
            event_type='feedback',
            description=context,
            lesson_learned=f"User feedback: {user_feedback}. Improvement: {improvement}",
            confidence_score=0.9,
            tags=['feedback', 'improvement']
        )
        self.learning_events.append(event)
        self._save_learning_data()
    
    def update_skill(self, skill_name: str, success: bool = True, notes: str = ""):
        """Update skill profile based on usage."""
        if skill_name not in self.skill_profiles:
            self.skill_profiles[skill_name] = SkillProfile(
                skill_name=skill_name,
                last_used=datetime.now().isoformat()
            )
        
        profile = self.skill_profiles[skill_name]
        profile.usage_count += 1
        profile.last_used = datetime.now().isoformat()
        
        # Update success rate
        if success:
            profile.success_rate = (profile.success_rate * (profile.usage_count - 1) + 1.0) / profile.usage_count
            profile.proficiency_level = min(1.0, profile.proficiency_level + 0.05)
        else:
            profile.success_rate = (profile.success_rate * (profile.usage_count - 1) + 0.0) / profile.usage_count
            profile.proficiency_level = max(0.0, profile.proficiency_level - 0.02)
        
        if notes:
            profile.notes = notes
        
        self._save_learning_data()
    
    def get_similar_lessons(self, query: str, top_k: int = 5) -> List[LearningEvent]:
        """Find similar past lessons based on query."""
        query_lower = query.lower()
        scored_events = []
        
        for event in self.learning_events:
            score = 0
            text_to_search = f"{event.description} {event.lesson_learned} {' '.join(event.tags)}".lower()
            
            # Simple keyword matching
            for word in query_lower.split():
                if word in text_to_search:
                    score += 1
            
            if score > 0:
                scored_events.append((score, event))
        
        # Sort by score and return top_k
        scored_events.sort(key=lambda x: x[0], reverse=True)
        return [event for _, event in scored_events[:top_k]]
    
    def generate_learning_summary(self) -> Dict[str, Any]:
        """Generate a summary of all learning."""
        total_events = len(self.learning_events)
        
        event_types = {}
        for event in self.learning_events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        
        top_skills = sorted(
            self.skill_profiles.values(),
            key=lambda x: x.proficiency_level,
            reverse=True
        )[:10]
        
        return {
            'total_learning_events': total_events,
            'event_breakdown': event_types,
            'top_skills': [asdict(s) for s in top_skills],
            'recent_lessons': [asdict(e) for e in self.learning_events[-10:]]
        }
    
    def compact_knowledge(self, max_events: int = 100):
        """Compact old learning events to save space while retaining important lessons."""
        if len(self.learning_events) <= max_events:
            return
        
        # Keep most recent and highest confidence events
        sorted_events = sorted(
            self.learning_events,
            key=lambda x: (x.confidence_score, x.timestamp),
            reverse=True
        )
        
        # Keep top events
        self.learning_events = sorted_events[:max_events]
        self._save_learning_data()


class SelfReflectionEngine:
    """
    Implements self-reflection patterns for better reasoning.
    
    Techniques:
    - Chain of Thought (CoT)
    - Tree of Thoughts (ToT)
    - Self-critique
    - Error detection
    """
    
    @staticmethod
    def generate_cot_prompt(task: str) -> str:
        """Generate Chain of Thought prompt."""
        return f"""Let's think step by step to solve this problem:

Task: {task}

Step 1: Understand the problem
- What is being asked?
- What are the constraints?
- What information do I have?

Step 2: Break down the problem
- What are the sub-problems?
- What approach should I take?

Step 3: Execute the solution
- Implement each step carefully
- Check for errors at each step

Step 4: Verify the solution
- Does the answer make sense?
- Are there edge cases I missed?
- Can I optimize anything?

Now let's solve it:"""
    
    @staticmethod
    def generate_self_critique_prompt(response: str) -> str:
        """Generate self-critique prompt to improve response quality."""
        return f"""Please critically review this response:

{response}

Critique checklist:
1. Is the answer complete and accurate?
2. Are there any logical errors or inconsistencies?
3. Did I miss any important edge cases?
4. Is the explanation clear and easy to understand?
5. Could the solution be more efficient or elegant?
6. Are there any assumptions I made that might be wrong?
7. Did I address all parts of the original question?

Please identify any issues and suggest improvements:"""
    
    @staticmethod
    def generate_tot_prompts(task: str, n_branches: int = 3) -> List[str]:
        """Generate Tree of Thoughts prompts for exploring multiple approaches."""
        prompts = []
        
        approaches = [
            "conservative",
            "creative",
            "analytical",
            "practical",
            "theoretical"
        ]
        
        for i in range(min(n_branches, len(approaches))):
            prompts.append(f"""Approach this problem from a {approaches[i]} perspective:

Task: {task}

Consider:
- What would a {approaches[i]} approach look like?
- What are the strengths of this approach?
- What are the potential pitfalls?
- How does this compare to other approaches?

Develop your solution:""")
        
        return prompts


class KnowledgeCompactor:
    """
    Compacts and optimizes knowledge for efficient storage and retrieval.
    
    Features:
    - Summarization
    - Deduplication
    - Importance scoring
    - Hierarchical organization
    """
    
    def __init__(self):
        self.knowledge_base: Dict[str, Any] = {}
    
    def add_knowledge(self, key: str, value: Any, importance: float = 1.0):
        """Add knowledge with importance scoring."""
        self.knowledge_base[key] = {
            'value': value,
            'importance': importance,
            'access_count': 0,
            'last_accessed': datetime.now().isoformat()
        }
    
    def get_knowledge(self, key: str) -> Optional[Any]:
        """Retrieve knowledge and update access stats."""
        if key in self.knowledge_base:
            self.knowledge_base[key]['access_count'] += 1
            self.knowledge_base[key]['last_accessed'] = datetime.now().isoformat()
            return self.knowledge_base[key]['value']
        return None
    
    def compact(self, max_entries: int = 1000):
        """Remove low-importance, low-access knowledge."""
        if len(self.knowledge_base) <= max_entries:
            return
        
        # Score each entry
        scored = []
        for key, data in self.knowledge_base.items():
            score = (data['importance'] * 0.6 + 
                    min(1.0, data['access_count'] / 10) * 0.4)
            scored.append((score, key))
        
        # Keep top entries
        scored.sort(key=lambda x: x[0], reverse=True)
        keys_to_keep = {key for _, key in scored[:max_entries]}
        
        self.knowledge_base = {
            k: v for k, v in self.knowledge_base.items() if k in keys_to_keep
        }


# Singleton instance for easy access
_enhancer_instance: Optional[IntelligenceEnhancer] = None
_reflection_engine: Optional[SelfReflectionEngine] = None
_compactor: Optional[KnowledgeCompactor] = None


def get_enhancer() -> IntelligenceEnhancer:
    """Get or create the intelligence enhancer instance."""
    global _enhancer_instance
    if _enhancer_instance is None:
        _enhancer_instance = IntelligenceEnhancer()
    return _enhancer_instance


def get_reflection_engine() -> SelfReflectionEngine:
    """Get or create the self-reflection engine instance."""
    global _reflection_engine
    if _reflection_engine is None:
        _reflection_engine = SelfReflectionEngine()
    return _reflection_engine


def get_compactor() -> KnowledgeCompactor:
    """Get or create the knowledge compactor instance."""
    global _compactor
    if _compactor is None:
        _compactor = KnowledgeCompactor()
    return _compactor

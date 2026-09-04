"""
Walid AI Worker - Enhanced with intelligence improvements and auto-learning.

This module handles the main AI processing loop with:
- Enhanced prompts (CoT, self-reflection)
- Automatic learning from interactions
- Skill tracking and improvement
"""

import time
import logging
from typing import List, Dict, Any, Optional

from litellm import completion

from core.config import Config
from core.session import SessionManager
from core.skills import SkillContext
from core.hooks import Hooks
from core.code_executor import CodeExecutor
from core.context_compaction import ContextCompactor
from core.exceptions import WalidAIException

# Intelligence enhancements imports
from core.intelligence_enhancements import get_enhancer, get_reflection_engine
from agent.learning import auto_learn, get_auto_learner
from agent.prompts import SYSTEM_PROMPT_ENHANCED, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class Worker:
    """
    Main AI worker with enhanced intelligence and auto-learning capabilities.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.session_manager = SessionManager()
        self.skill_context = SkillContext()
        self.hooks = Hooks()
        self.code_executor = CodeExecutor()
        self.context_compactor = ContextCompactor()
        
        # Initialize intelligence enhancements
        self.enhancer = get_enhancer()
        self.reflection_engine = get_reflection_engine()
        self.auto_learner = get_auto_learner()
        
        # Use enhanced system prompt
        self.system_prompt = SYSTEM_PROMPT_ENHANCED
        
        logger.info("Worker initialized with intelligence enhancements")
    
    def process(
        self,
        user_input: str,
        session_id: str = "default",
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process user input with enhanced intelligence and auto-learning.
        
        Args:
            user_input: The user's message
            session_id: Session identifier
            stream: Whether to stream the response
            **kwargs: Additional arguments
            
        Returns:
            Dictionary containing the AI response and metadata
        """
        start_time = time.time()
        tools_used = []
        errors = []
        
        try:
            # Get or create session
            session = self.session_manager.get_session(session_id)
            
            # Build messages with enhanced system prompt
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add conversation history
            messages.extend(session.get_messages())
            
            # Add current user message
            messages.append({"role": "user", "content": user_input})
            
            # Call LLM with enhanced prompt
            response = completion(
                model=self.config.model,
                messages=messages,
                stream=stream,
                **self.config.get_completion_kwargs()
            )
            
            # Extract AI response
            if stream:
                ai_response = self._handle_stream(response)
            else:
                ai_response = response.choices[0].message.content
            
            # Track tool usage (if any tools were called)
            # This would be extracted from the response or tool calls
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Add to session history
            session.add_message("user", user_input)
            session.add_message("assistant", ai_response)
            
            # Auto-learn from this successful interaction
            auto_learn(
                interaction_type='chat',
                user_input=user_input,
                ai_response=ai_response[:500],  # Truncate for storage
                success=True,
                tools_used=tools_used,
                errors=errors,
                duration_ms=duration_ms
            )
            
            # Update skills
            if tools_used:
                for tool in tools_used:
                    self.enhancer.update_skill(f"tool_{tool}", success=True)
            
            logger.info(f"Successfully processed input in {duration_ms:.2f}ms")
            
            return {
                "success": True,
                "response": ai_response,
                "session_id": session_id,
                "duration_ms": duration_ms,
                "tools_used": tools_used,
                "model": self.config.model
            }
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            errors.append(error_msg)
            
            logger.error(f"Error processing input: {error_msg}")
            
            # Auto-learn from this error
            auto_learn(
                interaction_type='chat',
                user_input=user_input,
                ai_response=f"Error: {error_msg}",
                success=False,
                tools_used=tools_used,
                errors=errors,
                duration_ms=duration_ms
            )
            
            # Update skills with failure
            if tools_used:
                for tool in tools_used:
                    self.enhancer.update_skill(f"tool_{tool}", success=False)
            
            return {
                "success": False,
                "error": error_msg,
                "session_id": session_id,
                "duration_ms": duration_ms
            }
    
    def _handle_stream(self, response) -> str:
        """Handle streaming response."""
        chunks = []
        for chunk in response:
            if chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)
        return "".join(chunks)
    
    def execute_code(
        self,
        code: str,
        language: str = "python",
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Execute code with auto-learning.
        
        Args:
            code: Code to execute
            language: Programming language
            session_id: Session identifier
            
        Returns:
            Execution result
        """
        start_time = time.time()
        
        try:
            # Execute the code
            result = self.code_executor.execute(code, language)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Auto-learn from successful execution
            auto_learn(
                interaction_type='code_execution',
                user_input=f"Execute {language} code",
                ai_response=f"Code executed successfully: {result.get('output', '')[:200]}",
                success=True,
                tools_used=['code_executor'],
                errors=[],
                duration_ms=duration_ms
            )
            
            # Update skill
            self.enhancer.update_skill(f"code_{language}", success=True)
            
            return {
                "success": True,
                "result": result,
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            # Auto-learn from error
            auto_learn(
                interaction_type='code_execution',
                user_input=f"Execute {language} code",
                ai_response=f"Error: {error_msg}",
                success=False,
                tools_used=['code_executor'],
                errors=[error_msg],
                duration_ms=duration_ms
            )
            
            # Update skill with failure
            self.enhancer.update_skill(f"code_{language}", success=False)
            
            return {
                "success": False,
                "error": error_msg,
                "duration_ms": duration_ms
            }
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of all learning."""
        return self.auto_learner.get_learning_summary()
    
    def get_skill_summary(self) -> Dict[str, Any]:
        """Get skill proficiency summary."""
        return self.enhancer.generate_learning_summary()

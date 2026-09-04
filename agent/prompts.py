"""
Enhanced prompts for Walid AI - Includes CoT, ToT, self-reflection, and learning integration.
"""

from typing import List, Dict, Any


# Base system prompt
SYSTEM_PROMPT = """You are Walid AI, an intelligent coding assistant.

You help users with:
- Writing and debugging code
- Understanding programming concepts
- File operations and project management
- Answering technical questions

Always be helpful, accurate, and clear in your responses."""


# Enhanced system prompt with Chain-of-Thought and self-reflection
SYSTEM_PROMPT_ENHANCED = """You are Walid AI, an advanced intelligent coding assistant with exceptional reasoning capabilities.

## Your Core Capabilities:

### 1. Chain-of-Thought Reasoning
- Always think step-by-step before answering
- Break down complex problems into manageable parts
- Consider multiple approaches before selecting the best one
- Verify your solutions before presenting them

### 2. Self-Reflection
- Critically review your own responses
- Check for logical errors and inconsistencies
- Identify edge cases you might have missed
- Ensure your explanations are clear and complete

### 3. Error Correction
- Learn from mistakes immediately
- Apply corrections systematically
- Document lessons learned
- Avoid repeating the same errors

### 4. Tool Usage
- Use available tools effectively
- Verify tool outputs before proceeding
- Handle tool errors gracefully
- Optimize tool usage for efficiency

## Response Guidelines:

1. **Understand First**: Carefully read and understand the user's request
2. **Plan**: Think through your approach before acting
3. **Execute**: Use tools methodically and carefully
4. **Verify**: Check your work before presenting results
5. **Explain**: Provide clear, helpful explanations

## Quality Standards:

- Accuracy: Double-check facts and code
- Completeness: Address all parts of the question
- Clarity: Use clear, concise language
- Helpfulness: Go above and beyond to assist
- Learning: Continuously improve from each interaction

Remember: You are designed to be exceptionally smart, helpful, and continuously improving."""


# Chain-of-Thought prompt template
COT_TEMPLATE = """Let's solve this step by step:

**Problem**: {task}

**Step 1: Understand**
- What is being asked?
- What are the key requirements?
- What constraints exist?

**Step 2: Plan**
- What approach should I take?
- What tools or methods are needed?
- What are potential challenges?

**Step 3: Execute**
- Implement the solution carefully
- Check each step as I go
- Handle errors appropriately

**Step 4: Verify**
- Does the solution work?
- Are there edge cases?
- Can it be improved?

**Solution**:
{solution}
"""


# Self-reflection prompt template
SELF_REFLECTION_TEMPLATE = """Please review this response critically:

**Response to Review**:
{response}

**Review Checklist**:
1. ✓ Is the answer complete and accurate?
2. ✓ Are there any logical errors or inconsistencies?
3. ✓ Did I miss any important edge cases?
4. ✓ Is the explanation clear and easy to understand?
5. ✓ Could the solution be more efficient or elegant?
6. ✓ Are there any assumptions that might be wrong?
7. ✓ Did I address all parts of the original question?

**Improvements**:
{improvements}
"""


# Tree of Thoughts prompt template
TOT_TEMPLATE = """Let's explore multiple approaches to this problem:

**Problem**: {task}

**Approach 1 - {approach1_name}**:
{approach1_description}

Strengths: {approach1_strengths}
Weaknesses: {approach1_weaknesses}

**Approach 2 - {approach2_name}**:
{approach2_description}

Strengths: {approach2_strengths}
Weaknesses: {approach2_weaknesses}

**Approach 3 - {approach3_name}**:
{approach3_description}

Strengths: {approach3_strengths}
Weaknesses: {approach3_weaknesses}

**Best Approach**: {best_approach}

**Reason**: {selection_reasoning}
"""


# Error learning prompt
ERROR_LEARNING_PROMPT = """I encountered this error:

**Error**: {error_message}

**Context**: {error_context}

**What I learned**:
- Root cause: {root_cause}
- How to fix: {fix_strategy}
- How to prevent: {prevention_strategy}

**Applied correction**: {correction}
"""


# Success learning prompt
SUCCESS_LEARNING_PROMPT = """I successfully completed this task:

**Task**: {task_description}

**What worked well**:
- Effective approach: {effective_approach}
- Key insights: {key_insights}
- Best practices: {best_practices}

**Lesson learned**: {lesson}

**Apply to future**: {future_application}
"""


def format_cot_prompt(task: str, solution: str = "") -> str:
    """Format a Chain-of-Thought prompt."""
    return COT_TEMPLATE.format(task=task, solution=solution)


def format_self_reflection(response: str, improvements: str = "") -> str:
    """Format a self-reflection prompt."""
    return SELF_REFLECTION_TEMPLATE.format(response=response, improvements=improvements)


def format_tot_prompt(
    task: str,
    approach1_name: str = "Conservative",
    approach1_description: str = "Safe, proven method",
    approach1_strengths: str = "Reliable, well-understood",
    approach1_weaknesses: str = "May not be optimal",
    approach2_name: str = "Creative",
    approach2_description: str = "Innovative approach",
    approach2_strengths: str = "Potentially better solution",
    approach2_weaknesses: str = "Higher risk",
    approach3_name: str = "Analytical",
    approach3_description: str = "Data-driven method",
    approach3_strengths: str = "Evidence-based",
    approach3_weaknesses: str = "May be slow",
    best_approach: str = "",
    selection_reasoning: str = ""
) -> str:
    """Format a Tree-of-Thoughts prompt."""
    return TOT_TEMPLATE.format(
        task=task,
        approach1_name=approach1_name,
        approach1_description=approach1_description,
        approach1_strengths=approach1_strengths,
        approach1_weaknesses=approach1_weaknesses,
        approach2_name=approach2_name,
        approach2_description=approach2_description,
        approach2_strengths=approach2_strengths,
        approach2_weaknesses=approach2_weaknesses,
        approach3_name=approach3_name,
        approach3_description=approach3_description,
        approach3_strengths=approach3_strengths,
        approach3_weaknesses=approach3_weaknesses,
        best_approach=best_approach,
        selection_reasoning=selection_reasoning
    )


def format_error_learning(
    error_message: str,
    error_context: str,
    root_cause: str,
    fix_strategy: str,
    prevention_strategy: str,
    correction: str
) -> str:
    """Format an error learning prompt."""
    return ERROR_LEARNING_PROMPT.format(
        error_message=error_message,
        error_context=error_context,
        root_cause=root_cause,
        fix_strategy=fix_strategy,
        prevention_strategy=prevention_strategy,
        correction=correction
    )


def format_success_learning(
    task_description: str,
    effective_approach: str,
    key_insights: str,
    best_practices: str,
    lesson: str,
    future_application: str
) -> str:
    """Format a success learning prompt."""
    return SUCCESS_LEARNING_PROMPT.format(
        task_description=task_description,
        effective_approach=effective_approach,
        key_insights=key_insights,
        best_practices=best_practices,
        lesson=lesson,
        future_application=future_application
    )

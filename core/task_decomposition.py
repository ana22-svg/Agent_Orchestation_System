"""
Task decomposition engine for breaking down complex requests into subtasks.

Converts a high-level request into an ordered, structured plan with:
- Subtasks with descriptions, required inputs, expected outputs
- Dependencies between subtasks
- Specialist assignments (which agent should execute each)
- Execution flow (parallel or sequential)
- Estimated complexity and priority
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import json
from pydantic import BaseModel, Field


class ExecutionMode(str, Enum):
    """How subtasks should be executed relative to each other."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MIXED = "mixed"  # Some parallel, some sequential


class Complexity(str, Enum):
    """Estimated complexity level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Subtask(BaseModel):
    """A single task in the decomposed plan."""
    id: str
    description: str
    specialist_type: str  # research, data_analysis, writing, code_execution
    required_inputs: list[str] = Field(default_factory=list)  # IDs of tasks this depends on
    expected_output_format: dict = Field(default_factory=dict)  # Schema for output
    estimated_complexity: Complexity = Complexity.MEDIUM
    priority: int = Field(default=0, ge=0, le=10)  # 0-10, higher = more important
    estimated_tokens: int = 0
    retry_count: int = 0
    max_retries: int = 2


class TaskPlan(BaseModel):
    """A complete decomposed plan for a request."""
    request_id: str
    original_request: str
    subtasks: list[Subtask]
    execution_flow: list[list[str]]  # Groups of task IDs to execute together
    execution_mode: ExecutionMode
    total_estimated_complexity: Complexity
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)  # Plan quality confidence
    notes: str = ""


class TaskDecompositionEngine:
    """
    Decomposes complex requests into structured task plans.
    
    Uses LLM to:
    1. Understand the request
    2. Identify required steps and dependencies
    3. Assign to appropriate specialists
    4. Structure into a valid plan
    
    Includes validation to ensure:
    - Plan passes schema validation on first try
    - No circular dependencies
    - All required inputs are available
    """

    def __init__(self, model_name: str = "gpt-4"):
        self.model_name = model_name

    async def decompose(self, request: str, context_facts: Optional[dict] = None) -> dict:
        """
        Decompose a complex request into a structured task plan.
        
        Args:
            request: The high-level task request
            context_facts: Optional domain facts or user preferences to consider
            
        Returns:
            TaskPlan as dictionary with validated structure
        """
        from langchain_openai import ChatOpenAI
        from langchain.output_parsers import PydanticOutputParser
        
        llm = ChatOpenAI(model_name=self.model_name, temperature=0)
        parser = PydanticOutputParser(pydantic_object=TaskPlan)
        
        # Build the decomposition prompt
        prompt = self._build_decomposition_prompt(request, context_facts, parser)
        
        # Attempt decomposition with retry logic
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = await self._call_llm(llm, prompt)
                plan = self._validate_plan(response, parser)
                return plan.model_dump()
            except ValueError as e:
                if attempt < max_attempts - 1:
                    # Retry with feedback
                    prompt = self._rebuild_prompt_with_feedback(prompt, str(e))
                else:
                    # Failed all retries, return fallback plan
                    return self._create_fallback_plan(request)
    
    def _build_decomposition_prompt(self, request: str, context_facts: Optional[dict], parser) -> str:
        """Build the LLM prompt for task decomposition."""
        context_str = ""
        if context_facts:
            context_str = "\n\nDomain Context and Facts:\n" + json.dumps(context_facts, indent=2)
        
        specialist_options = [
            "research - for information gathering, web search, document retrieval",
            "data_analysis - for data processing, statistical analysis, SQL queries",
            "writing - for content generation, editing, synthesis",
            "code_execution - for Python code execution, testing, automation",
        ]
        
        prompt = f"""You are a task planning expert. Break down the following complex request into a structured task plan.

REQUEST:
{request}
{context_str}

INSTRUCTIONS:
1. Identify all subtasks needed to complete the request
2. Determine dependencies between subtasks (what must happen first)
3. Assign each subtask to the most appropriate specialist:
   {chr(10).join(f"   - {opt}" for opt in specialist_options)}
4. Define the expected output format for each subtask
5. Estimate complexity (low/medium/high)
6. Determine if tasks can run in parallel or must be sequential

OUTPUT FORMAT:
Respond with ONLY a valid JSON object matching this schema:
{parser.get_format_instructions()}

SCHEMA:
- request_id: unique identifier (use hash of request)
- original_request: the full request text
- subtasks: array of subtask objects, each with:
  - id: unique task identifier (task_1, task_2, etc.)
  - description: what this subtask does
  - specialist_type: one of the specialist options above
  - required_inputs: list of task IDs this depends on (empty if none)
  - expected_output_format: JSON schema for the output
  - estimated_complexity: low/medium/high
  - priority: 0-10 (10 = most important)
- execution_flow: list of lists showing execution order [[task_1, task_2], [task_3]]
- execution_mode: sequential/parallel/mixed
- total_estimated_complexity: low/medium/high
- confidence: 0.0-1.0 (how confident is this plan?)
- notes: any caveats or special instructions

Ensure:
- No circular dependencies
- All required_inputs reference existing task IDs
- JSON is valid and properly formatted
- Schema matches exactly"""
        
        return prompt
    
    async def _call_llm(self, llm, prompt: str) -> str:
        """Call the LLM with the decomposition prompt."""
        response = await llm.ainvoke({"text": prompt})
        return response.content
    
    def _validate_plan(self, response_text: str, parser) -> TaskPlan:
        """Validate and parse the plan from LLM response."""
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON object found in response")
        
        json_str = json_match.group()
        plan_dict = json.loads(json_str)
        
        # Validate against schema
        plan = TaskPlan(**plan_dict)
        
        # Check for circular dependencies
        self._check_circular_dependencies(plan)
        
        # Validate all required inputs reference existing tasks
        self._validate_task_references(plan)
        
        return plan
    
    def _check_circular_dependencies(self, plan: TaskPlan) -> None:
        """Verify no circular dependencies exist in the plan."""
        task_ids = {t.id for t in plan.subtasks}
        
        def has_cycle(task_id, visited, rec_stack, graph):
            visited.add(task_id)
            rec_stack.add(task_id)
            
            for neighbor in graph.get(task_id, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack, graph):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        # Build dependency graph
        graph = {t.id: t.required_inputs for t in plan.subtasks}
        
        visited = set()
        for task_id in graph:
            if task_id not in visited:
                if has_cycle(task_id, visited, set(), graph):
                    raise ValueError(f"Circular dependency detected in task plan")
    
    def _validate_task_references(self, plan: TaskPlan) -> None:
        """Verify all required_inputs reference existing tasks."""
        task_ids = {t.id for t in plan.subtasks}
        
        for task in plan.subtasks:
            for required_id in task.required_inputs:
                if required_id not in task_ids:
                    raise ValueError(f"Task {task.id} requires non-existent task {required_id}")
    
    def _rebuild_prompt_with_feedback(self, original_prompt: str, error: str) -> str:
        """Rebuild prompt with feedback about what went wrong."""
        feedback = f"\n\nPREVIOUS ATTEMPT FAILED: {error}\nPlease ensure your JSON is valid and matches the exact schema."
        return original_prompt + feedback
    
    def _create_fallback_plan(self, request: str) -> dict:
        """Create a simple fallback plan if decomposition fails."""
        return {
            "request_id": hash(request) % 10000,
            "original_request": request,
            "subtasks": [
                {
                    "id": "task_1",
                    "description": request,
                    "specialist_type": "general",
                    "required_inputs": [],
                    "expected_output_format": {"type": "object"},
                    "estimated_complexity": "medium",
                    "priority": 5,
                    "estimated_tokens": 2000,
                    "retry_count": 0,
                    "max_retries": 2,
                }
            ],
            "execution_flow": [["task_1"]],
            "execution_mode": "sequential",
            "total_estimated_complexity": "medium",
            "confidence": 0.5,
            "notes": "Fallback plan - decomposition failed, treating request as single task",
        }

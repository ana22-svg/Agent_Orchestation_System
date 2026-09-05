"""
Core agent definitions for the Agent Orchestration System.

Three-layer hierarchy:
- Supervisor: Plans and delegates tasks
- Specialists: Domain-specific agents that execute tasks using tools
- Reviewer: Validates specialist output before synthesis
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from datetime import datetime


class SpecialistType(str, Enum):
    """Types of specialist agents."""
    RESEARCH = "research"
    DATA_ANALYSIS = "data_analysis"
    WRITING = "writing"
    CODE_EXECUTION = "code_execution"
    GENERAL = "general"


@dataclass
class AgentDecision:
    """Record of a decision made by an agent."""
    agent_id: str
    agent_type: str
    timestamp: datetime
    reasoning: str
    action: str
    tool_calls: list[dict] = field(default_factory=list)
    output: Optional[Any] = None
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class AgentContext:
    """Context shared across agents during execution."""
    task_id: str
    original_request: str
    plan: Optional[dict] = None
    completed_subtasks: dict[str, Any] = field(default_factory=dict)
    current_subtask: Optional[str] = None
    decisions: list[AgentDecision] = field(default_factory=list)
    error_log: list[dict] = field(default_factory=list)


class Agent(ABC):
    """Base agent class."""

    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type

    @abstractmethod
    async def execute(self, context: AgentContext, **kwargs) -> AgentDecision:
        """Execute the agent's primary function."""
        pass

    def _record_decision(
        self,
        context: AgentContext,
        reasoning: str,
        action: str,
        output: Optional[Any] = None,
        confidence: float = 1.0,
        tool_calls: Optional[list[dict]] = None,
    ) -> AgentDecision:
        """Record an agent decision in context."""
        decision = AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            timestamp=datetime.now(),
            reasoning=reasoning,
            action=action,
            tool_calls=tool_calls or [],
            output=output,
            confidence=confidence,
        )
        context.decisions.append(decision)
        return decision


class Supervisor(Agent):
    """
    Supervisor agent: plans tasks and delegates to specialists.
    
    Responsibilities:
    - Decompose complex requests into subtasks
    - Assign subtasks to appropriate specialists
    - Define task dependencies
    - Route execution flow
    """

    def __init__(self, model_name: str = "gpt-4"):
        super().__init__("supervisor_1", "supervisor")
        self.model_name = model_name

    async def execute(self, context: AgentContext, **kwargs) -> AgentDecision:
        """
        Create a task plan from the original request.
        
        Returns a structured plan with:
        - subtasks: list of tasks to execute
        - dependencies: task dependencies
        - assigned_specialists: which specialist handles each task
        - execution_order: parallel or sequential execution
        """
        from .task_decomposition import TaskDecompositionEngine
        
        decomposer = TaskDecompositionEngine(self.model_name)
        plan = await decomposer.decompose(context.original_request)
        
        reasoning = f"Decomposed complex request into {len(plan['subtasks'])} subtasks with dependencies"
        
        decision = self._record_decision(
            context=context,
            reasoning=reasoning,
            action="create_plan",
            output=plan,
            confidence=plan.get("confidence", 0.8),
        )
        
        context.plan = plan
        return decision


class Specialist(Agent):
    """
    Base specialist agent: executes domain-specific tasks using tools.
    
    Subtypes handle:
    - research: web search, document retrieval, information gathering
    - data_analysis: SQL queries, data processing, statistical analysis
    - writing: content generation, editing, synthesis
    - code_execution: Python code execution, testing
    """

    def __init__(self, specialist_type: SpecialistType, model_name: str = "gpt-4"):
        super().__init__(f"{specialist_type.value}_specialist", specialist_type.value)
        self.specialist_type = specialist_type
        self.model_name = model_name

    async def execute(self, context: AgentContext, subtask: dict, **kwargs) -> AgentDecision:
        """
        Execute a subtask using appropriate tools.
        
        Args:
            context: Shared execution context
            subtask: The specific subtask to execute
                - description: what to do
                - required_inputs: what data/context is needed
                - expected_output_format: structured output spec
        """
        from .tool_registry import ToolRegistry
        from langchain_openai import ChatOpenAI
        from langchain.agents import AgentExecutor, create_openai_functions_agent
        from langchain import hub
        
        context.current_subtask = subtask.get("id", "unknown")
        
        # Get available tools for this specialist type
        tool_registry = ToolRegistry.get_instance()
        available_tools = tool_registry.get_tools_for_specialist(self.specialist_type.value)
        
        # Initialize LLM
        llm = ChatOpenAI(model_name=self.model_name, temperature=0)
        
        # Create agent (for now, simplified version)
        reasoning = f"Executing subtask: {subtask.get('description', 'unknown')}"
        action = f"execute_subtask[{context.current_subtask}]"
        
        # Placeholder for actual tool-using agent execution
        # In full implementation, would create and run agent executor
        output = {
            "subtask_id": context.current_subtask,
            "status": "completed",
            "result": f"Processed: {subtask.get('description', '')}",
        }
        
        decision = self._record_decision(
            context=context,
            reasoning=reasoning,
            action=action,
            output=output,
            confidence=0.85,
            tool_calls=[],
        )
        
        context.completed_subtasks[context.current_subtask] = output
        return decision


class Reviewer(Agent):
    """
    Reviewer agent: validates specialist output and catches errors.
    
    Responsibilities:
    - Check specialist output against expected format
    - Validate correctness and completeness
    - Identify errors or issues needing rework
    - Approve or reject specialist work
    - Return to specialist with feedback if needed
    """

    def __init__(self, model_name: str = "gpt-4"):
        super().__init__("reviewer_1", "reviewer")
        self.model_name = model_name

    async def execute(self, context: AgentContext, output_to_review: dict, expected_format: dict, **kwargs) -> AgentDecision:
        """
        Review specialist output.
        
        Args:
            context: Shared execution context
            output_to_review: The specialist's output
            expected_format: The expected output schema
            
        Returns:
            AgentDecision with review result:
            - approved: boolean
            - issues: list of problems found
            - feedback: guidance for specialist if rejected
        """
        from langchain_openai import ChatOpenAI
        
        # Initialize LLM for review reasoning
        llm = ChatOpenAI(model_name=self.model_name, temperature=0)
        
        # Simplified review logic (in full implementation, would use LLM for reasoning)
        issues = []
        if not isinstance(output_to_review, dict):
            issues.append("Output is not a dictionary")
        
        approved = len(issues) == 0
        
        reasoning = f"Reviewed specialist output for {len(context.completed_subtasks)} completed subtasks"
        action = "review_output"
        
        review_result = {
            "approved": approved,
            "issues": issues,
            "feedback": "" if approved else "Address the following issues before resubmission",
            "subtasks_reviewed": len(context.completed_subtasks),
        }
        
        decision = self._record_decision(
            context=context,
            reasoning=reasoning,
            action=action,
            output=review_result,
            confidence=0.9 if approved else 0.7,
        )
        
        return decision

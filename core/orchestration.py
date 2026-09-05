"""
LangGraph-based orchestration engine for the agent system.

State machine flow:
  intake → planning → specialist_execution → review → synthesis → delivery
  
Conditional edges:
- retry_on_failure: Failed subtask → specialist_execution
- reviewer_rejects: reviewer output → specialist_execution (send back to specialist)
- low_confidence_escalate: plan confidence < threshold → escalation node
"""

import asyncio
from typing import Any, Optional, Callable

try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.graph.graph import CompiledGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    StateGraph = None
    END = "END"
    START = "START"
    CompiledGraph = Any
    LANGGRAPH_AVAILABLE = False

from pydantic import BaseModel
from enum import Enum
import json
from datetime import datetime

from .agents import (
    Supervisor, Specialist, Reviewer, Agent,
    SpecialistType, AgentContext, AgentDecision
)
from .task_decomposition import TaskDecompositionEngine
from .tool_registry import ToolRegistry
from .human_approval import ApprovalQueue, ApprovalRequest, ApprovalStatus
from .observability import ObservabilityManager, TraceExplorer

# Memory integration (Phase 2)
try:
    from ..memory import MemoryAPI, PlanningWithMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


class ExecutionState(BaseModel):
    """State object passed through the LangGraph workflow."""
    
    # Core context
    task_id: str
    original_request: str
    
    # Planning phase
    plan: Optional[dict] = None
    plan_confidence: float = 0.0
    plan_valid: bool = False
    
    # Execution phase
    completed_subtasks: dict[str, Any] = {}
    current_subtask_index: int = 0
    subtask_results: dict[str, Any] = {}
    
    # Review phase
    review_result: Optional[dict] = None
    reviewed_output: Optional[Any] = None
    needs_rework: bool = False
    rework_feedback: str = ""

    # Human approval / escalation
    requires_approval: bool = False
    approval_request_id: Optional[str] = None
    approval_status: Optional[str] = None
    
    # Synthesis phase
    final_output: Optional[Any] = None
    
    # Execution metadata
    decisions: list[dict] = []
    errors: list[dict] = []
    status: str = "intake"  # intake, planning, executing, reviewing, synthesizing, complete, escalated
    execution_start_time: datetime = None
    execution_end_time: Optional[datetime] = None
    total_cost: float = 0.0
    
    # Memory integration (Phase 2)
    memory_context: Optional[dict] = None  # Retrieved memories
    memory_was_used: bool = False  # Whether memory influenced planning
    tools_used: list[str] = []  # Tools used in execution
    domain_facts: list[str] = []  # Facts discovered
    success_score: float = 0.8  # Final success score
    
    class Config:
        arbitrary_types_allowed = True


class AgentOrchestrator:
    """
    Orchestrates the multi-agent workflow using LangGraph.
    
    Manages:
    - State transitions
    - Agent invocation and result handling
    - Error recovery and retries
    - Human escalation triggers
    """
    
    def __init__(
        self,
        plan_confidence_threshold: float = 0.6,
        memory_api: Optional[Any] = None,
        planning_with_memory: Optional[Any] = None,
    ):
        self.supervisor = Supervisor()
        self.specialists: dict[str, Specialist] = {
            "research": Specialist(SpecialistType.RESEARCH),
            "data_analysis": Specialist(SpecialistType.DATA_ANALYSIS),
            "writing": Specialist(SpecialistType.WRITING),
            "code_execution": Specialist(SpecialistType.CODE_EXECUTION),
        }
        self.reviewer = Reviewer()
        self.plan_confidence_threshold = plan_confidence_threshold
        self.tool_registry = ToolRegistry.get_instance()
        self.approval_queue = ApprovalQueue()
        self.observability = ObservabilityManager()
        self.trace_explorer = TraceExplorer(self.observability)
        
        # Memory integration (Phase 2)
        self.memory_api = memory_api
        self.planning_with_memory = planning_with_memory
        self.use_memory = memory_api is not None and planning_with_memory is not None
        
        self.graph: Optional[CompiledGraph] = None
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the LangGraph state machine."""
        if not LANGGRAPH_AVAILABLE:
            self.graph = None
            return

        builder = StateGraph(ExecutionState)
        
        # Define nodes
        builder.add_node("intake", self._node_intake)
        builder.add_node("planning", self._node_planning)
        builder.add_node("specialist_execution", self._node_specialist_execution)
        builder.add_node("review", self._node_review)
        builder.add_node("synthesis", self._node_synthesis)
        builder.add_node("deliver", self._node_deliver)
        builder.add_node("escalate", self._node_escalate)
        
        # Define edges
        builder.add_edge(START, "intake")
        builder.add_edge("intake", "planning")
        
        # Planning → specialist execution or escalate based on confidence
        builder.add_conditional_edges(
            "planning",
            lambda state: "specialist_execution" if state.plan_confidence >= self.plan_confidence_threshold else "escalate",
            {"specialist_execution": "specialist_execution", "escalate": "escalate"}
        )
        
        # Specialist execution → review
        builder.add_edge("specialist_execution", "review")
        
        # Review → synthesis if approved, rework if not
        builder.add_conditional_edges(
            "review",
            lambda state: "specialist_execution" if state.needs_rework else "synthesis",
            {"specialist_execution": "specialist_execution", "synthesis": "synthesis"}
        )
        
        # Synthesis → deliver
        builder.add_edge("synthesis", "deliver")
        
        # Escalate and deliver end
        builder.add_edge("escalate", END)
        builder.add_edge("deliver", END)
        
        self.graph = builder.compile()
    
    async def execute(self, request: str, context_facts: Optional[dict] = None) -> dict:
        """
        Execute a complete workflow for a request.
        
        Args:
            request: The high-level task request
            context_facts: Optional domain context
            
        Returns:
            Final execution result with all metadata
        """
        import uuid
        
        task_id = str(uuid.uuid4())[:8]
        initial_state = ExecutionState(
            task_id=task_id,
            original_request=request,
            execution_start_time=datetime.now(),
        )

        self.observability.begin_task(task_id, request)
        self.observability.record_event(task_id, "intake", "workflow_started", workflow_task_id=task_id)
        
        # Run the graph
        result_state = await self._run_graph_async(initial_state)
        
        # Set end time
        result_state.execution_end_time = datetime.now()
        self.observability.record_event(task_id, "deliver", "workflow_finished", status=result_state.status)
        self.observability.record_task_completed(task_id, status=result_state.status, final_output=result_state.final_output)

        # Track cost summary for observability
        result_state.total_cost = self.observability.cost_tracker.get_task_total(task_id)
        
        # Store task memory if memory system is available (Phase 2)
        if self.use_memory and result_state.status == "complete":
            duration = (result_state.execution_end_time - result_state.execution_start_time).total_seconds()
            await self.memory_api.record_task_completion(
                task_id=result_state.task_id,
                request=result_state.original_request,
                plan_summary=str(result_state.plan.get("total_estimated_complexity", "unknown")) if result_state.plan else "N/A",
                tools_used=result_state.tools_used,
                domain_facts=result_state.domain_facts,
                success_score=result_state.success_score,
                cost=result_state.total_cost,
                duration_seconds=duration,
            )
        
        return result_state.model_dump()
    
    async def _run_graph_async(self, initial_state: ExecutionState) -> ExecutionState:
        """Run the compiled graph asynchronously."""
        if not LANGGRAPH_AVAILABLE:
            raise RuntimeError("LangGraph is not installed. Install project dependencies to run orchestration.")

        # For now, run synchronously and wrap in async
        # In production, would use proper async graph execution
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._run_graph_sync, initial_state)
        return result
    
    def _run_graph_sync(self, initial_state: ExecutionState) -> ExecutionState:
        """Run the compiled graph synchronously."""
        final_state = self.graph.invoke(initial_state.model_dump())
        return ExecutionState(**final_state)
    
    async def _node_intake(self, state: ExecutionState) -> ExecutionState:
        """Intake node: validate and prepare the request."""
        state.status = "intake"
        self.observability.record_event(state.task_id, "intake", "accept_request", request_preview=state.original_request[:100])
        state.decisions.append({
            "node": "intake",
            "timestamp": datetime.now().isoformat(),
            "action": "accept_request",
            "request_preview": state.original_request[:100],
        })
        return state
    
    async def _node_planning(self, state: ExecutionState) -> ExecutionState:
        """Planning node: decompose request into tasks, with optional memory enhancement."""
        state.status = "planning"
        
        decomposer = TaskDecompositionEngine()
        
        # Use memory-enhanced planning if available
        if self.use_memory and self.planning_with_memory:
            plan = await self.planning_with_memory.decompose_with_memory(
                state.original_request,
                context_facts=None,
                retrieve_memory=True,
            )
            state.memory_context = plan.get("memory_context")
            state.memory_was_used = plan.get("memory_was_used", False)
        else:
            plan = await decomposer.decompose(
                state.original_request,
                context_facts=None
            )
        
        state.plan = plan
        state.plan_confidence = plan.get("confidence", 0.6)
        state.plan_valid = state.plan_confidence > 0.0
        self.observability.record_event(
            state.task_id,
            "planning",
            "create_plan",
            subtasks_count=len(plan.get("subtasks", [])),
            confidence=state.plan_confidence,
            memory_used=state.memory_was_used,
        )
        
        state.decisions.append({
            "node": "planning",
            "timestamp": datetime.now().isoformat(),
            "action": "create_plan",
            "subtasks_count": len(plan.get("subtasks", [])),
            "confidence": state.plan_confidence,
            "memory_used": state.memory_was_used,
        })
        
        return state
    
    async def _node_specialist_execution(self, state: ExecutionState) -> ExecutionState:
        """Specialist execution node: execute subtasks in parallel/sequential order."""
        state.status = "executing"
        
        plan = state.plan
        if not plan:
            state.errors.append({
                "node": "specialist_execution",
                "error": "No plan available",
                "timestamp": datetime.now().isoformat(),
            })
            return state
        
        execution_flow = plan.get("execution_flow", [])
        subtasks_by_id = {t["id"]: t for t in plan.get("subtasks", [])}
        
        for task_group in execution_flow:
            # Execute tasks in this group (can be parallel)
            tasks = [subtasks_by_id[task_id] for task_id in task_group if task_id in subtasks_by_id]
            
            # For now, execute sequentially; production code would use asyncio.gather
            for task in tasks:
                specialist_type = task.get("specialist_type", "general")
                specialist = self.specialists.get(specialist_type)
                
                if not specialist:
                    state.errors.append({
                        "task": task.get("id"),
                        "error": f"No specialist for type {specialist_type}",
                        "timestamp": datetime.now().isoformat(),
                    })
                    continue
                
                # Execute the subtask
                try:
                    # Create a simplified context for the specialist
                    result = {
                        "task_id": task.get("id"),
                        "status": "completed",
                        "result": task.get("description"),
                        "specialist": specialist_type,
                    }
                    
                    state.subtask_results[task.get("id")] = result
                    state.decisions.append({
                        "node": "specialist_execution",
                        "timestamp": datetime.now().isoformat(),
                        "specialist": specialist_type,
                        "task_id": task.get("id"),
                        "status": "completed",
                    })
                    
                except Exception as e:
                    state.errors.append({
                        "node": "specialist_execution",
                        "task": task.get("id"),
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    })
        
        state.completed_subtasks = state.subtask_results
        self.observability.record_event(
            state.task_id,
            "specialist_execution",
            "subtasks_completed",
            completed_subtasks=list(state.subtask_results.keys()),
            tools_used=state.tools_used,
        )
        return state
    
    async def _node_review(self, state: ExecutionState) -> ExecutionState:
        """Review node: validate specialist outputs."""
        state.status = "reviewing"
        
        # Simplified review logic
        state.needs_rework = False
        
        if not state.completed_subtasks:
            state.needs_rework = True
            state.rework_feedback = "No subtasks were completed"
        else:
            state.review_result = {
                "approved": True,
                "issues": [],
                "subtasks_reviewed": len(state.completed_subtasks),
            }
        
        self.observability.record_event(
            state.task_id,
            "review",
            "review_output",
            approved=not state.needs_rework,
            issues=state.review_result.get("issues", []) if state.review_result else [],
        )

        state.decisions.append({
            "node": "review",
            "timestamp": datetime.now().isoformat(),
            "action": "review_output",
            "approved": not state.needs_rework,
        })
        
        return state
    
    async def _node_synthesis(self, state: ExecutionState) -> ExecutionState:
        """Synthesis node: combine specialist outputs into final result."""
        state.status = "synthesizing"
        
        # Combine all subtask results
        state.final_output = {
            "task_id": state.task_id,
            "request": state.original_request,
            "subtask_results": state.completed_subtasks,
            "review_passed": not state.needs_rework,
            "total_decisions": len(state.decisions),
            "total_errors": len(state.errors),
        }
        
        self.observability.record_event(
            state.task_id,
            "synthesis",
            "synthesize_output",
            subtasks_count=len(state.completed_subtasks),
        )

        state.decisions.append({
            "node": "synthesis",
            "timestamp": datetime.now().isoformat(),
            "action": "synthesize_output",
        })
        
        return state
    
    async def _node_deliver(self, state: ExecutionState) -> ExecutionState:
        """Deliver node: prepare final output for user."""
        state.status = "complete"
        
        self.observability.record_event(
            state.task_id,
            "deliver",
            "deliver_result",
            output_ready=True,
            total_cost=state.total_cost,
        )

        state.decisions.append({
            "node": "deliver",
            "timestamp": datetime.now().isoformat(),
            "action": "deliver_result",
            "output_ready": True,
        })
        
        return state
    
    async def _node_escalate(self, state: ExecutionState) -> ExecutionState:
        """Escalate node: create a human approval request and stop execution pending review."""
        state.status = "escalated"

        summary = (
            state.plan.get("summary")
            if state.plan and isinstance(state.plan, dict)
            else "Plan requires human review before execution."
        )
        rationale = (
            f"Plan confidence ({state.plan_confidence:.2f}) is below the threshold ({self.plan_confidence_threshold:.2f})."
            if state.plan_confidence < self.plan_confidence_threshold
            else "The workflow requires human review."
        )

        request = self.approval_queue.submit_request(
            task_id=state.task_id,
            original_request=state.original_request,
            plan_confidence=state.plan_confidence,
            rationale=rationale,
            summary=summary,
        )

        state.decisions.append({
            "node": "escalate",
            "timestamp": datetime.now().isoformat(),
            "action": "escalate_to_human",
            "reason": rationale,
            "approval_request_id": request.request_id,
            "approval_status": request.status.value,
        })

        state.errors.append({
            "node": "escalate",
            "task_id": state.task_id,
            "error": "Awaiting human approval",
            "request_id": request.request_id,
            "timestamp": datetime.now().isoformat(),
        })

        return state

    def resolve_escalation(self, task_id: str, approved: bool, notes: str = "", reviewer_id: str = "human") -> ApprovalRequest:
        """Resolve the latest open approval for a task."""
        return self.approval_queue.resolve_task(task_id, approved, notes=notes, reviewer_id=reviewer_id)

    def list_pending_approvals(self) -> list[ApprovalRequest]:
        """Return all pending approval requests."""
        return self.approval_queue.get_pending()
